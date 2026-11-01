from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, JSON
from backend.app.database import Base


class SchedulerRunLog(Base):
    __tablename__ = "scheduler_run_logs"

    id = Column(Integer, primary_key=True, index=True)
    run_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    simulated_clock = Column(DateTime, nullable=True)
    items_checked = Column(Integer, default=0, nullable=False)
    alerts_created = Column(Integer, default=0, nullable=False)
    escalations_triggered = Column(Integer, default=0, nullable=False)
    status = Column(String(50), default="SUCCESS", nullable=False)
    duration_ms = Column(Integer, default=0, nullable=False)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

