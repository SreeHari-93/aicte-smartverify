from datetime import datetime, timedelta, timezone
import pytest
from backend.app.models.captcha import CaptchaChallenge
from backend.app.models.user import User
from backend.app.security.captcha import hash_captcha_text


def _create_mock_captcha(db_session, text="VALID"):
    from backend.app.services.auth_service import AuthService

    cid, _ = AuthService.create_captcha(db_session)
    ch = db_session.query(CaptchaChallenge).filter(CaptchaChallenge.id == cid).first()
    ch.text_hash = hash_captcha_text(text)
    db_session.commit()
    return cid


def test_account_lockout_after_five_failed_attempts(client, db_session, seed_test_data):
    inst_user = seed_test_data["inst_user"]

    # Perform 4 failed attempts
    for attempt in range(1, 5):
        cid = _create_mock_captcha(db_session, "VALID")
        res = client.post(
            "/api/auth/login",
            json={
                "role": "INSTITUTE",
                "institute_id": "TEST001",
                "password": "WrongPassword@999",
                "captcha_id": cid,
                "captcha_text": "VALID",
            },
        )
        assert res.status_code == 401
        assert "Incorrect login ID or password" in res.json()["detail"]

    # 5th failed attempt should trigger lockout (423 Locked)
    cid = _create_mock_captcha(db_session, "VALID")
    res5 = client.post(
        "/api/auth/login",
        json={
            "role": "INSTITUTE",
            "institute_id": "TEST001",
            "password": "WrongPassword@999",
            "captcha_id": cid,
            "captcha_text": "VALID",
        },
    )
    assert res5.status_code == 423
    data = res5.json()["detail"]
    assert data["locked"] is True
    assert data["remaining_seconds"] > 0

    # 6th attempt with CORRECT password should STILL be locked out
    cid = _create_mock_captcha(db_session, "VALID")
    res6 = client.post(
        "/api/auth/login",
        json={
            "role": "INSTITUTE",
            "institute_id": "TEST001",
            "password": "Institute@123",  # correct password
            "captcha_id": cid,
            "captcha_text": "VALID",
        },
    )
    assert res6.status_code == 423
    assert res6.json()["detail"]["locked"] is True

