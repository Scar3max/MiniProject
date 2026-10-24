"""
tests/test_streamlit_proof.py - Proof Streamlit still starts and completes one real interview.
Uses a separate test database so interview_history.db is never touched.
"""

import os
import sys
import shutil
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import pytest
from streamlit.testing.v1 import AppTest
import database

TEMP_DB = "test_streamlit_proof.db"

@pytest.mark.live
def test_streamlit_starts_and_completes_interview():
    # Ensure clean test DB
    if os.path.exists(TEMP_DB):
        os.remove(TEMP_DB)
    abs_temp_db = os.path.abspath(TEMP_DB)
    os.environ["INTERVIEW_DB_PATH"] = abs_temp_db
    database.DEFAULT_DB_PATH = abs_temp_db

    try:
        database.init_db(abs_temp_db)

        # 1. Initialize Streamlit App
        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "streamlit_app.py"))
        at = AppTest.from_file(script_path, default_timeout=60)
        at.run()
        assert not at.exception
        assert at.session_state.interview_started is False

        # 2. Enter candidate ID and domain, then click Start Interview
        at.text_input[0].input("streamlit_proof_user")
        at.text_input[1].input("Python Programming")
        at.button[0].click().run()

        assert not at.exception
        assert at.session_state.interview_started is True
        assert len(at.session_state.messages) >= 1
        opening_q = at.session_state.messages[0]["content"]
        assert len(opening_q) > 5
        print(f"\n[STREAMLIT PROOF] Opening Question: {opening_q}")

        # 3. Candidate answers turn 1
        turn1_answer = "A list is mutable while a tuple is immutable, meaning tuple contents cannot be changed after creation."
        at.chat_input[0].set_value(turn1_answer).run()

        assert not at.exception
        assert len(at.session_state.messages) >= 3  # [bot Q1, user A1, bot Q2]
        followup_q = at.session_state.messages[-1]["content"]
        print(f"[STREAMLIT PROOF] Candidate Turn 1 Answer: {turn1_answer}")
        print(f"[STREAMLIT PROOF] Follow-up Question: {followup_q}")
        assert at.session_state.interview_ended is False

        # 4. Candidate types 'quit' to complete the interview
        at.chat_input[0].set_value("quit").run()

        assert not at.exception
        assert at.session_state.interview_ended is True
        assert at.session_state.session_closed is True
        print(f"[STREAMLIT PROOF] Interview completed cleanly! Ended={at.session_state.interview_ended}, Closed={at.session_state.session_closed}")

        # 5. Verify database records
        cand_id = at.session_state.candidate_id
        sessions = database.get_candidate_sessions(cand_id, db_path=abs_temp_db)
        assert len(sessions) == 1
        sess = sessions[0]
        assert sess["domain"] == "Python Programming"
        assert sess["turns_count"] >= 1
        print(f"[STREAMLIT PROOF] Database verified: Session ID {sess['session_id']}, Domain: {sess['domain']}, Turns: {sess['turns_count']}, Overall Score: {sess['overall_score']}")

    finally:
        if os.path.exists(TEMP_DB):
            try:
                os.remove(TEMP_DB)
            except Exception:
                pass

if __name__ == "__main__":
    test_streamlit_starts_and_completes_interview()
