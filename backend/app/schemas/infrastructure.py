from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class InfrastructureDetailBase(BaseModel):
    total_built_up_area: float = Field(default=0.0, ge=0.0, description="Total built-up area in sq m")
    land_area: float = Field(default=0.0, ge=0.0, description="Total land area in sq m")
    classroom_count: int = Field(default=0, ge=0, description="Number of instructional classrooms")
    average_classroom_area: float = Field(default=0.0, ge=0.0, description="Average classroom area in sq m")
    laboratory_count: int = Field(default=0, ge=0, description="Number of laboratories and workshops")
    library_area: float = Field(default=0.0, ge=0.0, description="Central library reading & stack area in sq m")
    library_books_count: int = Field(default=0, ge=0, description="Number of technical library books/volumes")
    total_sanctioned_intake: int = Field(default=0, ge=0, description="Total sanctioned student intake")
    faculty_count: int = Field(default=0, ge=0, description="Total full-time approved faculty count")
    student_count: int = Field(default=0, ge=0, description="Total enrolled student count")
    computers_available: int = Field(default=0, ge=0, description="Computers available for student use")
    internet_bandwidth_mbps: float = Field(default=0.0, ge=0.0, description="Dedicated internet bandwidth in Mbps")
    barrier_free_facilities: bool = Field(default=False, description="Barrier-free facilities for Divyangjan (ramps/lifts)")
    fire_safety_installed: bool = Field(default=False, description="Fire safety and firefighting equipment installed")


class InfrastructureDetailCreate(InfrastructureDetailBase):
    status: str = Field(default="DRAFT", description="DRAFT or SUBMITTED")


class InfrastructureDetailUpdate(InfrastructureDetailBase):
    status: Optional[str] = Field(default=None, description="DRAFT or SUBMITTED")


class InfrastructureDetailOut(InfrastructureDetailBase):
    id: int
    institute_id: int
    application_id: int
    status: str
    built_up_area_per_intake: float
    faculty_student_ratio: float
    computer_student_ratio: float
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

