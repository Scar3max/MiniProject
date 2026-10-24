"""
backend/routers/analytics.py - Candidate and cohort performance analytics endpoints.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Request, Depends, HTTPException
import database
import analytics_service
from backend.config import DATABASE_PATH, MIN_COHORT_CANDIDATES
from backend.security import get_current_user

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("")
@router.get("/summary")
async def get_candidate_summary(
    request: Request,
    user: database.User = Depends(get_current_user)
):
    """Returns candidate's lifetime metrics, topic performance, and score distribution."""
    db_path = getattr(request.app.state, "db_path", DATABASE_PATH)
    cand, _ = database.get_or_create_candidate_for_user(user_id=user.user_id, db_path=db_path)

    stats = analytics_service.calculate_interview_stats(
        candidate_id=cand.candidate_id,
        db_path=db_path
    )

    return {
        "candidate_id": cand.candidate_id,
        "external_id": cand.external_id,
        "avg_score": cand.avg_score,
        "total_sessions": cand.total_sessions,
        "strongest_topic": cand.strongest_topic,
        "weakest_topic": cand.weakest_topic,
        "stats": stats or {
            "total_questions": 0,
            "total_answers": 0,
            "answer_types": {
                "Normal": 0, "Vague": 0, "Incorrect": 0,
                "Hesitation": 0, "Knowledge_Gap": 0, "Evasive": 0, "Violation": 0
            },
            "scores": [],
            "topics_covered": []
        }
    }


@router.get("/trends")
async def get_candidate_trends(
    request: Request,
    user: database.User = Depends(get_current_user)
):
    """Returns candidate's turn score timeline and session history for chart rendering."""
    db_path = getattr(request.app.state, "db_path", DATABASE_PATH)
    cand, _ = database.get_or_create_candidate_for_user(user_id=user.user_id, db_path=db_path)

    sessions = database.get_candidate_sessions(
        candidate_id=cand.candidate_id,
        include_excluded=False,
        db_path=db_path
    )

    turns = database.get_candidate_turns(
        candidate_id=cand.candidate_id,
        db_path=db_path
    )

    timeline = [
        {
            "turn_id": t["turn_id"],
            "session_id": t["session_id"],
            "subtopic": t["subtopic"],
            "score": t["score"],
            "answer_classification": t["answer_classification"],
            "created_at": str(t.get("timestamp")) if t.get("timestamp") else t.get("created_at")
        }
        for t in turns if t["score"] is not None
    ]

    return {
        "candidate_id": cand.candidate_id,
        "sessions": sessions,
        "timeline": timeline
    }


@router.get("/topics")
async def get_candidate_topics(
    request: Request,
    user: database.User = Depends(get_current_user)
):
    """Returns candidate's topic-level score breakdowns and question counts."""
    db_path = getattr(request.app.state, "db_path", DATABASE_PATH)
    cand, _ = database.get_or_create_candidate_for_user(user_id=user.user_id, db_path=db_path)
    turns = database.get_candidate_turns(candidate_id=cand.candidate_id, db_path=db_path)

    topic_map: Dict[str, List[float]] = {}
    for t in turns:
        sub = t.get("subtopic") or "General"
        sc = t.get("score")
        if sc is not None:
            topic_map.setdefault(sub, []).append(float(sc))

    breakdown = [
        {
            "topic": t,
            "turns_count": len(scores),
            "average_score": round(sum(scores) / len(scores), 1) if scores else 0.0
        }
        for t, scores in topic_map.items()
    ]
    breakdown.sort(key=lambda x: x["average_score"], reverse=True)

    return {
        "candidate_id": cand.candidate_id,
        "topics": breakdown
    }


@router.get("/classifications")
async def get_candidate_classifications(
    request: Request,
    user: database.User = Depends(get_current_user)
):
    """Returns distribution of answer classifications across candidate's turns."""
    db_path = getattr(request.app.state, "db_path", DATABASE_PATH)
    cand, _ = database.get_or_create_candidate_for_user(user_id=user.user_id, db_path=db_path)
    stats = analytics_service.calculate_interview_stats(candidate_id=cand.candidate_id, db_path=db_path)
    answer_types = (stats or {}).get("answer_types", {})
    total = sum(answer_types.values()) or 1

    distribution = [
        {
            "category": k,
            "count": v,
            "percentage": round((v / total) * 100, 1)
        }
        for k, v in answer_types.items()
    ]

    return {
        "candidate_id": cand.candidate_id,
        "total_answers": sum(answer_types.values()),
        "distribution": distribution
    }


@router.get("/timeline")
async def get_candidate_timeline(
    request: Request,
    user: database.User = Depends(get_current_user)
):
    """Returns chronological score timeline points formatted for line chart visualization."""
    db_path = getattr(request.app.state, "db_path", DATABASE_PATH)
    cand, _ = database.get_or_create_candidate_for_user(user_id=user.user_id, db_path=db_path)
    turns = database.get_candidate_turns(candidate_id=cand.candidate_id, db_path=db_path)

    points = [
        {
            "index": idx,
            "turn_id": t["turn_id"],
            "session_id": t["session_id"],
            "topic": t["subtopic"],
            "score": t["score"],
            "classification": t["answer_classification"],
            "timestamp": str(t.get("timestamp") or "")
        }
        for idx, t in enumerate(turns, 1)
        if t.get("score") is not None
    ]

    return {
        "candidate_id": cand.candidate_id,
        "points": points
    }


@router.get("/cohort")
async def get_cohort_analytics(
    request: Request,
    user: database.User = Depends(get_current_user)
):
    """
    Returns campus-wide cohort analytics benchmarks.
    Applies privacy threshold check: requires at least MIN_COHORT_CANDIDATES (default 5).
    """
    db_path = getattr(request.app.state, "db_path", DATABASE_PATH)

    summary = database.get_cohort_summary_stats(db_path=db_path)
    total_candidates = summary.get("total_candidates", 0)

    # Privacy threshold check
    if total_candidates < MIN_COHORT_CANDIDATES:
        return {
            "available": False,
            "total_candidates": total_candidates,
            "min_required": MIN_COHORT_CANDIDATES,
            "message": f"Cohort benchmark analytics requires data from at least {MIN_COHORT_CANDIDATES} distinct candidates to preserve privacy (currently {total_candidates})."
        }

    benchmarks = database.get_cohort_topic_benchmarks(
        min_candidates=MIN_COHORT_CANDIDATES,
        db_path=db_path
    )
    classifications = database.get_cohort_subtopic_classifications(
        min_candidates=MIN_COHORT_CANDIDATES,
        db_path=db_path
    )
    time_trend = database.get_cohort_time_trend(db_path=db_path)

    return {
        "available": True,
        "summary": summary,
        "topic_benchmarks": benchmarks,
        "subtopic_classifications": classifications,
        "time_trend": time_trend
    }
