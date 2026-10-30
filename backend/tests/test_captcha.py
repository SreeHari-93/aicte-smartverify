from datetime import datetime, timedelta, timezone
import pytest
from backend.app.models.captcha import CaptchaChallenge
from backend.app.security.captcha import hash_captcha_text
from backend.app.services.auth_service import AuthService


def test_captcha_generation(client):
    response = client.get("/api/auth/captcha")
    assert response.status_code == 200
    data = response.json()
    assert "captcha_id" in data
    assert "image_base64" in data
    assert data["image_base64"].startswith("data:image/png;base64,")


def test_captcha_verification_success(db_session):
    text = "G3C1M"
    cid, _ = AuthService.create_captcha(db_session)

    # Update challenge to have our known text hash
    challenge = db_session.query(CaptchaChallenge).filter(CaptchaChallenge.id == cid).first()
    challenge.text_hash = hash_captcha_text(text)
    db_session.commit()

    # Case-insensitive check
    assert AuthService.verify_and_consume_captcha(db_session, cid, "g3c1m") is True


def test_captcha_reuse_fails(db_session):
    text = "K9P4X"
    cid, _ = AuthService.create_captcha(db_session)

    challenge = db_session.query(CaptchaChallenge).filter(CaptchaChallenge.id == cid).first()
    challenge.text_hash = hash_captcha_text(text)
    db_session.commit()

    # First attempt succeeds
    assert AuthService.verify_and_consume_captcha(db_session, cid, text) is True
    # Second attempt MUST fail because it is one-time use
    assert AuthService.verify_and_consume_captcha(db_session, cid, text) is False


def test_captcha_expiry(db_session):
    text = "EXPIRE1"
    cid, _ = AuthService.create_captcha(db_session)

    challenge = db_session.query(CaptchaChallenge).filter(CaptchaChallenge.id == cid).first()
    challenge.text_hash = hash_captcha_text(text)
    # Set expiration in the past
    challenge.expires_at = datetime.now(timezone.utc) - timedelta(seconds=10)
    db_session.commit()

    # Verification must fail due to expiry
    assert AuthService.verify_and_consume_captcha(db_session, cid, text) is False

