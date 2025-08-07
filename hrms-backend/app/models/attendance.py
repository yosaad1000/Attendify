from sqlalchemy import Column, String, ForeignKey, Date, Enum, DateTime, Text
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum

class AttendanceStatus(str, enum.Enum):
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    EXCUSED = "excused"

class Attendance(BaseModel):
    __tablename__ = "attendances"
    
    student_id = Column(String, ForeignKey("students.id"), nullable=False)
    subject_id = Column(String, ForeignKey("subjects.id"), nullable=False)
    date = Column(Date, nullable=False)
    status = Column(Enum(AttendanceStatus), nullable=False)
    marked_by = Column(String, ForeignKey("teachers.id"), nullable=False)
    marked_at = Column(DateTime, nullable=False)
    notes = Column(Text, nullable=True)
    
    # Face recognition data
    confidence_score = Column(String, nullable=True)  # For AI-marked attendance
    
    # Relationships
    student = relationship("Student", back_populates="attendances")
    subject = relationship("Subject", back_populates="attendances")
    marked_by_teacher = relationship("Teacher", back_populates="attendances_marked")