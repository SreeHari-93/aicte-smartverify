from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON
from backend.app.database import Base


class NotificationRule(Base):
    __tablename__ = "notification_rules"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(100), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    offsets_days = Column(JSON, nullable=False, default=list)  # list of integer day offsets
    recipient_role = Column(String(50), nullable=False, default="INSTITUTE")
    channel = Column(String(50), nullable=False, default="BOTH")  # IN_APP, EMAIL, BOTH
    message_template = Column(Text, nullable=False)
    is_enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

