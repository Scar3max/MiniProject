"""
tests/test_golden_replay.py - Verifies deterministic replay of golden interview transcripts.
Ensures parity across domains, user quit, and syllabus completion flows.
"""

import os
import pytest
import database
import interview_service
from tests.replay_harness import DeterministicReplayHarness

TEST_DB_PATH = "test_replay_golden.db"


@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass
    database.init_db(TEST_DB_PATH)
    yield
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass


def test_golden_replay_python():
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "fixture_domain_python.json")
    harness = DeterministicReplayHarness(fixture_path)
    result = harness.run_replay(db_path=TEST_DB_PATH)

    # Assertions
    assert len(result["outcomes"]) == 3
    for outcome in result["outcomes"]:
        assert outcome["status"] == "CONTINUE"
        assert outcome["score"] is not None
        assert outcome["feedback_badge"]["label"] == "Good Answer"

    stats = result["stats"]
    assert stats["total_answers"] == 3
    assert stats["answer_types"]["Normal"] == 3
    assert result["final_res"]["overall_score"] == 8.8

    # Check database persistence
    db_turns = result["db_turns"]
    assert len(db_turns) == 3
    assert db_turns[0]["score"] == 8.5
    assert db_turns[1]["score"] == 9.0
    assert db_turns[2]["score"] == 9.0


def test_golden_replay_ml_quit():
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "fixture_domain_ml_quit.json")
    harness = DeterministicReplayHarness(fixture_path)
    result = harness.run_replay(db_path=TEST_DB_PATH)

    assert len(result["outcomes"]) == 2
    assert result["outcomes"][0]["status"] == "CONTINUE"
    assert result["outcomes"][1]["status"] == "TERMINATED"
    assert result["outcomes"][1]["reason"] == "UserQuit"

    stats = result["stats"]
    assert stats["total_answers"] == 1
    assert result["final_res"]["overall_score"] == 8.0


def test_golden_replay_os_syllabus_finished():
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "fixture_domain_os_syllabus_finished.json")
    harness = DeterministicReplayHarness(fixture_path)
    result = harness.run_replay(db_path=TEST_DB_PATH)

    assert len(result["outcomes"]) == 3
    assert result["outcomes"][0]["status"] == "CONTINUE"
    assert result["outcomes"][1]["status"] == "CONTINUE"
    assert result["outcomes"][2]["status"] == "TERMINATED"
    assert result["outcomes"][2]["reason"] == "SyllabusFinished"

    stats = result["stats"]
    assert stats["total_answers"] == 3
    assert result["final_res"]["overall_score"] == 8.7


def test_rebuild_orchestrator_parity():
    # First run python replay to produce turns in DB
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "fixture_domain_python.json")
    harness = DeterministicReplayHarness(fixture_path)
    result = harness.run_replay(db_path=TEST_DB_PATH)
    session_id = result["session_id"]

    # Rebuild from DB
    rebuilt = interview_service.rebuild_orchestrator_from_db(session_id, db_path=TEST_DB_PATH)
    assert rebuilt is not None
    assert rebuilt.turn_count == 3
    assert len(rebuilt.recent_scores) == 3
    assert rebuilt.recent_scores == [8.5, 9.0, 9.0]
    assert len(rebuilt.conversation_history) == 6  # 3 assistant + 3 user
