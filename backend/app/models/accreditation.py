from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database import Base


class Accreditation(Base):
    __tablename__ = "accreditations"

    id = Column(Integer, primary_key=True, index=True)
    institute_id = Column(Integer, ForeignKey("institutes.id"), unique=True, nullable=False, index=True)
    nirf_rank = Column(Integer, nullable=False)  # e.g., 73
    naac_grade = Column(String(50), nullable=False)  # e.g., "A++ (CGPA 3.62)"
    nba_accredited_courses = Column(Integer, default=8, nullable=False)
    college_code = Column(String(100), nullable=False)  # e.g. "C-26922 / TNEA 2718"
    location_address = Column(Text, nullable=False)
    phone = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    institute = relationship("Institute")

