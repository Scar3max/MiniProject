"""
database.py - Persistent Database Layer for Adaptive Interview Bot
SQLite + SQLAlchemy ORM models and repository helpers.
Supports Users, Profiles, Candidates, Sessions, and Turns.
"""

import os
import uuid
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Text, DateTime, Boolean, ForeignKey, func, desc, or_, event, text
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, scoped_session

Base = declarative_base()

DEFAULT_DB_PATH = os.getenv("INTERVIEW_DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "interview_history.db"))


# ---------------------------------------------------------------------------
# ORM Models
# ---------------------------------------------------------------------------

class User(Base):
    """
    Represents an authenticated user account or guest account.
    """
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=True)  # Null for guests
    role = Column(String, default="candidate", nullable=False)
    is_guest = Column(Boolean, default=False, nullable=False)
    guest_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    candidates = relationship("Candidate", back_populates="user", cascade="all, delete-orphan")


class UserProfile(Base):
    """
    User profile storing onboarding preferences and details.
    """
    __tablename__ = "user_profiles"

    profile_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    college_org = Column(String, nullable=True)
    year_experience = Column(String, nullable=True)
    target_role = Column(String, nullable=True)
    preferred_domains = Column(Text, nullable=True)  # JSON-serialized list
    preferred_difficulty = Column(String, default="adaptive", nullable=False)
    consent_save_sessions = Column(Boolean, default=True, nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="profile")


class Candidate(Base):
    """
    Represents a candidate identity.
    external_id is a generic identifier (name, email, or anon-UUID).
    user_id links to users table if registered/authenticated.
    """
    __tablename__ = "candidates"

    candidate_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=True, index=True)
    external_id = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    avg_score = Column(Float, nullable=True)
    total_sessions = Column(Integer, default=0, nullable=False)
    strongest_topic = Column(String, nullable=True)
    weakest_topic = Column(String, nullable=True)

    user = relationship("User", back_populates="candidates")
    sessions = relationship("InterviewSession", back_populates="candidate", cascade="all, delete-orphan")


class InterviewSession(Base):
    """
    Represents an interview session.
    is_excluded marks sessions excluded from history/analytics (e.g. consent_save_sessions = False).
    """
    __tablename__ = "sessions"

    session_id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(Integer, ForeignKey("candidates.candidate_id", ondelete="CASCADE"), nullable=False, index=True)
    domain = Column(String, nullable=False)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    ended_at = Column(DateTime, nullable=True)
    final_summary = Column(Text, nullable=True)
    overall_score = Column(Float, nullable=True)
    is_excluded = Column(Boolean, default=False, nullable=False)

    candidate = relationship("Candidate", back_populates="sessions")
    turns = relationship("Turn", back_populates="session", cascade="all, delete-orphan", order_by="Turn.turn_number")


class Turn(Base):
    """
    Represents a single turn in an interview session.
    Written turn-by-turn immediately as the interview progresses.
    """
    __tablename__ = "turns"

    turn_id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False, index=True)
    turn_number = Column(Integer, nullable=False)
    subtopic = Column(String, nullable=True)
    question_text = Column(Text, nullable=False)
    candidate_answer = Column(Text, nullable=False)
    answer_classification = Column(String, nullable=False)
    score = Column(Float, nullable=False)
    momentum_signal = Column(String, nullable=True)
    judge_justification = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    session = relationship("InterviewSession", back_populates="turns")


# ---------------------------------------------------------------------------
# Database Initialization & Session Factory
# ---------------------------------------------------------------------------

def get_engine(db_path: Optional[str] = None):
    path = db_path or os.getenv("INTERVIEW_DB_PATH") or DEFAULT_DB_PATH
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False, "timeout": 10.0})

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def get_session_factory(db_path: Optional[str] = None):
    engine = get_engine(db_path)
    return scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))


def init_db(db_path: Optional[str] = None):
    """Creates database tables if they do not already exist, and ensures additive columns are present."""
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)

    # Ensure additive columns exist on pre-existing tables
    with engine.connect() as conn:
        res = conn.execute(text("PRAGMA table_info(candidates)"))
        cand_cols = [row[1] for row in res.fetchall()]
        if "user_id" not in cand_cols:
            conn.execute(text("ALTER TABLE candidates ADD COLUMN user_id INTEGER REFERENCES users(user_id)"))

        res = conn.execute(text("PRAGMA table_info(sessions)"))
        sess_cols = [row[1] for row in res.fetchall()]
        if "is_excluded" not in sess_cols:
            conn.execute(text("ALTER TABLE sessions ADD COLUMN is_excluded BOOLEAN NOT NULL DEFAULT 0"))

        conn.commit()


def format_judge_justification(score_reason: Optional[str], analysis_notes: Optional[str]) -> str:
    """
    Combines scorer's justification text and judge's analysis notes.
    Format: 'Scorer: <score_reason> | Judge: <analysis_notes>'
    """
    parts = []
    if score_reason and str(score_reason).strip():
        parts.append(f"Scorer: {str(score_reason).strip()}")
    if analysis_notes and str(analysis_notes).strip():
        parts.append(f"Judge: {str(analysis_notes).strip()}")
    return " | ".join(parts) if parts else ""


# ---------------------------------------------------------------------------
# User & Auth Repository Functions
# ---------------------------------------------------------------------------

def create_user(
    email: str,
    password_hash: Optional[str] = None,
    role: str = "candidate",
    is_guest: bool = False,
    guest_expires_at: Optional[datetime] = None,
    db_path: Optional[str] = None
) -> User:
    """Creates a new user record."""
    init_db(db_path)
    SessionFactory = get_session_factory(db_path)
    session = SessionFactory()
    try:
        user = User(
            email=email.strip().lower(),
            password_hash=password_hash,
            role=role,
            is_guest=is_guest,
            guest_expires_at=guest_expires_at,
            created_at=datetime.now(timezone.utc)
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user
    finally:
        session.close()


def get_user_by_email(email: str, db_path: Optional[str] = None) -> Optional[User]:
    """Finds user by email (case-insensitive)."""
    init_db(db_path)
    SessionFactory = get_session_factory(db_path)
    session = SessionFactory()
    try:
        return session.query(User).filter_by(email=email.strip().lower()).first()
    finally:
        session.close()


def get_user_by_id(user_id: int, db_path: Optional[str] = None) -> Optional[User]:
    """Finds user by user_id."""
    init_db(db_path)
    SessionFactory = get_session_factory(db_path)
    session = SessionFactory()
    try:
        return session.query(User).filter_by(user_id=user_id).first()
    finally:
        session.close()


def get_user_profile(user_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves user profile details as dict."""
    init_db(db_path)
    SessionFactory = get_session_factory(db_path)
    session = SessionFactory()
    try:
        profile = session.query(UserProfile).filter_by(user_id=user_id).first()
        if not profile:
            return None
        domains = []
        if profile.preferred_domains:
            try:
                domains = json.loads(profile.preferred_domains)
            except Exception:
                domains = []
        return {
            "profile_id": profile.profile_id,
            "user_id": profile.user_id,
            "full_name": profile.full_name,
            "college_org": profile.college_org,
            "year_experience": profile.year_experience,
            "target_role": profile.target_role,
            "preferred_domains": domains,
            "preferred_difficulty": profile.preferred_difficulty,
            "consent_save_sessions": profile.consent_save_sessions,
            "updated_at": profile.updated_at
        }
    finally:
        session.close()


def upsert_user_profile(user_id: int, profile_data: Dict[str, Any], db_path: Optional[str] = None) -> Dict[str, Any]:
    """Creates or updates a user profile."""
    init_db(db_path)
    SessionFactory = get_session_factory(db_path)
    session = SessionFactory()
    try:
        profile = session.query(UserProfile).filter_by(user_id=user_id).first()
        if not profile:
            profile = UserProfile(user_id=user_id)
            session.add(profile)

        if "full_name" in profile_data:
            profile.full_name = profile_data["full_name"]
        if "college_org" in profile_data:
            profile.college_org = profile_data["college_org"]
        if "year_experience" in profile_data:
            profile.year_experience = profile_data["year_experience"]
        if "target_role" in profile_data:
            profile.target_role = profile_data["target_role"]
        if "preferred_domains" in profile_data:
            pref = profile_data["preferred_domains"]
            profile.preferred_domains = json.dumps(pref) if isinstance(pref, list) else str(pref)
        if "preferred_difficulty" in profile_data:
            profile.preferred_difficulty = profile_data["preferred_difficulty"]
        if "consent_save_sessions" in profile_data:
            profile.consent_save_sessions = bool(profile_data["consent_save_sessions"])

        profile.updated_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(profile)

        domains = []
        if profile.preferred_domains:
            try:
                domains = json.loads(profile.preferred_domains)
            except Exception:
                domains = []

        return {
            "profile_id": profile.profile_id,
            "user_id": profile.user_id,
            "full_name": profile.full_name,
            "college_org": profile.college_org,
            "year_experience": profile.year_experience,
            "target_role": profile.target_role,
            "preferred_domains": domains,
            "preferred_difficulty": profile.preferred_difficulty,
            "consent_save_sessions": profile.consent_save_sessions,
            "updated_at": profile.updated_at
        }
    finally:
        session.close()


def update_user_password(user_id: int, new_password_hash: str, db_path: Optional[str] = None) -> bool:
    """Updates password hash for a user."""
    init_db(db_path)
    SessionFactory = get_session_factory(db_path)
    session = SessionFactory()
    try:
        user = session.query(User).filter_by(user_id=user_id).first()
        if not user:
            return False
        user.password_hash = new_password_hash
        session.commit()
        return True
    finally:
        session.close()


def delete_user_data(user_id: int, db_path: Optional[str] = None) -> bool:
    """
    Deletes the user, profile, candidate row, sessions, and turns for that user only.
    """
    init_db(db_path)
    SessionFactory = get_session_factory(db_path)
    session = SessionFactory()
    try:
        user = session.query(User).filter_by(user_id=user_id).first()
        if not user:
            return False

        # Find linked candidates
        linked_candidates = session.query(Candidate).filter_by(user_id=user_id).all()
        for cand in linked_candidates:
            session.delete(cand)

        session.delete(user)
        session.commit()
        return True
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Candidate & Session Repository Functions
# ---------------------------------------------------------------------------

def get_or_create_candidate(external_id: Optional[str] = None, db_path: Optional[str] = None) -> Tuple[Candidate, bool]:
    """
    Retrieves or creates an anonymous or legacy candidate record.
    """
    init_db(db_path)
    SessionFactory = get_session_factory(db_path)
    session = SessionFactory()
    try:
        clean_id = external_id.strip() if external_id and external_id.strip() else None

        if not clean_id:
            clean_id = f"anon-{uuid.uuid4().hex[:12]}"
            candidate = Candidate(
                external_id=clean_id,
                created_at=datetime.now(timezone.utc),
                total_sessions=0
            )
            session.add(candidate)
            session.commit()
            session.refresh(candidate)
            return candidate, True

        candidate = session.query(Candidate).filter_by(external_id=clean_id).first()
        if candidate:
            return candidate, False

        candidate = Candidate(
            external_id=clean_id,
            created_at=datetime.now(timezone.utc),
            total_sessions=0
        )
        session.add(candidate)
        session.commit()
        session.refresh(candidate)
        return candidate, True
    finally:
        session.close()


def get_or_create_candidate_for_user(user_id: int, db_path: Optional[str] = None) -> Tuple[Candidate, bool]:
    """
    Retrieves or creates candidate record explicitly linked to a registered or guest user.
    Decision 3: Registration always creates a new candidate row linked via user_id.
    """
    init_db(db_path)
    SessionFactory = get_session_factory(db_path)
    session = SessionFactory()
    try:
        user = session.query(User).filter_by(user_id=user_id).first()
        if not user:
            raise ValueError(f"User with id {user_id} not found.")

        cand = session.query(Candidate).filter_by(user_id=user_id).first()
        if cand:
            return cand, False

        # Create new candidate row with unique external_id
        cand_ext_id = f"user-{user.user_id}-{uuid.uuid4().hex[:8]}"
        candidate = Candidate(
            user_id=user.user_id,
            external_id=cand_ext_id,
            created_at=datetime.now(timezone.utc),
            total_sessions=0
        )
        session.add(candidate)
        session.commit()
        session.refresh(candidate)
        return candidate, True
    finally:
        session.close()


def start_session(candidate_id: int, domain: str, db_path: Optional[str] = None) -> int:
    """
    Creates a new interview session record in SQLite and returns session_id.
    """
    init_db(db_path)
    SessionFactory = get_session_factory(db_path)
    session = SessionFactory()
    try:
        new_session = InterviewSession(
            candidate_id=candidate_id,
            domain=domain,
            started_at=datetime.now(timezone.utc),
            is_excluded=False
        )
        session.add(new_session)
        session.commit()
        session.refresh(new_session)
        return new_session.session_id
    finally:
        session.close()


def record_turn(
    session_id: int,
    turn_number: int,
    subtopic: Optional[str],
    question_text: str,
    candidate_answer: str,
    answer_classification: str,
    score: float,
    momentum_signal: Optional[str] = None,
    judge_justification: Optional[str] = None,
    db_path: Optional[str] = None
) -> int:
    """
    Persists a single turn immediately to SQLite. Returns turn_id.
    """
    init_db(db_path)
    SessionFactory = get_session_factory(db_path)
    session = SessionFactory()
    try:
        turn = Turn(
            session_id=session_id,
            turn_number=turn_number,
            subtopic=subtopic or "General",
            question_text=question_text,
            candidate_answer=candidate_answer,
            answer_classification=answer_classification,
            score=round(float(score), 1),
            momentum_signal=momentum_signal,
            judge_justification=judge_justification,
            timestamp=datetime.now(timezone.utc)
        )
        session.add(turn)
        session.commit()
        session.refresh(turn)
        return turn.turn_id
    finally:
        session.close()


def finish_session(
    session_id: int,
    final_summary: Optional[str] = None,
    overall_score: Optional[float] = None,
    is_excluded: bool = False,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Closes session row and recomputes candidate lifetime aggregates.
    If is_excluded=True (consent_save_sessions=False), marks session as excluded.
    """
    init_db(db_path)
    SessionFactory = get_session_factory(db_path)
    session = SessionFactory()
    try:
        interview_session = session.query(InterviewSession).filter_by(session_id=session_id).first()
        if not interview_session:
            raise ValueError(f"Session with id {session_id} not found.")

        if overall_score is None:
            turn_scores = [t.score for t in interview_session.turns if t.score is not None]
            overall_score = round(sum(turn_scores) / len(turn_scores), 1) if turn_scores else 0.0

        interview_session.ended_at = datetime.now(timezone.utc)
        interview_session.overall_score = round(float(overall_score), 1)
        interview_session.final_summary = final_summary
        interview_session.is_excluded = is_excluded
        session.flush()

        candidate_id = interview_session.candidate_id
        candidate = session.query(Candidate).filter_by(candidate_id=candidate_id).first()

        # Recompute total sessions (excluding excluded sessions)
        total_sessions = (
            session.query(func.count(InterviewSession.session_id))
            .filter(
                InterviewSession.candidate_id == candidate_id,
                InterviewSession.ended_at.isnot(None),
                InterviewSession.is_excluded == False
            )
            .scalar() or 0
        )
        candidate.total_sessions = total_sessions

        # Fetch non-excluded turns for candidate aggregates
        all_candidate_turns = (
            session.query(Turn)
            .join(InterviewSession, Turn.session_id == InterviewSession.session_id)
            .filter(
                InterviewSession.candidate_id == candidate_id,
                InterviewSession.is_excluded == False
            )
            .all()
        )

        if all_candidate_turns:
            all_scores = [t.score for t in all_candidate_turns if t.score is not None]
            candidate.avg_score = round(sum(all_scores) / len(all_scores), 1) if all_scores else None

            topic_scores: Dict[str, List[float]] = {}
            for t in all_candidate_turns:
                topic = t.subtopic or "General"
                topic_scores.setdefault(topic, []).append(t.score)

            topic_averages = {
                topic: sum(scores) / len(scores)
                for topic, scores in topic_scores.items()
                if scores
            }

            if topic_averages:
                sorted_topics = sorted(topic_averages.items(), key=lambda item: (item[1], item[0]))
                candidate.weakest_topic = sorted_topics[0][0]
                candidate.strongest_topic = sorted_topics[-1][0]
            else:
                candidate.weakest_topic = None
                candidate.strongest_topic = None
        else:
            candidate.avg_score = None
            candidate.weakest_topic = None
            candidate.strongest_topic = None

        session.commit()
        session.refresh(candidate)
        session.refresh(interview_session)

        return {
            "session_id": interview_session.session_id,
            "overall_score": interview_session.overall_score,
            "ended_at": interview_session.ended_at,
            "candidate_id": candidate.candidate_id,
            "external_id": candidate.external_id,
            "avg_score": candidate.avg_score,
            "total_sessions": candidate.total_sessions,
            "strongest_topic": candidate.strongest_topic,
            "weakest_topic": candidate.weakest_topic,
            "is_excluded": interview_session.is_excluded
        }
    finally:
        session.close()


def get_session_by_id(session_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves session metadata by session_id."""
    init_db(db_path)
    SessionFactory = get_session_factory(db_path)
    session = SessionFactory()
    try:
        s = session.query(InterviewSession).filter_by(session_id=session_id).first()
        if not s:
            return None
        return {
            "session_id": s.session_id,
            "candidate_id": s.candidate_id,
            "domain": s.domain,
            "started_at": s.started_at,
            "ended_at": s.ended_at,
            "final_summary": s.final_summary,
            "overall_score": s.overall_score,
            "is_excluded": bool(getattr(s, "is_excluded", False)),
            "turns_count": len(s.turns)
        }
    finally:
        session.close()


def get_candidate_by_external_id(external_id: str, db_path: Optional[str] = None) -> Optional[Candidate]:
    """Retrieves candidate record by external_id string."""
    init_db(db_path)
    SessionFactory = get_session_factory(db_path)
    session = SessionFactory()
    try:
        return session.query(Candidate).filter_by(external_id=external_id.strip()).first()
    finally:
        session.close()

def get_candidate_by_id(candidate_id: int, db_path: Optional[str] = None) -> Optional[Candidate]:
    """Retrieves candidate record by candidate_id integer."""
    init_db(db_path)
    SessionFactory = get_session_factory(db_path)
    session = SessionFactory()
    try:
        return session.query(Candidate).filter_by(candidate_id=candidate_id).first()
    finally:
        session.close()


def get_candidate_user_id(candidate_id: int, db_path: Optional[str] = None) -> Optional[int]:
    """Retrieves user_id associated with candidate_id if any."""
    cand = get_candidate_by_id(candidate_id, db_path=db_path)
    return cand.user_id if cand else None


def get_candidate_sessions(
    candidate_id: int,
    include_excluded: bool = False,
    db_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieves all sessions for a candidate ordered newest to oldest."""
    init_db(db_path)
    SessionFactory = get_session_factory(db_path)
    session = SessionFactory()
    try:
        query = session.query(InterviewSession).filter_by(candidate_id=candidate_id)
        if not include_excluded:
            query = query.filter(InterviewSession.is_excluded == False)

        sessions = query.order_by(desc(InterviewSession.started_at)).all()
        return [
            {
                "session_id": s.session_id,
                "domain": s.domain,
                "started_at": s.started_at,
                "ended_at": s.ended_at,
                "overall_score": s.overall_score,
                "final_summary": s.final_summary,
                "is_excluded": bool(getattr(s, "is_excluded", False)),
                "turns_count": len(s.turns)
            }
            for s in sessions
        ]
    finally:
        session.close()


def get_session_turns(session_id: int, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves all turns for a session in order."""
    init_db(db_path)
    SessionFactory = get_session_factory(db_path)
    session = SessionFactory()
    try:
        turns = (
            session.query(Turn)
            .filter_by(session_id=session_id)
            .order_by(Turn.turn_number)
            .all()
        )
        return [
            {
                "turn_id": t.turn_id,
                "session_id": t.session_id,
                "turn_number": t.turn_number,
                "subtopic": t.subtopic,
                "question_text": t.question_text,
                "candidate_answer": t.candidate_answer,
                "answer_classification": t.answer_classification,
                "score": t.score,
                "momentum_signal": t.momentum_signal,
                "judge_justification": t.judge_justification,
                "timestamp": t.timestamp
            }
            for t in turns
        ]
    finally:
        session.close()


def get_candidate_turns(candidate_id: int, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves all turns across all valid sessions for a candidate."""
    init_db(db_path)
    SessionFactory = get_session_factory(db_path)
    session = SessionFactory()
    try:
        turns = (
            session.query(Turn)
            .join(InterviewSession, Turn.session_id == InterviewSession.session_id)
            .filter(
                InterviewSession.candidate_id == candidate_id,
                InterviewSession.is_excluded == False
            )
            .order_by(Turn.timestamp)
            .all()
        )
        return [
            {
                "turn_id": t.turn_id,
                "session_id": t.session_id,
                "turn_number": t.turn_number,
                "subtopic": t.subtopic,
                "question_text": t.question_text,
                "candidate_answer": t.candidate_answer,
                "answer_classification": t.answer_classification,
                "score": t.score,
                "momentum_signal": t.momentum_signal,
                "judge_justification": t.judge_justification,
                "timestamp": t.timestamp
            }
            for t in turns
        ]
    finally:
        session.close()


def calculate_db_stats(
    candidate_id: Optional[int] = None,
    session_id: Optional[int] = None,
    db_path: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Computes analytics stats directly from SQLite for a specific session
    or across all valid sessions for a candidate.
    """
    init_db(db_path)
    SessionFactory = get_session_factory(db_path)
    session = SessionFactory()
    try:
        query = session.query(Turn).join(InterviewSession, Turn.session_id == InterviewSession.session_id)
        if session_id is not None:
            query = query.filter(Turn.session_id == session_id)
        elif candidate_id is not None:
            query = query.filter(
                InterviewSession.candidate_id == candidate_id,
                InterviewSession.is_excluded == False
            )
        else:
            return None

        turns = query.order_by(Turn.timestamp).all()
        if not turns:
            return None

        stats = {
            "total_questions": len(turns),
            "total_answers": len(turns),
            "answer_types": {
                "Normal": 0,
                "Vague": 0,
                "Incorrect": 0,
                "Hesitation": 0,
                "Knowledge_Gap": 0,
                "Evasive": 0,
                "Violation": 0
            },
            "scores": [],
            "topics_covered": set()
        }

        for t in turns:
            at = (t.answer_classification or "Normal").upper()
            if at == "NORMAL":
                stats["answer_types"]["Normal"] += 1
            elif at == "VAGUE":
                stats["answer_types"]["Vague"] += 1
            elif at == "FACTUALLY_INCORRECT":
                stats["answer_types"]["Incorrect"] += 1
            elif at == "HESITATION_SIGNAL":
                stats["answer_types"]["Hesitation"] += 1
            elif at == "KNOWLEDGE_GAP":
                stats["answer_types"]["Knowledge_Gap"] += 1
            elif at == "EVASIVE_NON_ANSWER":
                stats["answer_types"]["Evasive"] += 1
            elif at == "EVASIVE_CHALLENGE":
                stats["answer_types"]["Violation"] += 1
            else:
                stats["answer_types"]["Normal"] += 1

            if t.score is not None:
                stats["scores"].append(float(t.score))

            if t.subtopic:
                stats["topics_covered"].add(t.subtopic)

        return stats
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Cohort-Level Aggregation Functions (Phase 2 & Part 1F)
# ---------------------------------------------------------------------------

def get_cohort_topic_benchmarks(
    min_candidates: Optional[int] = None,
    db_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Average score and turn volume by subtopic across non-guest, non-excluded candidates.
    Applies privacy threshold min_candidates (groups with fewer users are omitted).
    """
    init_db(db_path)
    SessionFactory = get_session_factory(db_path)
    session = SessionFactory()
    min_req = min_candidates if min_candidates is not None else int(os.getenv("MIN_COHORT_CANDIDATES", "1"))
    try:
        query = (
            session.query(
                Turn.subtopic.label("subtopic"),
                func.count(Turn.turn_id).label("turn_count"),
                func.count(func.distinct(InterviewSession.candidate_id)).label("candidate_count"),
                func.round(func.avg(Turn.score), 1).label("avg_score")
            )
            .join(InterviewSession, Turn.session_id == InterviewSession.session_id)
            .join(Candidate, InterviewSession.candidate_id == Candidate.candidate_id)
            .outerjoin(User, Candidate.user_id == User.user_id)
            .filter(
                Turn.score.isnot(None),
                InterviewSession.is_excluded == False,
                or_(User.user_id == None, User.is_guest == False)
            )
            .group_by(Turn.subtopic)
        )

        if min_req > 1:
            query = query.having(func.count(func.distinct(InterviewSession.candidate_id)) >= min_req)

        results = query.order_by(func.avg(Turn.score).asc()).all()
        return [
            {
                "subtopic": r.subtopic or "General",
                "turn_count": int(r.turn_count),
                "candidate_count": int(r.candidate_count),
                "avg_score": float(r.avg_score) if r.avg_score is not None else 0.0
            }
            for r in results
        ]
    finally:
        session.close()


def get_cohort_subtopic_classifications(
    min_candidates: Optional[int] = None,
    db_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Answer classification frequency per subtopic campus-wide.
    Excludes guests and excluded sessions. Applies min_candidates threshold.
    """
    init_db(db_path)
    SessionFactory = get_session_factory(db_path)
    session = SessionFactory()
    min_req = min_candidates if min_candidates is not None else int(os.getenv("MIN_COHORT_CANDIDATES", "1"))
    try:
        # Check subtopics meeting privacy threshold
        subtopic_cand_counts = dict(
            session.query(
                Turn.subtopic,
                func.count(func.distinct(InterviewSession.candidate_id))
            )
            .join(InterviewSession, Turn.session_id == InterviewSession.session_id)
            .join(Candidate, InterviewSession.candidate_id == Candidate.candidate_id)
            .outerjoin(User, Candidate.user_id == User.user_id)
            .filter(
                InterviewSession.is_excluded == False,
                or_(User.user_id == None, User.is_guest == False)
            )
            .group_by(Turn.subtopic)
            .all()
        )

        results = (
            session.query(
                Turn.subtopic.label("subtopic"),
                Turn.answer_classification.label("classification"),
                func.count(Turn.turn_id).label("count")
            )
            .join(InterviewSession, Turn.session_id == InterviewSession.session_id)
            .join(Candidate, InterviewSession.candidate_id == Candidate.candidate_id)
            .outerjoin(User, Candidate.user_id == User.user_id)
            .filter(
                InterviewSession.is_excluded == False,
                or_(User.user_id == None, User.is_guest == False)
            )
            .group_by(Turn.subtopic, Turn.answer_classification)
            .order_by(Turn.subtopic, desc(func.count(Turn.turn_id)))
            .all()
        )

        subtopic_map: Dict[str, Dict[str, Any]] = {}
        for r in results:
            sub = r.subtopic or "General"
            cand_count = subtopic_cand_counts.get(r.subtopic, 0)
            if cand_count < min_req:
                continue

            cls_name = r.classification or "NORMAL"
            count = int(r.count)
            if sub not in subtopic_map:
                subtopic_map[sub] = {
                    "subtopic": sub,
                    "total_turns": 0,
                    "candidate_count": cand_count,
                    "classifications": {},
                    "dominant_classification": cls_name,
                    "dominant_count": count
                }
            subtopic_map[sub]["classifications"][cls_name] = count
            subtopic_map[sub]["total_turns"] += count
            if count > subtopic_map[sub]["dominant_count"]:
                subtopic_map[sub]["dominant_classification"] = cls_name
                subtopic_map[sub]["dominant_count"] = count

        return list(subtopic_map.values())
    finally:
        session.close()


def get_cohort_time_trend(
    min_candidates: Optional[int] = None,
    db_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Session count and average overall score trend over time (bucketed by date/day).
    Excludes guests and excluded sessions.
    """
    init_db(db_path)
    SessionFactory = get_session_factory(db_path)
    session = SessionFactory()
    min_req = min_candidates if min_candidates is not None else int(os.getenv("MIN_COHORT_CANDIDATES", "1"))
    try:
        date_bucket = func.strftime('%Y-%m-%d', InterviewSession.started_at).label("date_bucket")
        query = (
            session.query(
                date_bucket,
                func.count(InterviewSession.session_id).label("session_count"),
                func.count(func.distinct(InterviewSession.candidate_id)).label("candidate_count"),
                func.round(func.avg(InterviewSession.overall_score), 1).label("avg_overall_score")
            )
            .join(Candidate, InterviewSession.candidate_id == Candidate.candidate_id)
            .outerjoin(User, Candidate.user_id == User.user_id)
            .filter(
                InterviewSession.overall_score.isnot(None),
                InterviewSession.is_excluded == False,
                or_(User.user_id == None, User.is_guest == False)
            )
            .group_by(date_bucket)
        )

        if min_req > 1:
            query = query.having(func.count(func.distinct(InterviewSession.candidate_id)) >= min_req)

        results = query.order_by(date_bucket.asc()).all()
        return [
            {
                "date": str(r.date_bucket),
                "session_count": int(r.session_count),
                "candidate_count": int(r.candidate_count),
                "avg_overall_score": float(r.avg_overall_score) if r.avg_overall_score is not None else 0.0
            }
            for r in results
        ]
    finally:
        session.close()


def get_cohort_summary_stats(
    min_candidates: Optional[int] = None,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    High-level cohort KPI card stats across non-guest, non-excluded sessions.
    """
    init_db(db_path)
    SessionFactory = get_session_factory(db_path)
    session = SessionFactory()
    try:
        total_candidates = (
            session.query(func.count(Candidate.candidate_id))
            .outerjoin(User, Candidate.user_id == User.user_id)
            .filter(or_(User.user_id == None, User.is_guest == False))
            .scalar() or 0
        )
        total_sessions = (
            session.query(func.count(InterviewSession.session_id))
            .join(Candidate, InterviewSession.candidate_id == Candidate.candidate_id)
            .outerjoin(User, Candidate.user_id == User.user_id)
            .filter(
                InterviewSession.ended_at.isnot(None),
                InterviewSession.is_excluded == False,
                or_(User.user_id == None, User.is_guest == False)
            )
            .scalar() or 0
        )
        total_turns = (
            session.query(func.count(Turn.turn_id))
            .join(InterviewSession, Turn.session_id == InterviewSession.session_id)
            .join(Candidate, InterviewSession.candidate_id == Candidate.candidate_id)
            .outerjoin(User, Candidate.user_id == User.user_id)
            .filter(
                InterviewSession.is_excluded == False,
                or_(User.user_id == None, User.is_guest == False)
            )
            .scalar() or 0
        )
        overall_avg = (
            session.query(func.round(func.avg(Turn.score), 1))
            .join(InterviewSession, Turn.session_id == InterviewSession.session_id)
            .join(Candidate, InterviewSession.candidate_id == Candidate.candidate_id)
            .outerjoin(User, Candidate.user_id == User.user_id)
            .filter(
                Turn.score.isnot(None),
                InterviewSession.is_excluded == False,
                or_(User.user_id == None, User.is_guest == False)
            )
            .scalar()
        )

        benchmarks = get_cohort_topic_benchmarks(min_candidates=min_candidates, db_path=db_path)
        hardest_topic = benchmarks[0]["subtopic"] if benchmarks else "N/A"
        hardest_score = benchmarks[0]["avg_score"] if benchmarks else 0.0
        easiest_topic = benchmarks[-1]["subtopic"] if benchmarks else "N/A"
        easiest_score = benchmarks[-1]["avg_score"] if benchmarks else 0.0

        return {
            "total_candidates": total_candidates,
            "total_sessions": total_sessions,
            "total_turns": total_turns,
            "cohort_avg_score": float(overall_avg) if overall_avg is not None else 0.0,
            "hardest_topic": hardest_topic,
            "hardest_score": hardest_score,
            "easiest_topic": easiest_topic,
            "easiest_score": easiest_score
        }
    finally:
        session.close()
