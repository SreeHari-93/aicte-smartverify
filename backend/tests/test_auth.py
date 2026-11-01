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
    assert "Incorrect login ID or password" in res.json()["detail"]


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



def test_login_wrong_password_returns_401_generic(client, db_session, seed_test_data):
    cid = _create_mock_captcha(db_session, "VALID1")
    wrong_pw = "TotallyWrongSecret!999"
    res = client.post(
        "/api/auth/login",
        json={
            "role": "INSTITUTE",
            "institute_id": "TEST001",
            "password": wrong_pw,
            "captcha_id": cid,
            "captcha_text": "VALID1",
        },
    )
    assert res.status_code == 401
    assert res.json() == {"detail": "Incorrect login ID or password"}

    # Verify no password appears in audit log
    from backend.app.models.audit_log import AuditLog
    logs = db_session.query(AuditLog).filter(AuditLog.action == "LOGIN_FAILURE").all()
    for log in logs:
        assert wrong_pw not in str(log.reason)
        assert wrong_pw not in str(log.details)


def test_login_wrong_captcha_returns_400_checked_before_password(client, db_session, seed_test_data):
    cid = _create_mock_captcha(db_session, "CORRECT")
    # Even with wrong password, wrong captcha fails FIRST with 400
    res = client.post(
        "/api/auth/login",
        json={
            "role": "INSTITUTE",
            "institute_id": "TEST001",
            "password": "WrongPassword",
            "captcha_id": cid,
            "captcha_text": "WRONG_CAPTCHA",
        },
    )
    assert res.status_code == 400
    assert res.json() == {"detail": "Captcha doesn't match"}


def test_login_rate_limit_returns_429(client, db_session, seed_test_data):
    from backend.app.security.rate_limiter import ip_limiter
    with ip_limiter.lock:
        ip_limiter.requests.clear()

    # Hit 5 times to exhaust IP limit
    for i in range(5):
        cid = _create_mock_captcha(db_session, "VALID")
        res = client.post(
            "/api/auth/login",
            json={
                "role": "INSTITUTE",
                "institute_id": f"INST_RATE_{i}",
                "password": "WrongPassword@123",
                "captcha_id": cid,
                "captcha_text": "VALID",
            },
        )
        assert res.status_code == 401

    # 6th attempt returns 429
    cid = _create_mock_captcha(db_session, "VALID")
    res6 = client.post(
        "/api/auth/login",
        json={
            "role": "INSTITUTE",
            "institute_id": "INST_RATE_6",
            "password": "WrongPassword@123",
            "captcha_id": cid,
            "captcha_text": "VALID",
        },
    )
    assert res6.status_code == 429
    assert res6.json() == {"detail": "Too many attempts. Try again in a few minutes."}
