"""
backend/routers/interviews.py - Interview session management: start, process turn, SSE stream, end, and history.
"""

import json
import asyncio
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

import database
import interview_service
from backend.config import DATABASE_PATH
from backend.security import get_current_user, verify_csrf
from backend.session_manager import session_manager, ActiveSessionEntry

router = APIRouter(prefix="/interviews", tags=["interviews"])


class StartInterviewRequest(BaseModel):
    domain: str = Field(..., min_length=2, max_length=100)
    difficulty: Optional[str] = None


class AnswerRequest(BaseModel):
    answer: str = Field(..., min_length=1)
    client_turn_id: Optional[str] = None


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_csrf)])
@router.post("/start", status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_csrf)])
async def start_interview(
    req: StartInterviewRequest,
    request: Request,
    user: database.User = Depends(get_current_user)
):
    db_path = getattr(request.app.state, "db_path", DATABASE_PATH)

    # Start session and generate opening L0 question
    start_res = interview_service.start_interview_session(
        selected_domain=req.domain,
        user_id=user.user_id,
        difficulty=req.difficulty,
        db_path=db_path
    )

    if start_res.get("status") == "ERROR":
        error_code = start_res.get("error_code")
        if error_code == "RATE_LIMIT_EXCEEDED":
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit reached. Please wait before retrying.",
                headers={"Retry-After": "60"}
            )
        elif error_code == "SYLLABUS_FAILED":
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to generate syllabus for domain. Please try a different domain or retry."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=start_res.get("message", "Failed to start interview session.")
        )

    session_id = start_res["session_id"]
    candidate_id = start_res["candidate_id"]

    # Register in memory active session registry
    session_manager.register_session(
        session_id=session_id,
        user_id=user.user_id,
        candidate_id=candidate_id,
        domain=req.domain,
        orchestrator=start_res["chatbot"]
    )

    return {
        "status": "STARTED",
        "session_id": session_id,
        "domain": req.domain,
        "question": start_res["question"],
        "turn_number": 1,
        "current_subtopic": start_res.get("current_subtopic"),
        "current_difficulty": start_res.get("current_difficulty", "Fundamental")
    }


@router.post("/{session_id}/answer", dependencies=[Depends(verify_csrf)])
async def answer_question(
    session_id: int,
    req: AnswerRequest,
    request: Request,
    user: database.User = Depends(get_current_user)
):
    db_path = getattr(request.app.state, "db_path", DATABASE_PATH)

    # Retrieve or automatically rebuild from DB turns (enforces ownership 403 / 404)
    entry: ActiveSessionEntry = await session_manager.get_or_rebuild_session(
        session_id=session_id,
        user_id=user.user_id,
        db_path=db_path
    )

    clean_answer = req.answer.strip()

    # Idempotency fast-path: if same answer submitted on retry/double-click, return cached outcome
    if entry.last_answer_input == clean_answer and entry.last_turn_result is not None:
        return entry.last_turn_result

    # Acquire session lock to serialize turns
    async with entry.lock:
        if entry.last_answer_input == clean_answer and entry.last_turn_result is not None:
            return entry.last_turn_result

        # Process through pure interview service
        loop = asyncio.get_running_loop()
        outcome = await loop.run_in_executor(
            None,
            lambda: interview_service.process_candidate_answer(
                chatbot=entry.orchestrator,
                user_answer=clean_answer
            )
        )

        entry.update_activity()
        entry.last_answer_input = clean_answer
        entry.last_turn_result = outcome

        # If terminated, close session in DB with consent check
        if outcome.get("status") == "TERMINATED":
            profile = database.get_user_profile(user.user_id, db_path=db_path)
            is_excluded = False
            if profile and not profile.get("consent_save_sessions", True):
                is_excluded = True

            finalize_res = await loop.run_in_executor(
                None,
                lambda: interview_service.finalize_interview_session(
                    session_id=session_id,
                    chatbot=entry.orchestrator,
                    candidate_id=entry.candidate_id,
                    is_excluded=is_excluded,
                    db_path=db_path
                )
            )
            outcome["final_summary"] = finalize_res.get("final_summary")
            outcome["overall_score"] = finalize_res.get("overall_score")
            session_manager.remove_session(session_id)

        outcome["interviewer_message"] = outcome.get("next_question") or outcome.get("message")
        return outcome


@router.post("/{session_id}/answer/stream", dependencies=[Depends(verify_csrf)])
async def answer_question_stream(
    session_id: int,
    req: AnswerRequest,
    request: Request,
    user: database.User = Depends(get_current_user)
):
    """
    SSE streaming endpoint: yields real-time pipeline status events ('analyzing_answer', 'generating_question')
    and final structured 'result' event.
    """
    db_path = getattr(request.app.state, "db_path", DATABASE_PATH)

    entry: ActiveSessionEntry = await session_manager.get_or_rebuild_session(
        session_id=session_id,
        user_id=user.user_id,
        db_path=db_path
    )

    clean_answer = req.answer.strip()

    async def event_generator():
        try:
            if await request.is_disconnected():
                return

            # Yield analyzing status
            yield f"event: status\ndata: {json.dumps({'step': 'analyzing_answer', 'message': 'Analyzing answer accuracy and technical depth...'})}\n\n"
            await asyncio.sleep(0.05)

            async with entry.lock:
                if await request.is_disconnected():
                    return

                # Check idempotency
                if entry.last_answer_input == clean_answer and entry.last_turn_result is not None:
                    yield f"event: result\ndata: {json.dumps(entry.last_turn_result)}\n\n"
                    return

                yield f"event: status\ndata: {json.dumps({'step': 'generating_question', 'message': 'Formulating adaptive follow-up...'})}\n\n"

                loop = asyncio.get_running_loop()
                outcome = await loop.run_in_executor(
                    None,
                    lambda: interview_service.process_candidate_answer(
                        chatbot=entry.orchestrator,
                        user_answer=clean_answer
                    )
                )

                entry.update_activity()
                entry.last_answer_input = clean_answer
                entry.last_turn_result = outcome

                if outcome.get("status") == "TERMINATED":
                    profile = database.get_user_profile(user.user_id, db_path=db_path)
                    is_excluded = bool(profile and not profile.get("consent_save_sessions", True))

                    finalize_res = await loop.run_in_executor(
                        None,
                        lambda: interview_service.finalize_interview_session(
                            session_id=session_id,
                            chatbot=entry.orchestrator,
                            candidate_id=entry.candidate_id,
                            is_excluded=is_excluded,
                            db_path=db_path
                        )
                    )
                    outcome["final_summary"] = finalize_res.get("final_summary")
                    outcome["overall_score"] = finalize_res.get("overall_score")
                    session_manager.remove_session(session_id)

                outcome["interviewer_message"] = outcome.get("next_question") or outcome.get("message")

                if not await request.is_disconnected():
                    yield f"event: result\ndata: {json.dumps(outcome)}\n\n"

        except asyncio.CancelledError:
            pass
        except Exception as e:
            if not await request.is_disconnected():
                yield f"event: error\ndata: {json.dumps({'detail': str(e), 'code': 'STREAM_ERROR'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/{session_id}/end", dependencies=[Depends(verify_csrf)])
async def end_interview(
    session_id: int,
    request: Request,
    user: database.User = Depends(get_current_user)
):
    db_path = getattr(request.app.state, "db_path", DATABASE_PATH)

    # Rebuild if needed to verify ownership (403/404)
    entry: ActiveSessionEntry = await session_manager.get_or_rebuild_session(
        session_id=session_id,
        user_id=user.user_id,
        db_path=db_path
    )

    profile = database.get_user_profile(user.user_id, db_path=db_path)
    is_excluded = bool(profile and not profile.get("consent_save_sessions", True))

    finalize_res = interview_service.finalize_interview_session(
        session_id=session_id,
        chatbot=entry.orchestrator,
        candidate_id=entry.candidate_id,
        is_excluded=is_excluded,
        db_path=db_path
    )

    session_manager.remove_session(session_id)

    return {
        "status": "TERMINATED",
        "session_id": session_id,
        "overall_score": finalize_res.get("overall_score"),
        "final_summary": finalize_res.get("final_summary"),
        "final_summary_items": finalize_res.get("final_summary_items", []),
        "message": "Interview concluded."
    }


@router.get("")
@router.get("/history")
async def list_interviews(
    request: Request,
    domain: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
    user: database.User = Depends(get_current_user)
):
    db_path = getattr(request.app.state, "db_path", DATABASE_PATH)
    cand, _ = database.get_or_create_candidate_for_user(user_id=user.user_id, db_path=db_path)

    sessions = database.get_candidate_sessions(
        candidate_id=cand.candidate_id,
        include_excluded=False,
        db_path=db_path
    )

    enhanced = []
    for s in sessions:
        started_at = s.get("started_at")
        ended_at = s.get("ended_at")
        duration = None
        if started_at and ended_at:
            duration = round((ended_at - started_at).total_seconds())

        s_status = "COMPLETED" if ended_at else "IN_PROGRESS"
        item = {
            **s,
            "status": s_status,
            "duration": duration
        }

        # Filter by domain
        if domain and domain.lower() != "all":
            if item.get("domain", "").lower() != domain.lower():
                continue

        # Filter by search text
        if search and search.strip():
            query = search.strip().lower()
            d_name = (item.get("domain") or "").lower()
            summary = (item.get("final_summary") or "").lower()
            if query not in d_name and query not in summary:
                continue

        enhanced.append(item)

    total_count = len(enhanced)
    start_idx = max(0, (page - 1) * page_size)
    paginated = enhanced[start_idx : start_idx + page_size]

    return paginated


@router.get("/{session_id}")
async def get_interview_detail(
    session_id: int,
    request: Request,
    user: database.User = Depends(get_current_user)
):
    db_path = getattr(request.app.state, "db_path", DATABASE_PATH)
    session_info = database.get_session_by_id(session_id, db_path=db_path)
    if not session_info:
        raise HTTPException(status_code=404, detail="Interview session not found.")

    cand_user_id = database.get_candidate_user_id(session_info["candidate_id"], db_path=db_path)
    if cand_user_id is not None and cand_user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Access denied: You do not own this session.")

    turns = database.get_session_turns(session_id, db_path=db_path)

    # Enhance turns with alias fields
    enhanced_turns = []
    for t in turns:
        enhanced_turns.append({
            **t,
            "justification": t.get("judge_justification"),
            "momentum": t.get("momentum_signal") or "NEUTRAL"
        })

    # Compute session current difficulty
    current_difficulty = "Fundamental"
    scores = [t["score"] for t in turns if t["score"] is not None]
    if scores:
        avg_s = sum(scores[-3:]) / len(scores[-3:])
        if avg_s >= 8.0:
            current_difficulty = "Advanced"
        elif avg_s >= 5.0:
            current_difficulty = "Intermediate"

    session_status = "COMPLETED" if session_info.get("ended_at") else "IN_PROGRESS"
    
    # Resolve pending_question for in-progress session
    pending_question = None
    if session_status == "IN_PROGRESS":
        if session_manager.has_session(session_id):
            active_entry = session_manager.get_session(session_id)
            pending_question = getattr(active_entry.orchestrator, "last_question", None)
        elif enhanced_turns:
            pending_question = enhanced_turns[-1].get("question_text")

    # Generate final_summary_items from stats if session ended
    final_summary_items = []
    if session_status == "COMPLETED" and scores:
        import analytics_service
        stats = analytics_service.calculate_interview_stats(
            candidate_id=session_info["candidate_id"],
            session_id=session_id,
            db_path=db_path
        )
        final_summary_items = analytics_service.generate_ai_feedback_items(stats)

    return {
        "session": {
            **session_info,
            "status": session_status,
            "pending_question": pending_question,
            "current_difficulty": current_difficulty,
            "final_summary_items": final_summary_items
        },
        "turns": enhanced_turns,
        "current_difficulty": current_difficulty,
        "status": session_status,
        "pending_question": pending_question,
        "final_summary_items": final_summary_items
    }
