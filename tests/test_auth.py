"""
tests/test_auth.py - Verification of registration, login, guest access, session verification, and logout.
"""

import os
import pytest
from starlette.testclient import TestClient
import database
from backend.main import app

TEST_DB = "test_auth_api.db"


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


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_register_success(client):
    res = client.post("/api/auth/register", json={
        "email": "testuser@example.com",
        "password": "secretpassword123",
        "full_name": "Test User"
    })
    assert res.status_code == 201
    data = res.json()
    assert data["user"]["email"] == "testuser@example.com"
    assert data["user"]["full_name"] == "Test User"
    assert data["user"]["is_guest"] is False
    assert "csrf_token" in data

    # Check cookies
    cookies = client.cookies
    assert "access_token" in cookies
    assert "csrf_token" in cookies

    # Verify candidate row was created
    cand = database.get_candidate_by_id(1, db_path=TEST_DB)
    assert cand is not None
    assert cand.user_id == data["user"]["user_id"]
    assert cand.external_id.startswith(f"user-{data['user']['user_id']}-")


def test_register_duplicate_email(client):
    client.post("/api/auth/register", json={
        "email": "dup@example.com",
        "password": "password123"
    })
    res2 = client.post("/api/auth/register", json={
        "email": "dup@example.com",
        "password": "password123"
    })
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"]


def test_login_success_and_failure(client):
    # Register first
    client.post("/api/auth/register", json={
        "email": "loginuser@example.com",
        "password": "mypassword123"
    })

    # Clear cookies to simulate fresh client
    client.cookies.clear()

    # Wrong password
    bad_res = client.post("/api/auth/login", json={
        "email": "loginuser@example.com",
        "password": "wrongpassword"
    })
    assert bad_res.status_code == 401
    assert "Invalid email or password" in bad_res.json()["detail"]

    # Correct password
    good_res = client.post("/api/auth/login", json={
        "email": "loginuser@example.com",
        "password": "mypassword123"
    })
    assert good_res.status_code == 200
    assert good_res.json()["user"]["email"] == "loginuser@example.com"
    assert "access_token" in client.cookies


def test_guest_session_lifecycle(client):
    res = client.post("/api/auth/guest")
    assert res.status_code == 201
    data = res.json()
    assert data["user"]["is_guest"] is True
    assert data["user"]["role"] == "guest"
    assert "guest-" in data["user"]["email"]

    # Verify me endpoint recognizes guest
    me_res = client.get("/api/auth/me")
    assert me_res.status_code == 200
    assert me_res.json()["is_guest"] is True


def test_auth_me_and_logout(client):
    reg = client.post("/api/auth/register", json={
        "email": "me@example.com",
        "password": "password123",
        "full_name": "Me Myself"
    })
    csrf = reg.json()["csrf_token"]

    # Call /auth/me
    me_res = client.get("/api/auth/me")
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "me@example.com"
    assert me_res.json()["profile"]["consent_save_sessions"] is True

    # Call logout
    logout_res = client.post("/api/auth/logout")
    assert logout_res.status_code == 200

    # Next call should be unauthorized
    unauth_res = client.get("/api/auth/me")
    assert unauth_res.status_code == 401


def test_auth_rate_limiting(client):
    import backend.security
    # Temporarily enable rate limiter in testing
    old_testing = os.environ.get("TESTING")
    os.environ.pop("TESTING", None)
    backend.security._RATE_LIMIT_STORE.clear()

    try:
        # 1. Register rate limit (max 10)
        for i in range(10):
            res = client.post("/api/auth/register", json={
                "email": f"rate_reg_{i}@test.com",
                "password": "password123"
            })
            assert res.status_code in (201, 409)
        # 11th should be 429
        res_limit = client.post("/api/auth/register", json={
            "email": "rate_reg_blocked@test.com",
            "password": "password123"
        })
        assert res_limit.status_code == 429

        # 2. Login rate limit (max 15)
        for i in range(15):
            res = client.post("/api/auth/login", json={
                "email": "nonexistent@test.com",
                "password": "wrongpassword"
            })
            assert res.status_code == 401
        # 16th should be 429
        res_login_limit = client.post("/api/auth/login", json={
            "email": "nonexistent@test.com",
            "password": "wrongpassword"
        })
        assert res_login_limit.status_code == 429

        # 3. Guest rate limit (max 20)
        for i in range(20):
            res = client.post("/api/auth/guest")
            assert res.status_code == 201
        # 21st should be 429
        res_guest_limit = client.post("/api/auth/guest")
        assert res_guest_limit.status_code == 429
    finally:
        if old_testing is not None:
            os.environ["TESTING"] = old_testing
        backend.security._RATE_LIMIT_STORE.clear()
