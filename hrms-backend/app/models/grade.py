from sqlalchemy import Column, String, ForeignKey, Float, Integer, Enum, DateTime, Text
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum

class ExamType(str, enum.Enum):
    MIDTERM = "midterm"
    FINAL = "final"
    ASSIGNMENT = "assignment"
    QUIZ = "quiz"
    PROJECT = "project"
    LAB = "lab"

class Grade(BaseModel):
    __tablename__ = "grades"
    
    student_id = Column(String, ForeignKey("students.id"), nullable=False)
    subject_id = Column(String, ForeignKey("subjects.id"), nullable=False)
    exam_type = Column(Enum(ExamType), nullable=False)
    marks_obtained = Column(Float, nullable=False)
    max_marks = Column(Float, nullable=False)
    grade_letter = Column(String(2), nullable=True)  # A+, A, B+, etc.
    grade_points = Column(Float, nullable=True)  # 4.0 scale
    graded_by = Column(String, ForeignKey("teachers.id"), nullable=False)
    graded_at = Column(DateTime, nullable=False)
    comments = Column(Text, nullable=True)
    
    # Relationships
    student = relationship("Student", back_populates="grades")
    subject = relationship("Subject", back_populates="grades")
    graded_by_teacher = relationship("Teacher", back_populates="grades_given")