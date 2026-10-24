"""
interview_service.py - Pure Python service for interview session management and orchestration.
No Streamlit dependencies. Used by both Streamlit app and FastAPI backend.
"""

from typing import Dict, Any, Optional, Tuple, List
import database
from interview import InterviewOrchestrator
import analytics_service

FEEDBACK_BADGE_MAP = {
    "NORMAL": {"label": "Good Answer", "category": "normal"},
    "Normal": {"label": "Good Answer", "category": "normal"},
    "VAGUE": {"label": "Vague", "category": "vague"},
    "Vague": {"label": "Vague", "category": "vague"},
    "FACTUALLY_INCORRECT": {"label": "Incorrect", "category": "incorrect"},
    "Factually_Incorrect": {"label": "Incorrect", "category": "incorrect"},
    "HESITATION_SIGNAL": {"label": "Hesitation", "category": "hesitation"},
    "KNOWLEDGE_GAP": {"label": "Knowledge Gap", "category": "knowledge-gap"},
    "EVASIVE_NON_ANSWER": {"label": "Evasive", "category": "evasive"},
    "EVASIVE_CHALLENGE": {"label": "Violation", "category": "violation"},
}


def get_feedback_badge_info(answer_type: Optional[str]) -> Dict[str, str]:
    """Returns label and category for a given answer classification."""
    if not answer_type:
        return {"label": "Analyzed", "category": "normal"}
    return FEEDBACK_BADGE_MAP.get(answer_type, {"label": answer_type.replace("_", " ").title(), "category": "normal"})


def _compute_current_difficulty(chatbot: InterviewOrchestrator) -> str:
    """Computes dynamic technical difficulty based on performance trajectory."""
    if hasattr(chatbot, "recent_scores") and chatbot.recent_scores:
        recent = chatbot.recent_scores[-3:]
        avg = sum(recent) / len(recent)
        if avg >= 8.0:
            return "Advanced"
        elif avg >= 5.0:
            return "Intermediate"
        else:
            return "Fundamental"
    return "Fundamental"


def start_interview_session(
    selected_domain: str,
    candidate_identifier: Optional[str] = None,
    user_id: Optional[int] = None,
    difficulty: Optional[str] = None,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Initializes candidate, session, and orchestrator; generates opening L0 question.
    Returns session and initial question payload.
    """
    # 1. Resolve candidate
    if user_id is not None:
        candidate, _ = database.get_or_create_candidate_for_user(user_id=user_id, db_path=db_path)
    else:
        candidate, _ = database.get_or_create_candidate(candidate_identifier, db_path=db_path)

    # 2. Start session in DB
    session_id = database.start_session(
        candidate_id=candidate.candidate_id,
        domain=selected_domain,
        db_path=db_path
    )

    # 3. Create orchestrator
    chatbot = InterviewOrchestrator(
        domain=selected_domain,
        candidate_id=candidate.candidate_id,
        session_id=session_id,
        db_path=db_path
    )

    # Check initialization health
    if chatbot.rate_limit_hit:
        return {
            "status": "ERROR",
            "error_code": "RATE_LIMIT_EXCEEDED",
            "message": "Rate limit reached during initialization. Please try again later.",
            "session_id": session_id,
            "chatbot": chatbot
        }

    if not chatbot.current_topic:
        return {
            "status": "ERROR",
            "error_code": "SYLLABUS_FAILED",
            "message": "Failed to create interview syllabus. Please try again.",
            "session_id": session_id,
            "chatbot": chatbot
        }

    # Generate first question
    question = chatbot.start_interview()

    if isinstance(question, dict) and question.get("status") == "TERMINATED":
        return {
            "status": "ERROR",
            "error_code": "RATE_LIMIT_EXCEEDED",
            "message": "Rate limit reached during opening question. Please try again later.",
            "session_id": session_id,
            "chatbot": chatbot
        }

    return {
        "status": "STARTED",
        "session_id": session_id,
        "candidate_id": candidate.candidate_id,
        "external_id": candidate.external_id,
        "domain": selected_domain,
        "current_subtopic": chatbot.current_topic,
        "current_difficulty": "Fundamental",
        "question": question,
        "turn_number": 1,
        "chatbot": chatbot
    }


def process_candidate_answer(
    chatbot: InterviewOrchestrator,
    user_answer: str
) -> Dict[str, Any]:
    """
    Processes candidate answer through InterviewOrchestrator and returns structured turn outcome.
    """
    clean_answer = user_answer.strip()

    # Check for quit
    if clean_answer.lower() in ["quit", "exit"]:
        diff = _compute_current_difficulty(chatbot)
        return {
            "status": "TERMINATED",
            "reason": "UserQuit",
            "message": "Thank you for participating! The interview has ended. 🎉",
            "next_question": None,
            "analysis": None,
            "score": None,
            "feedback_badge": None,
            "turn_number": chatbot.turn_count,
            "current_difficulty": diff
        }

    # Run orchestrator turn
    response = chatbot.process_user_answer(clean_answer)

    analysis = response.get("analysis", {})
    answer_type = analysis.get("answer_type", "Normal") if isinstance(analysis, dict) else "Normal"
    score = analysis.get("score_used") if isinstance(analysis, dict) else None

    badge = get_feedback_badge_info(answer_type)
    current_diff = _compute_current_difficulty(chatbot)

    if response.get("status") == "TERMINATED":
        reason = response.get("reason", "Concluded")
        if reason == "RateLimit":
            end_message = "🚨 Rate limit reached. Thank you for your time!"
        elif reason == "SyllabusFinished":
            end_message = "🎉 That covers all topics! Thank you for your time!"
        else:
            end_message = "Thank you for your time. The interview has concluded."

        return {
            "status": "TERMINATED",
            "reason": reason,
            "message": end_message,
            "next_question": None,
            "analysis": analysis,
            "score": score,
            "answer_type": (analysis or {}).get("answer_type"),
            "feedback_badge": badge,
            "label": badge.get("label"),
            "category": badge.get("category"),
            "turn_number": chatbot.turn_count,
            "current_subtopic": chatbot.current_topic,
            "current_difficulty": current_diff
        }

    return {
        "status": "CONTINUE",
        "reason": None,
        "next_question": response.get("next_question"),
        "analysis": analysis,
        "score": score,
        "answer_type": (analysis or {}).get("answer_type"),
        "feedback_badge": badge,
        "label": badge.get("label"),
        "category": badge.get("category"),
        "turn_number": chatbot.turn_count,
        "current_subtopic": chatbot.current_topic,
        "current_difficulty": current_diff
    }


def finalize_interview_session(
    session_id: int,
    chatbot: Optional[InterviewOrchestrator] = None,
    candidate_id: Optional[int] = None,
    is_excluded: bool = False,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Calculates final stats, closes session row, and recomputes candidate aggregates.
    """
    stats = analytics_service.calculate_interview_stats(
        candidate_id=candidate_id,
        session_id=session_id,
        chatbot=chatbot,
        db_path=db_path
    )
    final_summary = analytics_service.generate_ai_feedback(stats)
    final_summary_items = analytics_service.generate_ai_feedback_items(stats)

    overall_score = None
    if stats and stats.get("scores"):
        scores = stats["scores"]
        overall_score = round(sum(scores) / len(scores), 1)

    if chatbot:
        summary_result = chatbot.end_session(final_summary=final_summary, overall_score=overall_score)
    else:
        summary_result = database.finish_session(
            session_id=session_id,
            final_summary=final_summary,
            overall_score=overall_score,
            is_excluded=is_excluded,
            db_path=db_path
        )

    return {
        "session_id": session_id,
        "overall_score": overall_score,
        "final_summary": final_summary,
        "final_summary_items": final_summary_items,
        "stats": stats,
        "summary_result": summary_result
    }


def rebuild_orchestrator_from_db(
    session_id: int,
    db_path: Optional[str] = None
) -> Optional[InterviewOrchestrator]:
    """
    Rebuilds an InterviewOrchestrator state from historical DB turns when not present in memory.
    Ensures session resumption matches uninterrupted runs.
    """
    session_info = database.get_session_by_id(session_id, db_path=db_path)
    if not session_info:
        return None

    # Fetch turns in order
    turns = database.get_session_turns(session_id, db_path=db_path)

    # Initialize fresh orchestrator for this domain
    orch = InterviewOrchestrator(
        domain=session_info["domain"],
        candidate_id=session_info["candidate_id"],
        session_id=session_id,
        db_path=db_path
    )

    if not turns:
        return orch

    # Replay turn history into orchestrator state
    orch.conversation_history = []
    orch.recent_scores = []
    orch.turn_count = len(turns)

    # Reconstruct topic syllabus position and streak tracking
    last_subtopic = turns[-1].get("subtopic") or session_info["domain"]
    orch.current_topic = last_subtopic
    orch.last_question = turns[-1].get("question_text", "")

    # Count questions in the current topic
    questions_in_topic = sum(1 for t in turns if (t.get("subtopic") or session_info["domain"]) == last_subtopic)
    orch.questions_in_current_topic = questions_in_topic

    # Rebuild conversation history and score trajectory
    hesitation_streak = 0
    vague_streak = 0
    poor_types = ("VAGUE", "FACTUALLY_INCORRECT", "EVASIVE_NON_ANSWER", "EVASIVE_CHALLENGE", "HESITATION_SIGNAL", "KNOWLEDGE_GAP")

    for t in turns:
        q_text = t.get("question_text", "")
        a_text = t.get("candidate_answer", "")
        orch.conversation_history.append({"role": "assistant", "content": q_text})
        orch.conversation_history.append({"role": "user", "content": a_text})

        score_val = t.get("score")
        if score_val is not None:
            orch.recent_scores.append(float(score_val))

        # Track streak
        cls_type = (t.get("answer_classification") or "NORMAL").upper()
        if cls_type == "HESITATION_SIGNAL":
            hesitation_streak += 1
        else:
            hesitation_streak = 0

        if cls_type in poor_types:
            vague_streak += 1
        else:
            vague_streak = 0

    orch.hesitation_streak = hesitation_streak
    orch.vague_streak = vague_streak

    # Pop already visited topics from syllabus if present
    covered_topics = set(t.get("subtopic") for t in turns if t.get("subtopic"))
    orch.topic_syllabus = [topic for topic in orch.topic_syllabus if topic not in covered_topics]

    return orch
