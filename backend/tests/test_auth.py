import pytest
from backend.app.models.captcha import CaptchaChallenge
from backend.app.security.captcha import hash_captcha_text


def _create_mock_captcha(db_session, text="ABCDE"):
    from backend.app.services.auth_service import AuthService

    cid, _ = AuthService.create_captcha(db_session)
    ch = db_session.query(CaptchaChallenge).filter(CaptchaChallenge.id == cid).first()
    ch.text_hash = hash_captcha_text(text)
    db_session.commit()
    return cid


def test_successful_institute_login(client, db_session, seed_test_data):
    cid = _create_mock_captcha(db_session, "ABCDE")
    res = client.post(
        "/api/auth/login",
        json={
            "role": "INSTITUTE",
            "institute_id": "TEST001",
            "password": "Institute@123",
            "captcha_id": cid,
            "captcha_text": "abcde",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["message"] == "Login successful"
    assert data["user"]["role"] == "INSTITUTE"
    assert "csrf_token" in data
    # Verify cookies
    assert "aicte_access_token" in res.cookies
    assert "aicte_refresh_token" in res.cookies
    assert "aicte_csrf_token" in res.cookies


def test_successful_admin_login(client, db_session, seed_test_data):
    cid = _create_mock_captcha(db_session, "ADMIN1")
    res = client.post(
        "/api/auth/login",
        json={
            "role": "ADMIN",
            "identifier": "admin@aicte-india.org",
            "password": "Admin@2026!",
            "captcha_id": cid,
            "captcha_text": "admin1",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["role"] == "ADMIN"
    assert "aicte_access_token" in res.cookies


def test_wrong_role_login_rejection(client, db_session, seed_test_data):
    # Attempting to log into Institute role using Admin email
    cid = _create_mock_captcha(db_session, "ABCDE")
    res = client.post(
        "/api/auth/login",
        json={
            "role": "INSTITUTE",
            "institute_id": "NON_EXISTENT",
            "password": "Admin@2026!",
            "captcha_id": cid,
            "captcha_text": "ABCDE",
        },
    )
    assert res.status_code == 401
    assert "Invalid credentials" in res.json()["detail"]


def test_get_me_authenticated(client, db_session, seed_test_data):
    # 1. Login
    cid = _create_mock_captcha(db_session, "ABCDE")
    login_res = client.post(
        "/api/auth/login",
        json={
            "role": "INSTITUTE",
            "institute_id": "TEST001",
            "password": "Institute@123",
            "captcha_id": cid,
            "captcha_text": "ABCDE",
        },
    )
    assert login_res.status_code == 200

    # 2. Get profile
    me_res = client.get("/api/auth/me")
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == "test_inst@aicte.edu.in"
    assert me_data["role"] == "INSTITUTE"
    assert me_data["institute"]["aicte_institute_id"] == "TEST001"


def test_logout_revokes_session(client, db_session, seed_test_data):
    # 1. Login
    cid = _create_mock_captcha(db_session, "ABCDE")
    client.post(
        "/api/auth/login",
        json={
            "role": "INSTITUTE",
            "institute_id": "TEST001",
            "password": "Institute@123",
            "captcha_id": cid,
            "captcha_text": "ABCDE",
        },
    )

    # 2. Logout
    logout_res = client.post("/api/auth/logout")
    assert logout_res.status_code == 200

    # 3. /me should now fail
    me_res = client.get("/api/auth/me")
    assert me_res.status_code == 401

