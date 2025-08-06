# services/database_interface.py
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

class DatabaseInterface(ABC):
    """Abstract interface for database operations"""
    
    @abstractmethod
    def get_student(self, student_id: str):
        """Get a student by ID"""
        pass
    
    @abstractmethod
    def get_all_students(self) -> List:
        """Get all students"""
        pass
    
    @abstractmethod
    def add_student(self, student) -> bool:
        """Add a new student"""
        pass
    
    @abstractmethod
    def update_student(self, student) -> bool:
        """Update an existing student"""
        pass
    
    @abstractmethod
    def student_exists(self, student_id: str) -> bool:
        """Check if student exists"""
        pass
    
    @abstractmethod
    def get_all_departments(self) -> List:
        """Get all departments"""
        pass
    
    @abstractmethod
    def add_department(self, department) -> bool:
        """Add a new department"""
        pass
    
    @abstractmethod
    def update_department(self, dept_id: str, updates: Dict[str, Any]) -> bool:
        """Update a department"""
        pass
    
    @abstractmethod
    def get_all_faculty(self) -> List:
        """Get all faculty members"""
        pass
    
    @abstractmethod
    def get_faculty_by_id(self, faculty_id: str):
        """Get faculty by ID"""
        pass
    
    @abstractmethod
    def add_faculty(self, faculty) -> bool:
        """Add a new faculty member"""
        pass
    
    @abstractmethod
    def update_faculty(self, faculty_id: str, updates: Dict[str, Any]) -> bool:
        """Update a faculty member"""
        pass
    
    @abstractmethod
    def delete_faculty(self, faculty_id: str) -> bool:
        """Delete a faculty member"""
        pass
    
    @abstractmethod
    def get_all_subjects(self) -> List:
        """Get all subjects"""
        pass
    
    @abstractmethod
    def get_subject_by_id(self, subject_id: str):
        """Get subject by ID"""
        pass
    
    @abstractmethod
    def add_subject(self, subject) -> bool:
        """Add a new subject"""
        pass
    
    @abstractmethod
    def update_subject(self, subject_id: str, updates: Dict[str, Any]) -> bool:
        """Update a subject"""
        pass
    
    @abstractmethod
    def delete_subject(self, subject_id: str) -> bool:
        """Delete a subject"""
        pass
    
    @abstractmethod
    def get_courses_by_department_semester(self, department_id: str, semester: int) -> List:
        """Get courses by department and semester"""
        pass
    
    @abstractmethod
    def enroll_student_in_courses(self, student_id: str, course_ids: List[str]) -> bool:
        """Enroll student in multiple courses"""
        pass
    
    @abstractmethod
    def clear_student_enrollments(self, student_id: str) -> bool:
        """Clear all enrollments for a student"""
        pass
    
    @abstractmethod
    def get_student_subjects(self, student_id: str) -> List:
        """Get all subjects a student is enrolled in"""
        pass
    
    @abstractmethod
    def get_enrolled_students(self, subject_id: str) -> List[str]:
        """Get list of student IDs enrolled in a subject"""
        pass
    
    @abstractmethod
    def update_student_semester(self, student_id: str, semester: int) -> bool:
        """Update student's current semester"""
        pass
    
    @abstractmethod
    def get_attendance_records(self, filters: Dict[str, Any] = None) -> List:
        """Get attendance records with optional filters"""
        pass
    
    @abstractmethod
    def add_attendance_record(self, attendance) -> bool:
        """Add an attendance record"""
        pass