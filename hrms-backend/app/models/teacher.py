from sqlalchemy import Column, String, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship
from .base import BaseModel

class Teacher(BaseModel):
    __tablename__ = "teachers"
    
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    teacher_id = Column(String, unique=True, index=True, nullable=False)
    department_id = Column(String, ForeignKey("departments.id"), nullable=False)
    qualification = Column(String, nullable=False)
    experience_years = Column(Integer, default=0)
    specialization = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", backref="teacher_profile")
    department = relationship("Department", back_populates="teachers")
    subjects = relationship("Subject", back_populates="teacher")
    attendances_marked = relationship("Attendance", back_populates="marked_by_teacher")
    grades_given = relationship("Grade", back_populates="graded_by_teacher")