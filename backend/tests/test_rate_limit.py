import pytest
from backend.app.models.captcha import CaptchaChallenge
from backend.app.security.captcha import hash_captcha_text
from backend.app.security.rate_limiter import ip_limiter


def _create_mock_captcha(db_session, text="VALID"):
    from backend.app.services.auth_service import AuthService

    cid, _ = AuthService.create_captcha(db_session)
    ch = db_session.query(CaptchaChallenge).filter(CaptchaChallenge.id == cid).first()
    ch.text_hash = hash_captcha_text(text)
    db_session.commit()
    return cid


def test_ip_rate_limiting(client, db_session, seed_test_data):
    # Ensure limiters are clean
    with ip_limiter.lock:
        ip_limiter.requests.clear()

    # Perform 5 rapid requests from the client IP with different usernames so account lockout is not triggered
    for i in range(5):
        cid = _create_mock_captcha(db_session, "VALID")
        res = client.post(
            "/api/auth/login",
            json={
                "role": "INSTITUTE",
                "institute_id": f"TEST_INST_{i}",
                "password": "WrongPassword@123",
                "captcha_id": cid,
                "captcha_text": "VALID",
            },
        )
        assert res.status_code == 401

    # The 6th request should be blocked by IP rate limit (429 Too Many Requests)
    cid = _create_mock_captcha(db_session, "VALID")
    res6 = client.post(
        "/api/auth/login",
        json={
            "role": "INSTITUTE",
            "institute_id": "TEST_INST_6",
            "password": "WrongPassword@123",
            "captcha_id": cid,
            "captcha_text": "VALID",
        },
    )
    assert res6.status_code == 429
    assert "Too many attempts. Try again in a few minutes." in res6.json()["detail"]
    assert "Retry-After" in res6.headers
