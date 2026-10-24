"""
backend/session_manager.py - In-memory active session registry with per-session locks,
idle eviction, and automatic DB rebuild capabilities.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Any

from fastapi import HTTPException, status

import database
import interview_service
from interview import InterviewOrchestrator


class ActiveSessionEntry:
    def __init__(
        self,
        session_id: int,
        user_id: int,
        candidate_id: int,
        domain: str,
        orchestrator: InterviewOrchestrator
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.candidate_id = candidate_id
        self.domain = domain
        self.orchestrator = orchestrator
        self.lock = asyncio.Lock()
        self.last_activity = datetime.now(timezone.utc)
        self.last_answer_input: Optional[str] = None
        self.last_turn_result: Optional[Dict[str, Any]] = None

    def update_activity(self):
        self.last_activity = datetime.now(timezone.utc)


class ActiveSessionManager:
    """
    Registry for in-flight interview sessions with automatic rehydration from SQLite.
    """

    def __init__(self):
        self._sessions: Dict[int, ActiveSessionEntry] = {}
        self._registry_lock = asyncio.Lock()

    def register_session(
        self,
        session_id: int,
        user_id: int,
        candidate_id: int,
        domain: str,
        orchestrator: InterviewOrchestrator
    ) -> ActiveSessionEntry:
        entry = ActiveSessionEntry(
            session_id=session_id,
            user_id=user_id,
            candidate_id=candidate_id,
            domain=domain,
            orchestrator=orchestrator
        )
        self._sessions[session_id] = entry
        return entry

    def has_session(self, session_id: int) -> bool:
        return session_id in self._sessions

    def get_session(self, session_id: int) -> Optional[ActiveSessionEntry]:
        return self._sessions.get(session_id)

    async def get_or_rebuild_session(
        self,
        session_id: int,
        user_id: int,
        db_path: Optional[str] = None
    ) -> ActiveSessionEntry:
        """
        Retrieves active session from memory or seamlessly rebuilds it from SQLite DB.
        Enforces strict user ownership.
        """
        async with self._registry_lock:
            # 1. In-memory check
            if session_id in self._sessions:
                entry = self._sessions[session_id]
                if entry.user_id != user_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: You do not own this interview session."
                    )
                entry.update_activity()
                return entry

            # 2. Database lookup
            session_info = database.get_session_by_id(session_id, db_path=db_path)
            if not session_info:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Interview session {session_id} not found."
                )

            # 3. Ownership check via candidate record
            candidate_id = session_info["candidate_id"]
            cand_user_id = database.get_candidate_user_id(candidate_id, db_path=db_path)

            if cand_user_id is not None and cand_user_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You do not own this interview session."
                )

            # 4. Rebuild orchestrator state from turns
            orchestrator = interview_service.rebuild_orchestrator_from_db(session_id, db_path=db_path)
            if not orchestrator:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to reconstruct interview session {session_id} from history."
                )

            # 5. Re-register into active memory map
            entry = self.register_session(
                session_id=session_id,
                user_id=user_id,
                candidate_id=candidate_id,
                domain=session_info["domain"],
                orchestrator=orchestrator
            )
            return entry

    def remove_session(self, session_id: int):
        """Removes session from in-memory registry."""
        if session_id in self._sessions:
            del self._sessions[session_id]

    async def cleanup_idle_sessions(self, timeout_hours: int = 2) -> int:
        """Evicts sessions inactive for more than timeout_hours from memory."""
        now = datetime.now(timezone.utc)
        evict_threshold = timedelta(hours=timeout_hours)
        evicted_ids = []

        async with self._registry_lock:
            for sid, entry in list(self._sessions.items()):
                if (now - entry.last_activity) > evict_threshold:
                    evicted_ids.append(sid)

            for sid in evicted_ids:
                del self._sessions[sid]

        return len(evicted_ids)


session_manager = ActiveSessionManager()
