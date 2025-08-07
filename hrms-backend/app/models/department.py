from sqlalchemy import Column, String, Text
from sqlalchemy.orm import relationship
from .base import BaseModel

class Department(BaseModel):
    __tablename__ = "departments"
    
    name = Column(String, nullable=False)
    code = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    hod_id = Column(String, nullable=True)  # Head of Department
    
    # Relationships
    students = relationship("Student", back_populates="department")
    teachers = relationship("Teacher", back_populates="department")
    subjects = relationship("Subject", back_populates="department")