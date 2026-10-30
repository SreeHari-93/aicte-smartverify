from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime
from backend.app.database import Base


class CaptchaChallenge(Base):
    __tablename__ = "captcha_challenges"

    id = Column(String(36), primary_key=True, index=True)
    text_hash = Column(String(64), nullable=False)  # SHA-256 hash
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

