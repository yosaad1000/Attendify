from sqlalchemy import Column, String, Integer, ForeignKey, Float, Enum
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum

class FeeStatus(str, enum.Enum):
    PAID = "paid"
    PENDING = "pending"
    OVERDUE = "overdue"

class Student(BaseModel):
    __tablename__ = "students"
    
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    student_id = Column(String, unique=True, index=True, nullable=False)
    department_id = Column(String, ForeignKey("departments.id"), nullable=False)
    semester = Column(Integer, nullable=False)
    batch_year = Column(Integer, nullable=False)
    cgpa = Column(Float, default=0.0)
    total_credits = Column(Integer, default=0)
    fee_status = Column(Enum(FeeStatus), default=FeeStatus.PENDING)
    
    # Face recognition data
    face_encoding = Column(String, nullable=True)  # JSON string of face encoding
    
    # Relationships
    user = relationship("User", backref="student_profile")
    department = relationship("Department", back_populates="students")
    enrollments = relationship("Enrollment", back_populates="student")
    attendances = relationship("Attendance", back_populates="student")
    grades = relationship("Grade", back_populates="student")
    fees = relationship("Fee", back_populates="student")