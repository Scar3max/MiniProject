"""
tests/test_settings.py - Verification of password updates and GDPR data deletion.
"""

import os
import pytest
from starlette.testclient import TestClient
import database
from backend.main import app

TEST_DB = "test_settings_api.db"


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


def test_password_change():
    client = TestClient(app)
    reg = client.post("/api/auth/register", json={
        "email": "pwduser@example.com",
        "password": "oldpassword123"
    })
    csrf = reg.json()["csrf_token"]

    # Wrong current password
    bad_res = client.put(
        "/api/settings/password",
        json={"current_password": "wrongpassword", "new_password": "newpassword456"},
        headers={"X-CSRF-Token": csrf}
    )
    assert bad_res.status_code == 400
    assert "Current password is incorrect" in bad_res.json()["detail"]

    # Correct current password
    good_res = client.put(
        "/api/settings/password",
        json={"current_password": "oldpassword123", "new_password": "newpassword456"},
        headers={"X-CSRF-Token": csrf}
    )
    assert good_res.status_code == 200

    # Verify login with new password
    client.cookies.clear()
    login_res = client.post("/api/auth/login", json={
        "email": "pwduser@example.com",
        "password": "newpassword456"
    })
    assert login_res.status_code == 200


def test_gdpr_data_deletion():
    client = TestClient(app)
    reg = client.post("/api/auth/register", json={
        "email": "delete_me@example.com",
        "password": "password123"
    })
    user_id = reg.json()["user"]["user_id"]
    csrf = reg.json()["csrf_token"]

    # Create session and turn for user
    cand = database.get_or_create_candidate_for_user(user_id=user_id, db_path=TEST_DB)[0]
    s_id = database.start_session(candidate_id=cand.candidate_id, domain="Python", db_path=TEST_DB)
    database.record_turn(session_id=s_id, turn_number=1, subtopic="Python", question_text="Q?", candidate_answer="A", score=9.0, answer_classification="NORMAL", db_path=TEST_DB)

    # Wrong confirmation string
    bad_del = client.request(
        "DELETE",
        "/api/settings/data",
        json={"confirmation": "wrong"},
        headers={"X-CSRF-Token": csrf}
    )
    assert bad_del.status_code == 400

    # Correct confirmation string
    good_del = client.request(
        "DELETE",
        "/api/settings/data",
        json={"confirmation": "DELETE MY DATA"},
        headers={"X-CSRF-Token": csrf}
    )
    assert good_del.status_code == 200
    assert good_del.json()["status"] == "deleted"

    # Verify user and candidate are completely wiped from DB
    assert database.get_user_by_id(user_id, db_path=TEST_DB) is None
    assert database.get_candidate_by_id(cand.candidate_id, db_path=TEST_DB) is None
    assert database.get_session_by_id(s_id, db_path=TEST_DB) is None
