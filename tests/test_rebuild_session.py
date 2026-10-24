"""
tests/test_rebuild_session.py - Verification that inactive/evicted sessions automatically
reconstruct from SQLite DB history and continue smoothly.
"""

import os
import json
import pytest
from unittest.mock import MagicMock, patch
from starlette.testclient import TestClient
import database
from backend.main import app
from backend.session_manager import session_manager

TEST_DB = "test_rebuild_api.db"


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
            return MockChatCompletionResponse(json.dumps({"score": 8.5, "score_reason": "Accurate"}))
        if "expert interview judge and strategist" in prompt:
            return MockChatCompletionResponse(json.dumps({
                "answer_quality_score": 8.5,
                "answer_type": "NORMAL",
                "justification": "Good explanation",
                "technical_depth": "Intermediate",
                "subtopic": "Python Programming"
            }))
        return MockChatCompletionResponse("What are the advantages of generators over lists?")

    mock_groq = MagicMock()
    mock_groq.chat.completions.create.side_effect = side_effect

    mock_syllabus = MagicMock()
    mock_syllabus.get_syllabus.return_value = ["Generators", "Asyncio"]
    mock_syllabus.get_opening_question.return_value = "What is a Python generator?"

    with patch("interview.Groq", return_value=mock_groq), \
         patch("interview.SyllabusService", return_value=mock_syllabus), \
         patch("interview.LLAMA_AVAILABLE", False):
        yield


def test_session_rebuild_after_memory_eviction(mock_llm):
    client = TestClient(app)
    reg = client.post("/api/auth/register", json={
        "email": "rebuilduser@example.com",
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
    session_id = start_res.json()["session_id"]

    # 2. Answer Turn 1
    t1_res = client.post(
        f"/api/interviews/{session_id}/answer",
        json={"answer": "A generator produces items lazily using the yield keyword."},
        headers={"X-CSRF-Token": csrf}
    )
    assert t1_res.status_code == 200
    assert t1_res.json()["status"] == "CONTINUE"

    # Verify session is currently in memory
    assert session_id in session_manager._sessions

    # 3. Simulate Server Restart / Idle Eviction by clearing in-memory registry
    session_manager._sessions.clear()
    assert session_id not in session_manager._sessions

    # 4. Submit Turn 2 — API should automatically rehydrate from SQLite turns!
    t2_res = client.post(
        f"/api/interviews/{session_id}/answer",
        json={"answer": "Generators consume O(1) memory since they compute values on the fly."},
        headers={"X-CSRF-Token": csrf}
    )
    assert t2_res.status_code == 200
    outcome = t2_res.json()
    assert outcome["status"] == "CONTINUE"

    # Verify session was re-registered in memory with rebuilt state
    assert session_id in session_manager._sessions
    entry = session_manager._sessions[session_id]
    assert entry.orchestrator.turn_count == 2
    assert len(entry.orchestrator.recent_scores) == 2
    assert entry.orchestrator.recent_scores == [8.5, 8.5]
