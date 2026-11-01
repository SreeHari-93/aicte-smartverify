from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON
from backend.app.database import Base


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    case_id = Column(String(100), nullable=False, index=True)
    recipient_role = Column(String(50), nullable=False, index=True)
    due_date = Column(DateTime, nullable=True)
    offset_days = Column(Integer, nullable=False, default=0)
    details = Column(JSON, nullable=True)
    status = Column(String(50), default="PENDING", nullable=False, index=True)

    # In-app alert messaging fields
    title = Column(String(255), nullable=True)
    message = Column(Text, nullable=True)
    link = Column(String(255), nullable=True)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    institute_id = Column(Integer, nullable=True, index=True)
    recipient_user_id = Column(Integer, nullable=True, index=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
