"""
tests/test_ownership.py - Verification of strict ownership isolation and CSRF defenses.
[Touches Database: test_ownership_api.db]
"""

import os
import json
import pytest
from unittest.mock import MagicMock, patch
from starlette.testclient import TestClient
import database
from backend.main import app

TEST_DB = "test_ownership_api.db"


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


class MockChatCompletionResponse:
    def __init__(self, content: str):
        self.choices = [MagicMock(message=MagicMock(content=content))]


@pytest.fixture
def mock_llm():
    def side_effect(*args, **kwargs):
        messages = kwargs.get("messages", [])
        prompt = messages[-1].get("content", "") if messages else ""
        if "begin an interview in the domain" in prompt or "Generate exactly ONE concise" in prompt:
            return MockChatCompletionResponse("What is a Python generator?")
        if "strict numeric scorer" in prompt:
            return MockChatCompletionResponse(json.dumps({"score": 8.0, "score_reason": "Good"}))
        if "expert interview judge and strategist" in prompt:
            return MockChatCompletionResponse(json.dumps({
                "answer_quality_score": 8.0,
                "answer_type": "NORMAL",
                "justification": "Good",
                "technical_depth": "Intermediate",
                "subtopic": "Python Programming"
            }))
        return MockChatCompletionResponse("Next question?")

    mock_groq = MagicMock()
    mock_groq.chat.completions.create.side_effect = side_effect

    mock_syllabus = MagicMock()
    mock_syllabus.get_syllabus.return_value = ["Generators & Iterators"]
    mock_syllabus.get_opening_question.return_value = "What is a Python generator?"

    with patch("interview.Groq", return_value=mock_groq), \
         patch("interview.SyllabusService", return_value=mock_syllabus), \
         patch("interview.LLAMA_AVAILABLE", False):
        yield


def test_session_ownership_all_endpoints(mock_llm):
    """
    Verifies that User B receives 403 Forbidden on EVERY endpoint taking a session id,
    and nonexistent sessions receive 404 Not Found.
    Endpoints:
      1. GET /api/interviews/{id}
      2. POST /api/interviews/{id}/answer
      3. POST /api/interviews/{id}/answer/stream
      4. POST /api/interviews/{id}/end
    """
    # 1. User A registers and starts a session
    client_a = TestClient(app)
    reg_a = client_a.post("/api/auth/register", json={
        "email": "owner_a@example.com",
        "password": "password123"
    })
    csrf_a = reg_a.json()["csrf_token"]

    start_res = client_a.post(
        "/api/interviews",
        json={"domain": "Python Programming"},
        headers={"X-CSRF-Token": csrf_a}
    )
    assert start_res.status_code == 201
    session_id = start_res.json()["session_id"]

    # 2. User B registers
    client_b = TestClient(app)
    reg_b = client_b.post("/api/auth/register", json={
        "email": "intruder_b@example.com",
        "password": "password123"
    })
    csrf_b = reg_b.json()["csrf_token"]

    # --- 403 Forbidden Checks for User B on User A's session ---

    # Endpoint 1: GET /api/interviews/{id}
    res_get = client_b.get(f"/api/interviews/{session_id}")
    assert res_get.status_code == 403
    assert "Access denied" in res_get.json()["detail"]

    # Endpoint 2: POST /api/interviews/{id}/answer
    res_ans = client_b.post(
        f"/api/interviews/{session_id}/answer",
        json={"answer": "Trying to answer another user's session."},
        headers={"X-CSRF-Token": csrf_b}
    )
    assert res_ans.status_code == 403
    assert "Access denied" in res_ans.json()["detail"]

    # Endpoint 3: POST /api/interviews/{id}/answer/stream
    res_stream = client_b.post(
        f"/api/interviews/{session_id}/answer/stream",
        json={"answer": "Trying to stream answer on another user's session."},
        headers={"X-CSRF-Token": csrf_b}
    )
    assert res_stream.status_code == 403
    assert "Access denied" in res_stream.json()["detail"]

    # Endpoint 4: POST /api/interviews/{id}/end
    res_end = client_b.post(
        f"/api/interviews/{session_id}/end",
        headers={"X-CSRF-Token": csrf_b}
    )
    assert res_end.status_code == 403
    assert "Access denied" in res_end.json()["detail"]

    # --- 404 Not Found Checks for Nonexistent Session ID 999999 ---
    nonexistent_id = 999999
    assert client_a.get(f"/api/interviews/{nonexistent_id}").status_code == 404
    assert client_a.post(
        f"/api/interviews/{nonexistent_id}/answer",
        json={"answer": "test"},
        headers={"X-CSRF-Token": csrf_a}
    ).status_code == 404
    assert client_a.post(
        f"/api/interviews/{nonexistent_id}/answer/stream",
        json={"answer": "test"},
        headers={"X-CSRF-Token": csrf_a}
    ).status_code == 404
    assert client_a.post(
        f"/api/interviews/{nonexistent_id}/end",
        headers={"X-CSRF-Token": csrf_a}
    ).status_code == 404

    # --- Verification: User A retains valid ownership access ---
    valid_detail = client_a.get(f"/api/interviews/{session_id}")
    assert valid_detail.status_code == 200
    assert valid_detail.json()["session"]["session_id"] == session_id


def test_csrf_token_protection(mock_llm):
    """
    Verifies that state-changing requests without or with mismatched CSRF headers are rejected with 403.
    """
    client = TestClient(app)
    reg = client.post("/api/auth/register", json={
        "email": "csrfuser@example.com",
        "password": "password123"
    })
    valid_csrf = reg.json()["csrf_token"]

    # State-changing request with NO CSRF header -> 403 Forbidden
    no_csrf = client.post("/api/interviews", json={"domain": "Python Programming"})
    assert no_csrf.status_code == 403
    assert "CSRF token validation failed" in no_csrf.json()["detail"]

    # State-changing request with WRONG CSRF header -> 403 Forbidden
    bad_csrf = client.post(
        "/api/interviews",
        json={"domain": "Python Programming"},
        headers={"X-CSRF-Token": "invalid_fake_token"}
    )
    assert bad_csrf.status_code == 403

    # With valid CSRF header -> 201 Created
    good_csrf = client.post(
        "/api/interviews",
        json={"domain": "Python Programming"},
        headers={"X-CSRF-Token": valid_csrf}
    )
    assert good_csrf.status_code == 201
