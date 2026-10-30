from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    institute_id = Column(Integer, ForeignKey("institutes.id"), nullable=False, index=True)
    report_type = Column(String(100), nullable=False)  # Application Summary, Certificate Expiry, Validation Summary
    format = Column(String(20), nullable=False)  # PDF, CSV
    date_range = Column(String(100), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    application_id = Column(String(100), nullable=True, index=True)
    language = Column(String(10), default="en", nullable=True)
    generated_by = Column(String(100), default="INSTITUTE", nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    institute = relationship("Institute")
