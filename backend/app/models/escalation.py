from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from backend.app.database import Base


class EscalationMatrix(Base):
    __tablename__ = "escalation_matrix"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    level = Column(Integer, nullable=False, default=1)
    days_overdue = Column(Integer, nullable=False, default=1)
    designated_role = Column(String(50), nullable=False, default="REGIONAL_OFFICER")
    is_enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class EscalationRecord(Base):
    __tablename__ = "escalation_records"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(String(100), nullable=False, index=True)
    case_type = Column(String(50), nullable=False, index=True)  # workflow, undertaking, evc, validity
    event_type = Column(String(100), nullable=False, index=True)
    level = Column(Integer, nullable=False)
    notified_role = Column(String(50), nullable=False)
    notified_user_email = Column(String(255), nullable=True)
    days_overdue = Column(Integer, nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False, index=True)  # ACTIVE, AUTO_CLOSED, RESOLVED
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

