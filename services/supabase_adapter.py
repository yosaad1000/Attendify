# services/supabase_adapter.py
import logging
from typing import List, Optional, Dict, Any
from supabase import create_client, Client
from supabase.client import ClientOptions

from config import config
from services.database_interface import DatabaseInterface
from models.student import Student
from models.department import Department
from models.faculty import Faculty
from models.subject import Subject
from models.attendance import Attendance

logger = logging.getLogger(__name__)

class SupabaseAdapter(DatabaseInterface):
    """Supabase implementation of the database interface"""
    
    def __init__(self):
        # Initialize Supabase with explicit options to avoid proxy parameter issue
        try:
            # Method 1: Use ClientOptions to control initialization
            options = ClientOptions()
            self.supabase: Client = create_client(
                config.SUPABASE_URL, 
                config.SUPABASE_KEY,
                options
            )
        except Exception as e:
            logger.error(f"Error with ClientOptions, trying alternative method: {e}")
            # Method 2: Alternative initialization without options
            try:
                self.supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
            except Exception as e2:
                logger.error(f"Error creating Supabase client: {e2}")
                raise
    
    def get_student(self, student_id: str):
        """Get a student by ID"""
        try:
            result = self.supabase.table('students').select("*").eq('student_id', student_id).execute()
            if result.data:
                return Student.from_dict(result.data[0])
            return None
        except Exception as e:
            logger.error(f"Error getting student: {e}")
            return None
    
    def get_all_students(self) -> List[Student]:
        """Get all students"""
        try:
            result = self.supabase.table('students').select("*").execute()
            return [Student.from_dict(record) for record in result.data]
        except Exception as e:
            logger.error(f"Error getting all students: {e}")
            return []
    
    def add_student(self, student: Student) -> bool:
        """Add a new student"""
        try:
            result = self.supabase.table('students').insert(student.to_dict()).execute()
            return True
        except Exception as e:
            logger.error(f"Error adding student: {e}")
            return False
    
    def update_student(self, student: Student) -> bool:
        """Update an existing student"""
        try:
            result = self.supabase.table('students').update(student.to_dict()).eq('student_id', student.student_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating student: {e}")
            return False
    
    def student_exists(self, student_id: str) -> bool:
        """Check if student exists"""
        try:
            result = self.supabase.table('students').select("student_id").eq('student_id', student_id).execute()
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"Error checking student existence: {e}")
            return False
    
    def get_all_departments(self) -> List[Department]:
        """Get all departments"""
        try:
            result = self.supabase.table('departments').select("*").execute()
            return [Department.from_dict(record) for record in result.data]
        except Exception as e:
            logger.error(f"Error getting all departments: {e}")
            return []
    
    def add_department(self, department: Department) -> bool:
        """Add a new department"""
        try:
            result = self.supabase.table('departments').insert(department.to_dict()).execute()
            return True
        except Exception as e:
            logger.error(f"Error adding department: {e}")
            return False
    
    def update_department(self, dept_id: str, updates: Dict[str, Any]) -> bool:
        """Update a department"""
        try:
            result = self.supabase.table('departments').update(updates).eq('dept_id', dept_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating department: {e}")
            return False
    
    def get_all_faculty(self) -> List[Faculty]:
        """Get all faculty members"""
        try:
            result = self.supabase.table('faculty').select("*").execute()
            return [Faculty.from_dict(record) for record in result.data]
        except Exception as e:
            logger.error(f"Error getting all faculty: {e}")
            return []
    
    def get_faculty_by_id(self, faculty_id: str):
        """Get faculty by ID"""
        try:
            result = self.supabase.table('faculty').select("*").eq('faculty_id', faculty_id).execute()
            if result.data:
                return Faculty.from_dict(result.data[0])
            return None
        except Exception as e:
            logger.error(f"Error getting faculty by ID: {e}")
            return None
    
    def add_faculty(self, faculty: Faculty) -> bool:
        """Add a new faculty member"""
        try:
            result = self.supabase.table('faculty').insert(faculty.to_dict()).execute()
            return True
        except Exception as e:
            logger.error(f"Error adding faculty: {e}")
            return False
    
    def update_faculty(self, faculty_id: str, updates: Dict[str, Any]) -> bool:
        """Update a faculty member"""
        try:
            result = self.supabase.table('faculty').update(updates).eq('faculty_id', faculty_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating faculty: {e}")
            return False
    
    def delete_faculty(self, faculty_id: str) -> bool:
        """Delete a faculty member"""
        try:
            result = self.supabase.table('faculty').delete().eq('faculty_id', faculty_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error deleting faculty: {e}")
            return False
    
    def get_all_subjects(self) -> List[Subject]:
        """Get all subjects"""
        try:
            result = self.supabase.table('subjects').select("*").execute()
            return [Subject.from_dict(record) for record in result.data]
        except Exception as e:
            logger.error(f"Error getting all subjects: {e}")
            return []
    
    def get_subject_by_id(self, subject_id: str):
        """Get subject by ID"""
        try:
            result = self.supabase.table('subjects').select("*").eq('subject_id', subject_id).execute()
            if result.data:
                return Subject.from_dict(result.data[0])
            return None
        except Exception as e:
            logger.error(f"Error getting subject by ID: {e}")
            return None
    
    def add_subject(self, subject: Subject) -> bool:
        """Add a new subject"""
        try:
            result = self.supabase.table('subjects').insert(subject.to_dict()).execute()
            return True
        except Exception as e:
            logger.error(f"Error adding subject: {e}")
            return False
    
    def update_subject(self, subject_id: str, updates: Dict[str, Any]) -> bool:
        """Update a subject"""
        try:
            result = self.supabase.table('subjects').update(updates).eq('subject_id', subject_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating subject: {e}")
            return False
    
    def delete_subject(self, subject_id: str) -> bool:
        """Delete a subject"""
        try:
            result = self.supabase.table('subjects').delete().eq('subject_id', subject_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error deleting subject: {e}")
            return False
    
    def get_courses_by_department_semester(self, department_id: str, semester: int) -> List[Subject]:
        """Get courses by department and semester"""
        try:
            result = self.supabase.table('subjects').select("*").eq('department_id', department_id).eq('semester', semester).execute()
            return [Subject.from_dict(record) for record in result.data]
        except Exception as e:
            logger.error(f"Error getting courses by department and semester: {e}")
            return []
    
    def enroll_student_in_courses(self, student_id: str, course_ids: List[str]) -> bool:
        """Enroll student in multiple courses"""
        try:
            # Get the student to verify they exist
            student = self.get_student(student_id)
            if not student:
                logger.error(f"Student {student_id} not found")
                return False
            
            # Get student's currently enrolled courses
            student_courses = student.course_enrolled_ids or []
            courses_added = []
            
            # Update each course's enrolled_students list
            for course_id in course_ids:
                # Get current course data
                course_result = self.supabase.table('subjects').select("*").eq('subject_id', course_id).execute()
                
                if not course_result.data:
                    logger.error(f"Course {course_id} not found")
                    continue
                
                course_data = course_result.data[0]
                enrolled_students = course_data.get('enrolled_students', [])
                
                # Add student if not already enrolled
                if student_id not in enrolled_students:
                    enrolled_students.append(student_id)
                    self.supabase.table('subjects').update({
                        'enrolled_students': enrolled_students
                    }).eq('subject_id', course_id).execute()
                    courses_added.append(course_id)
            
            # Update student's enrolled courses
            for course_id in courses_added:
                if course_id not in student_courses:
                    student_courses.append(course_id)
            
            # Update student document if any courses were added
            if courses_added:
                student.course_enrolled_ids = student_courses
                self.update_student(student)
            
            return True
        except Exception as e:
            logger.error(f"Error enrolling student in courses: {e}")
            return False
    
    def clear_student_enrollments(self, student_id: str) -> bool:
        """Clear all enrollments for a student"""
        try:
            # Get the student record
            student = self.get_student(student_id)
            if not student:
                logger.error(f"Student {student_id} not found")
                return False
            
            # Clear the student's course enrollments
            student.course_enrolled_ids = []
            self.update_student(student)
            
            # Find all subjects that have this student enrolled and remove them
            subjects_result = self.supabase.table('subjects').select("*").execute()
            
            for subject_data in subjects_result.data:
                enrolled_students = subject_data.get('enrolled_students', [])
                
                # If student is enrolled in this subject, remove them
                if student_id in enrolled_students:
                    enrolled_students.remove(student_id)
                    self.supabase.table('subjects').update({
                        'enrolled_students': enrolled_students
                    }).eq('subject_id', subject_data['subject_id']).execute()
            
            return True
        except Exception as e:
            logger.error(f"Error clearing student enrollments: {e}")
            return False
    
    def get_student_subjects(self, student_id: str) -> List[Subject]:
        """Get all subjects a student is enrolled in"""
        try:
            student = self.get_student(student_id)
            if not student or not student.course_enrolled_ids:
                return []
            
            subjects = []
            for subject_id in student.course_enrolled_ids:
                subject = self.get_subject_by_id(subject_id)
                if subject:
                    subjects.append(subject)
            
            return subjects
        except Exception as e:
            logger.error(f"Error getting student subjects: {e}")
            return []
    
    def get_enrolled_students(self, subject_id: str) -> List[str]:
        """Get list of student IDs enrolled in a subject"""
        try:
            result = self.supabase.table('subjects').select("enrolled_students").eq('subject_id', subject_id).execute()
            if result.data:
                return result.data[0].get('enrolled_students', [])
            return []
        except Exception as e:
            logger.error(f"Error getting enrolled students: {e}")
            return []
    
    def update_student_semester(self, student_id: str, semester: int) -> bool:
        """Update student's current semester"""
        try:
            result = self.supabase.table('students').update({
                'current_semester': semester
            }).eq('student_id', student_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating student semester: {e}")
            return False
    
    def get_attendance_records(self, filters: Dict[str, Any] = None) -> List[Attendance]:
        """Get attendance records with optional filters"""
        try:
            query = self.supabase.table('attendance').select("*")
            
            if filters:
                for key, value in filters.items():
                    if key == 'student_id':
                        query = query.eq('student_id', value)
                    elif key == 'subject_id':
                        query = query.eq('subject_id', value)
                    elif key == 'date':
                        query = query.eq('date', value)
                    elif key == 'start_date':
                        query = query.gte('date', value)
                    elif key == 'end_date':
                        query = query.lte('date', value)
            
            result = query.execute()
            return [Attendance.from_dict(record) for record in result.data]
        except Exception as e:
            logger.error(f"Error getting attendance records: {e}")
            return []
    
    def add_attendance_record(self, attendance: Attendance) -> bool:
        """Add an attendance record"""
        try:
            result = self.supabase.table('attendance').insert(attendance.to_dict()).execute()
            return True
        except Exception as e:
            logger.error(f"Error adding attendance record: {e}")
            return False