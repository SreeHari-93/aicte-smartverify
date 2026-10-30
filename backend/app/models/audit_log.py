from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, JSON
from backend.app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, nullable=True, index=True)
    role = Column(String(50), nullable=True)
    ip_address = Column(String(45), nullable=True)  # supports IPv4 and IPv6
    user_agent = Column(String(512), nullable=True)
    action = Column(String(50), nullable=False, index=True)
    reason = Column(String(255), nullable=True)
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

