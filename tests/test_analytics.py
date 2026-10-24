"""
tests/test_analytics.py - Verification of candidate analytics, cohort privacy threshold,
and exclusion filtering.
"""

import os
import pytest
from starlette.testclient import TestClient
import database
from backend.main import app

TEST_DB = "test_analytics_api.db"


@pytest.fixture(autouse=True)
def setup_teardown_db():
    if os.path.exists(TEST_DB):
        try:
            os.remove(TEST_DB)
        except Exception:
            pass
    database.init_db(TEST_DB)
    app.state.db_path = TEST_DB
    yield
    if os.path.exists(TEST_DB):
        try:
            os.remove(TEST_DB)
        except Exception:
            pass


def test_candidate_summary_and_trends():
    client = TestClient(app)
    reg = client.post("/api/auth/register", json={
        "email": "analytics_user@example.com",
        "password": "password123"
    })
    user_id = reg.json()["user"]["user_id"]
    cand = database.get_or_create_candidate_for_user(user_id=user_id, db_path=TEST_DB)[0]

    # Populate a session and turns directly in DB
    s_id = database.start_session(candidate_id=cand.candidate_id, domain="Operating Systems", db_path=TEST_DB)
    database.record_turn(
        session_id=s_id,
        turn_number=1,
        subtopic="Processes",
        question_text="What is a process?",
        candidate_answer="A program in execution.",
        score=9.0,
        answer_classification="NORMAL",
        db_path=TEST_DB
    )
    database.record_turn(
        session_id=s_id,
        turn_number=2,
        subtopic="Memory Management",
        question_text="What is paging?",
        candidate_answer="Splitting memory into pages.",
        score=7.0,
        answer_classification="NORMAL",
        db_path=TEST_DB
    )
    database.finish_session(session_id=s_id, overall_score=8.0, final_summary="Good session", db_path=TEST_DB)

    # 1. Summary
    sum_res = client.get("/api/analytics/summary")
    assert sum_res.status_code == 200
    s_data = sum_res.json()
    assert s_data["total_sessions"] == 1
    assert s_data["avg_score"] == 8.0
    assert s_data["stats"]["total_answers"] == 2
    assert s_data["strongest_topic"] == "Processes"

    # 2. Trends
    trends_res = client.get("/api/analytics/trends")
    assert trends_res.status_code == 200
    t_data = trends_res.json()
    assert len(t_data["sessions"]) == 1
    assert len(t_data["timeline"]) == 2


def test_cohort_privacy_threshold_and_exclusions():
    client = TestClient(app)
    reg = client.post("/api/auth/register", json={
        "email": "cohort_user1@example.com",
        "password": "password123"
    })

    # With only 1 candidate, cohort endpoint should reject/suppress data due to privacy threshold (< 5)
    cohort_res1 = client.get("/api/analytics/cohort")
    assert cohort_res1.status_code == 200
    c_data1 = cohort_res1.json()
    assert c_data1["available"] is False
    assert "at least 5 distinct candidates" in c_data1["message"]
    assert c_data1["min_required"] == 5

    # Create 4 more candidates to reach 5 candidates total
    for i in range(2, 6):
        c_reg, _ = database.get_or_create_candidate(f"user-cohort-{i}", db_path=TEST_DB)
        s_id = database.start_session(candidate_id=c_reg.candidate_id, domain="Computer Networks", db_path=TEST_DB)
        database.record_turn(
            session_id=s_id,
            turn_number=1,
            subtopic="TCP/IP",
            question_text="What is TCP?",
            candidate_answer="A reliable stream protocol.",
            score=8.0 + (i * 0.2),
            answer_classification="NORMAL",
            db_path=TEST_DB
        )
        database.finish_session(session_id=s_id, overall_score=8.5, db_path=TEST_DB)

    # Add an excluded session (consent_save_sessions = False)
    c_reg_exc, _ = database.get_or_create_candidate("user-excluded", db_path=TEST_DB)
    s_exc_id = database.start_session(candidate_id=c_reg_exc.candidate_id, domain="Computer Networks", db_path=TEST_DB)
    database.record_turn(
        session_id=s_exc_id,
        turn_number=1,
        subtopic="TCP/IP",
        question_text="Excluded question?",
        candidate_answer="Excluded answer",
        score=2.0,
        answer_classification="NORMAL",
        db_path=TEST_DB
    )
    database.finish_session(session_id=s_exc_id, is_excluded=True, db_path=TEST_DB)

    # Now we have >= 5 candidates -> cohort data is available!
    cohort_res2 = client.get("/api/analytics/cohort")
    assert cohort_res2.status_code == 200
    c_data2 = cohort_res2.json()
    assert c_data2["available"] is True
    assert "summary" in c_data2
    assert "topic_benchmarks" in c_data2
    # Verify excluded session turn was omitted from benchmarks
    benchmarks = c_data2["topic_benchmarks"]
    tcp_bench = next((b for b in benchmarks if b["subtopic"] == "TCP/IP"), None)
    if tcp_bench:
        # Average score should reflect the 4 good turns (8.4-9.0), not the 2.0 excluded turn
        assert tcp_bench["avg_score"] >= 8.0
