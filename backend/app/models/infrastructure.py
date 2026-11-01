from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, Boolean, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from backend.app.database import Base


class InfrastructureDetail(Base):
    __tablename__ = "infrastructure_details"

    id = Column(Integer, primary_key=True, index=True)
    institute_id = Column(Integer, ForeignKey("institutes.id"), nullable=False, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False, unique=True, index=True)

    # Core Infrastructure Fields
    total_built_up_area = Column(Float, nullable=False, default=0.0)      # sq m
    land_area = Column(Float, nullable=False, default=0.0)                # sq m
    classroom_count = Column(Integer, nullable=False, default=0)
    average_classroom_area = Column(Float, nullable=False, default=0.0)   # sq m
    laboratory_count = Column(Integer, nullable=False, default=0)
    library_area = Column(Float, nullable=False, default=0.0)             # sq m
    library_books_count = Column(Integer, nullable=False, default=0)
    total_sanctioned_intake = Column(Integer, nullable=False, default=0)
    faculty_count = Column(Integer, nullable=False, default=0)
    student_count = Column(Integer, nullable=False, default=0)
    computers_available = Column(Integer, nullable=False, default=0)
    internet_bandwidth_mbps = Column(Float, nullable=False, default=0.0)  # Mbps
    barrier_free_facilities = Column(Boolean, nullable=False, default=False)
    fire_safety_installed = Column(Boolean, nullable=False, default=False)

    # Submission status: DRAFT or SUBMITTED
    status = Column(String(20), nullable=False, default="DRAFT", index=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    institute = relationship("Institute")
    application = relationship("Application", back_populates="infrastructure")

    @property
    def built_up_area_per_intake(self) -> float:
        if self.total_sanctioned_intake and self.total_sanctioned_intake > 0:
            return round(self.total_built_up_area / self.total_sanctioned_intake, 2)
        return 0.0

    @property
    def faculty_student_ratio(self) -> float:
        if self.faculty_count and self.faculty_count > 0:
            return round(self.student_count / self.faculty_count, 2)
        return 0.0

    @property
    def computer_student_ratio(self) -> float:
        if self.student_count and self.student_count > 0:
            return round(self.computers_available / self.student_count, 3)
        return 0.0

