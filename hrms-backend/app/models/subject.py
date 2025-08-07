from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from .base import BaseModel

class Subject(BaseModel):
    __tablename__ = "subjects"
    
    name = Column(String, nullable=False)
    code = Column(String, unique=True, index=True, nullable=False)
    department_id = Column(String, ForeignKey("departments.id"), nullable=False)
    teacher_id = Column(String, ForeignKey("teachers.id"), nullable=True)
    semester = Column(Integer, nullable=False)
    credits = Column(Integer, nullable=False)
    is_elective = Column(Boolean, default=False)
    description = Column(Text, nullable=True)
    syllabus_url = Column(String, nullable=True)
    
    # Google Classroom integration
    classroom_id = Column(String, nullable=True)
    
    # Relationships
    department = relationship("Department", back_populates="subjects")
    teacher = relationship("Teacher", back_populates="subjects")
    enrollments = relationship("Enrollment", back_populates="subject")
    attendances = relationship("Attendance", back_populates="subject")
    grades = relationship("Grade", back_populates="subject")