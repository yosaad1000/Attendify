from sqlalchemy import Column, String, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum

class EnrollmentStatus(str, enum.Enum):
    ENROLLED = "enrolled"
    DROPPED = "dropped"
    COMPLETED = "completed"

class Enrollment(BaseModel):
    __tablename__ = "enrollments"
    
    student_id = Column(String, ForeignKey("students.id"), nullable=False)
    subject_id = Column(String, ForeignKey("subjects.id"), nullable=False)
    status = Column(Enum(EnrollmentStatus), default=EnrollmentStatus.ENROLLED)
    enrollment_date = Column(DateTime, nullable=False)
    completion_date = Column(DateTime, nullable=True)
    
    # Relationships
    student = relationship("Student", back_populates="enrollments")
    subject = relationship("Subject", back_populates="enrollments")