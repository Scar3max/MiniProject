"""
tests/test_edge_cases.py - Verification of missing edge-case test requirements:
1. Stale-session auto-eviction.
2. 429 with Retry-After header and syllabus error mapping.
3. Dropped stream does not create duplicate turns.
4. Analytics with empty DB, one user, and many users.
5. Guest session expiration after guest_expires_at.
[Touches Database: test_edge_cases_*.db]
"""

import os
import json
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest
from starlette.testclient import TestClient

import database
import interview_service
from backend.main import app
from backend.session_manager import session_manager, ActiveSessionEntry


@pytest.fixture(autouse=True)
def per_test_db(request):
    db_file = f"test_edge_{request.node.name}.db"
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass
    database.init_db(db_file)
    app.state.db_path = db_file
    yield db_file
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass


class MockChatCompletionResponse:
    def __init__(self, content: str):
        self.choices = [MagicMock(message=MagicMock(content=content))]


@pytest.fixture
def mock_llm():
    def side_effect(*args, **kwargs):
        messages = kwargs.get("messages", [])
        prompt = messages[-1].get("content", "") if messages else ""
        if "begin an interview in the domain" in prompt or "Generate exactly ONE concise" in prompt:
            return MockChatCompletionResponse("What is a process?")
        if "strict numeric scorer" in prompt:
            return MockChatCompletionResponse(json.dumps({"score": 8.5, "score_reason": "Good definition."}))
        if "expert interview judge and strategist" in prompt:
            return MockChatCompletionResponse(json.dumps({
                "answer_quality_score": 8.5,
                "answer_type": "NORMAL",
                "justification": "Good definition",
                "technical_depth": "Intermediate",
                "subtopic": "Operating Systems"
            }))
        return MockChatCompletionResponse("How does a process differ from a thread?")

    mock_groq = MagicMock()
    mock_groq.chat.completions.create.side_effect = side_effect

    mock_syllabus = MagicMock()
    mock_syllabus.get_syllabus.return_value = ["Processes & Threads"]
    mock_syllabus.get_opening_question.return_value = "What is a process?"

    with patch("interview.Groq", return_value=mock_groq), \
         patch("interview.SyllabusService", return_value=mock_syllabus), \
         patch("interview.LLAMA_AVAILABLE", False):
        yield


def test_stale_session_cleanup(per_test_db):
    """
    Verifies that inactive sessions older than timeout threshold are evicted from memory.
    """
    mock_orch = MagicMock()
    mock_orch.turn_count = 1

    entry = session_manager.register_session(
        session_id=888,
        user_id=1,
        candidate_id=1,
        domain="Operating Systems",
        orchestrator=mock_orch
    )
    # Artificially set last_activity to 3 hours ago
    entry.last_activity = datetime.now(timezone.utc) - timedelta(hours=3)

    # Run cleanup with 2 hour timeout
    evicted = asyncio.run(session_manager.cleanup_idle_sessions(timeout_hours=2))
    assert evicted >= 1
    assert 888 not in session_manager._sessions


def test_429_rate_limit_and_syllabus_error_mapping(per_test_db):
    """
    Verifies:
    1. RATE_LIMIT_EXCEEDED maps to HTTP 429 with 'Retry-After: 60' header.
    2. SYLLABUS_FAILED maps to HTTP 502 Bad Gateway.
    """
    client = TestClient(app)
    reg = client.post("/api/auth/register", json={
        "email": "ratelimit_user@example.com",
        "password": "password123"
    })
    csrf = reg.json()["csrf_token"]

    # 1. Test 429 Rate Limit mapping
    with patch("interview_service.start_interview_session") as mock_start:
        mock_start.return_value = {
            "status": "ERROR",
            "error_code": "RATE_LIMIT_EXCEEDED",
            "message": "Rate limit reached during initialization."
        }
        res_429 = client.post(
            "/api/interviews",
            json={"domain": "Operating Systems"},
            headers={"X-CSRF-Token": csrf}
        )
        assert res_429.status_code == 429
        assert res_429.headers.get("retry-after") == "60"
        assert "Rate limit reached" in res_429.json()["detail"]

    # 2. Test 502 Syllabus Failure mapping
    with patch("interview_service.start_interview_session") as mock_start:
        mock_start.return_value = {
            "status": "ERROR",
            "error_code": "SYLLABUS_FAILED",
            "message": "Failed to create interview syllabus."
        }
        res_502 = client.post(
            "/api/interviews",
            json={"domain": "Invalid Domain XYZ"},
            headers={"X-CSRF-Token": csrf}
        )
        assert res_502.status_code == 502
        assert "Failed to generate syllabus" in res_502.json()["detail"]


def test_dropped_stream_creates_no_duplicate_turn(mock_llm, per_test_db):
    """
    Verifies that client disconnection or aborted stream does not duplicate turn records in the DB.
    """
    client = TestClient(app)
    reg = client.post("/api/auth/register", json={
        "email": "stream_user@example.com",
        "password": "password123"
    })
    csrf = reg.json()["csrf_token"]

    start_res = client.post(
        "/api/interviews",
        json={"domain": "Operating Systems"},
        headers={"X-CSRF-Token": csrf}
    )
    session_id = start_res.json()["session_id"]

    # Process first answer via regular endpoint
    client.post(
        f"/api/interviews/{session_id}/answer",
        json={"answer": "A process has its own address space."},
        headers={"X-CSRF-Token": csrf}
    )

    turns_before = database.get_session_turns(session_id, db_path=per_test_db)
    assert len(turns_before) == 1

    # Simulate dropped stream request by reading only initial events then closing connection
    with client.stream(
        "POST",
        f"/api/interviews/{session_id}/answer/stream",
        json={"answer": "Threads share process address space."},
        headers={"X-CSRF-Token": csrf}
    ) as response:
        for line in response.iter_lines():
            if line:
                break

    # Verify turns count is exactly 2 (no duplicate phantom turns recorded)
    turns_after = database.get_session_turns(session_id, db_path=per_test_db)
    assert len(turns_after) == 2


def test_analytics_empty_db_one_user_and_many_users(per_test_db):
    """
    Verifies analytics behavior across 3 data volume tiers:
    Tier 1: Empty database (clean zero state, cohort unavailable).
    Tier 2: Single candidate (user stats populated, cohort unavailable due to privacy < 5).
    Tier 3: Many candidates (>= 5, cohort benchmarks fully available).
    """
    client = TestClient(app)

    # --- Tier 1: Empty DB ---
    # Register user but record 0 interviews
    reg1 = client.post("/api/auth/register", json={"email": "u1@example.com", "password": "password123"})
    sum_empty = client.get("/api/analytics/summary").json()
    assert sum_empty["total_sessions"] == 0
    assert sum_empty["stats"]["total_answers"] == 0

    cohort_empty = client.get("/api/analytics/cohort").json()
    assert cohort_empty["available"] is False
    assert cohort_empty["total_candidates"] == 1  # Exactly 1 registered candidate with 0 turns

    # --- Tier 2: One User With Turns ---
    cand1 = database.get_or_create_candidate_for_user(user_id=reg1.json()["user"]["user_id"], db_path=per_test_db)[0]
    s1 = database.start_session(candidate_id=cand1.candidate_id, domain="Operating Systems", db_path=per_test_db)
    database.record_turn(session_id=s1, turn_number=1, subtopic="Processes", question_text="Q1", candidate_answer="A1", score=8.0, answer_classification="NORMAL", db_path=per_test_db)
    database.finish_session(session_id=s1, overall_score=8.0, db_path=per_test_db)

    sum_user1 = client.get("/api/analytics/summary").json()
    assert sum_user1["total_sessions"] == 1
    assert sum_user1["avg_score"] == 8.0

    cohort_tier2 = client.get("/api/analytics/cohort").json()
    assert cohort_tier2["available"] is False
    assert cohort_tier2["total_candidates"] == 1

    # --- Tier 3: Many Candidates (reach 5 distinct candidates) ---
    for i in range(2, 6):
        c_i, _ = database.get_or_create_candidate(f"tier3-user-{i}", db_path=per_test_db)
        s_i = database.start_session(candidate_id=c_i.candidate_id, domain="Operating Systems", db_path=per_test_db)
        database.record_turn(session_id=s_i, turn_number=1, subtopic="Processes", question_text="Q", candidate_answer="A", score=9.0, answer_classification="NORMAL", db_path=per_test_db)
        database.finish_session(session_id=s_i, overall_score=9.0, db_path=per_test_db)

    cohort_tier3 = client.get("/api/analytics/cohort").json()
    assert cohort_tier3["available"] is True
    assert cohort_tier3["summary"]["total_candidates"] == 5
    assert len(cohort_tier3["topic_benchmarks"]) >= 1


def test_guest_session_expiration(per_test_db):
    """
    Verifies that an expired guest session is rejected with HTTP 401 Unauthorized.
    """
    client = TestClient(app)

    # 1. Create a guest user expired 1 hour ago
    expired_time = datetime.now(timezone.utc) - timedelta(hours=1)
    user = database.create_user(
        email="expired_guest@guest.local",
        password_hash=None,
        role="guest",
        is_guest=True,
        guest_expires_at=expired_time,
        db_path=per_test_db
    )

    from backend.security import create_access_token
    expired_token = create_access_token(data={"sub": str(user.user_id), "role": "guest"})

    client.cookies.set("access_token", expired_token)

    res = client.get("/api/auth/me")
    assert res.status_code == 401
    assert "Guest session expired" in res.json()["detail"]
