"""
tests/test_interviews.py - Verification of interview lifecycle: start, turn processing,
idempotency, SSE streaming, and finalization.
"""

import os
import json
import pytest
from unittest.mock import MagicMock, patch
from starlette.testclient import TestClient
import database
from backend.main import app

TEST_DB = "test_interviews_api.db"


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
    groq_call_count = [0]

    def side_effect(*args, **kwargs):
        groq_call_count[0] += 1
        messages = kwargs.get("messages", [])
        prompt = messages[-1].get("content", "") if messages else ""
        if "begin an interview in the domain" in prompt or "Generate exactly ONE concise" in prompt:
            return MockChatCompletionResponse("What is a decorator in Python?")
        if "strict numeric scorer" in prompt:
            return MockChatCompletionResponse(json.dumps({"score": 9.0, "score_reason": "Accurate explanation."}))
        if "expert interview judge and strategist" in prompt:
            return MockChatCompletionResponse(json.dumps({
                "answer_quality_score": 9.0,
                "answer_type": "NORMAL",
                "justification": "Accurate explanation of decorator closures.",
                "technical_depth": "Advanced",
                "subtopic": "Python Programming"
            }))
        return MockChatCompletionResponse("How does functools.wraps preserve function metadata?")

    mock_groq = MagicMock()
    mock_groq.chat.completions.create.side_effect = side_effect

    mock_syllabus = MagicMock()
    mock_syllabus.get_syllabus.return_value = ["Decorators & Functions", "Memory Management"]
    mock_syllabus.get_opening_question.return_value = "What is a decorator in Python?"

    with patch("interview.Groq", return_value=mock_groq), \
         patch("interview.SyllabusService", return_value=mock_syllabus), \
         patch("interview.LLAMA_AVAILABLE", False):
        yield {"call_count": groq_call_count}


def test_interview_full_turn_and_idempotency(mock_llm):
    client = TestClient(app)
    reg = client.post("/api/auth/register", json={
        "email": "candidate@example.com",
        "password": "password123"
    })
    csrf = reg.json()["csrf_token"]

    # 1. Start interview
    start_res = client.post(
        "/api/interviews",
        json={"domain": "Python Programming"},
        headers={"X-CSRF-Token": csrf}
    )
    assert start_res.status_code == 201
    s_data = start_res.json()
    session_id = s_data["session_id"]
    assert s_data["question"] == "What is a decorator in Python?"
    assert s_data["turn_number"] == 1

    calls_before = mock_llm["call_count"][0]

    # 2. Answer question
    ans_res = client.post(
        f"/api/interviews/{session_id}/answer",
        json={"answer": "A decorator wraps another function to extend its behavior dynamically."},
        headers={"X-CSRF-Token": csrf}
    )
    assert ans_res.status_code == 200
    outcome = ans_res.json()
    assert outcome["status"] == "CONTINUE"
    assert outcome["score"] == 9.0
    assert outcome["feedback_badge"]["label"] == "Good Answer"
    assert "functools.wraps" in outcome["next_question"]

    calls_after_first = mock_llm["call_count"][0]
    assert calls_after_first > calls_before

    # 3. Idempotency test: submit the exact same answer again
    retry_res = client.post(
        f"/api/interviews/{session_id}/answer",
        json={"answer": "A decorator wraps another function to extend its behavior dynamically."},
        headers={"X-CSRF-Token": csrf}
    )
    assert retry_res.status_code == 200
    retry_outcome = retry_res.json()
    assert retry_outcome == outcome
    # Verify no additional LLM calls were made
    assert mock_llm["call_count"][0] == calls_after_first


def test_interview_sse_streaming(mock_llm):
    client = TestClient(app)
    reg = client.post("/api/auth/register", json={
        "email": "sseuser@example.com",
        "password": "password123"
    })
    csrf = reg.json()["csrf_token"]

    start_res = client.post(
        "/api/interviews",
        json={"domain": "Python Programming"},
        headers={"X-CSRF-Token": csrf}
    )
    session_id = start_res.json()["session_id"]

    # Call streaming endpoint
    stream_res = client.post(
        f"/api/interviews/{session_id}/answer/stream",
        json={"answer": "A decorator takes a function as argument and returns an inner wrapper."},
        headers={"X-CSRF-Token": csrf}
    )
    assert stream_res.status_code == 200
    assert "text/event-stream" in stream_res.headers["content-type"]

    body = stream_res.text
    assert "event: status" in body
    assert "analyzing_answer" in body
    assert "event: result" in body
    assert '"status": "CONTINUE"' in body


def test_end_interview_early(mock_llm):
    client = TestClient(app)
    reg = client.post("/api/auth/register", json={
        "email": "earlyend@example.com",
        "password": "password123"
    })
    csrf = reg.json()["csrf_token"]

    start_res = client.post(
        "/api/interviews",
        json={"domain": "Python Programming"},
        headers={"X-CSRF-Token": csrf}
    )
    session_id = start_res.json()["session_id"]

    # Answer one turn
    client.post(
        f"/api/interviews/{session_id}/answer",
        json={"answer": "Decorators wrap functions."},
        headers={"X-CSRF-Token": csrf}
    )

    # End interview explicitly
    end_res = client.post(
        f"/api/interviews/{session_id}/end",
        headers={"X-CSRF-Token": csrf}
    )
    assert end_res.status_code == 200
    end_data = end_res.json()
    assert end_data["status"] == "TERMINATED"
    assert end_data["overall_score"] == 9.0
    assert "Interview concluded" in end_data["message"]
