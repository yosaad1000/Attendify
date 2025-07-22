import logging
from supabase import create_client, Client
from supabase.client import ClientOptions
from pinecone import Pinecone, ServerlessSpec
import numpy as np
from datetime import datetime
import uuid

from config import config

logger = logging.getLogger(__name__)

class StorageService:
    """
    Service for database and vector storage operations using Supabase
    """
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
        
        # Initialize Pinecone
        self.pc = Pinecone(api_key=config.PINECONE_API_KEY)
        
        # Create index if it doesn't exist
        if config.PINECONE_INDEX_NAME not in self.pc.list_indexes().names():
            self.pc.create_index(
                name=config.PINECONE_INDEX_NAME,
                dimension=config.FACE_ENCODING_DIMENSION,
                metric=config.FACE_METRIC,
                spec=ServerlessSpec(
                    cloud=config.PINECONE_ENV,
                    region=config.PINECONE_REGION
                )
            )
        
        self.face_index = self.pc.Index(config.PINECONE_INDEX_NAME)
    
    def store_student_face(self, student_id, name, face_encoding):
        """Store student face encoding in Pinecone"""
        self.face_index.upsert(vectors=[{
            "id": student_id,
            "values": face_encoding.tolist(),
            "metadata": {
                "name": name,
                "student_id": student_id
            }
        }])
    
    def find_matching_face(self, face_encoding):
        """Find a matching face in Pinecone"""
        results = self.face_index.query(
            vector=face_encoding.tolist(),
            top_k=1,
            include_metadata=True
        )
        
        if results['matches'] and results['matches'][0]['score'] < config.FACE_THRESHOLD:
            match = results['matches'][0]
            return match['id'], match['metadata'].get('name', 'Unknown'), match['score']
        
        return None, "Unknown", 1.0
    
    def add_department(self, department):
        """Add a department to Supabase"""
        try:
            result = self.supabase.table('departments').insert(department.to_dict()).execute()
            return result
        except Exception as e:
            logger.error(f"Error adding department: {e}")
            raise
    
    def get_department(self, dept_id):
        """Get a department from Supabase"""
        try:
            result = self.supabase.table('departments').select("*").eq('dept_id', dept_id).execute()
            if result.data:
                from models.department import Department
                return Department.from_dict(result.data[0])
            return None
        except Exception as e:
            logger.error(f"Error getting department: {e}")
            return None
    
    def add_faculty(self, faculty):
        """Add a faculty member to Supabase"""
        try:
            result = self.supabase.table('faculty').insert(faculty.to_dict()).execute()
            return result
        except Exception as e:
            logger.error(f"Error adding faculty: {e}")
            raise
    
    def add_subject(self, subject):
        """Add a subject to Supabase"""
        try:
            result = self.supabase.table('subjects').insert(subject.to_dict()).execute()
            return result
        except Exception as e:
            logger.error(f"Error adding subject: {e}")
            raise
    
    def add_student(self, student):
        """Add a student to Supabase"""
        try:
            result = self.supabase.table('students').insert(student.to_dict()).execute()
            return result
        except Exception as e:
            logger.error(f"Error adding student: {e}")
            raise
    
    def student_exists(self, student_id):
        """Check if a student exists in Supabase"""
        try:
            result = self.supabase.table('students').select("student_id").eq('student_id', student_id).execute()
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"Error checking student existence: {e}")
            return False
    
    def record_attendance(self, attendance):
        """Record student attendance"""
        try:
            result = self.supabase.table('attendance').insert(attendance.to_dict()).execute()
            return result
        except Exception as e:
            logger.error(f"Error recording attendance: {e}")
            raise
    
    def get_student_attendance(self, student_id, subject_id=None, start_date=None, end_date=None):
        """Get attendance records for a student"""
        try:
            query = self.supabase.table('attendance').select("*").eq('student_id', student_id)
            
            if subject_id:
                query = query.eq('subject_id', subject_id)
            
            if start_date:
                query = query.gte('date', start_date.isoformat())
            
            if end_date:
                query = query.lte('date', end_date.isoformat())
            
            result = query.execute()
            
            from models.attendance import Attendance
            return [Attendance.from_dict(record) for record in result.data]
        except Exception as e:
            logger.error(f"Error getting student attendance: {e}")
            return []
    
    def get_subject_attendance(self, subject_id, date=None):
        """Get attendance records for a subject"""
        try:
            query = self.supabase.table('attendance').select("*").eq('subject_id', subject_id)
            
            if date:
                query = query.eq('date', date.isoformat())
            
            result = query.execute()
            
            from models.attendance import Attendance
            return [Attendance.from_dict(record) for record in result.data]
        except Exception as e:
            logger.error(f"Error getting subject attendance: {e}")
            return []
    
    def get_all_students(self):
        """Get all students"""
        try:
            result = self.supabase.table('students').select("*").execute()
            from models.student import Student
            return [Student.from_dict(record) for record in result.data]
        except Exception as e:
            logger.error(f"Error getting all students: {e}")
            return []
    
    def get_all_subjects(self):
        """Get all subjects"""
        try:
            result = self.supabase.table('subjects').select("*").execute()
            from models.subject import Subject
            return [Subject.from_dict(record) for record in result.data]
        except Exception as e:
            logger.error(f"Error getting all subjects: {e}")
            return []
    
    def get_all_departments(self):
        """Get all departments"""
        try:
            result = self.supabase.table('departments').select("*").execute()
            from models.department import Department
            return [Department.from_dict(record) for record in result.data]
        except Exception as e:
            logger.error(f"Error getting all departments: {e}")
            return []
    
    def get_student(self, student_id):
        """Get a student from Supabase by ID"""
        try:
            result = self.supabase.table('students').select("*").eq('student_id', student_id).execute()
            if result.data:
                from models.student import Student
                return Student.from_dict(result.data[0])
            return None
        except Exception as e:
            logger.error(f"Error getting student: {e}")
            return None
    
    def update_student(self, student):
        """Update a student in Supabase"""
        try:
            result = self.supabase.table('students').update(student.to_dict()).eq('student_id', student.student_id).execute()
            return result
        except Exception as e:
            logger.error(f"Error updating student: {e}")
            raise
    
    def update_student_semester(self, student_id, new_semester):
        """Update a student's current semester"""
        try:
            result = self.supabase.table('students').update({
                'current_semester': new_semester
            }).eq('student_id', student_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating student semester: {e}")
            return False
    
    def get_courses_by_department_semester(self, department_id, semester):
        """Get all courses for a specific department and semester"""
        try:
            result = self.supabase.table('subjects').select("*").eq('department_id', department_id).eq('semester', semester).execute()
            
            from models.subject import Subject
            return [Subject.from_dict(record) for record in result.data]
        except Exception as e:
            logger.error(f"Error getting courses by department and semester: {e}")
            return []
    
    def enroll_student_in_courses(self, student_id, course_ids):
        """Enroll a student in multiple courses at once"""
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
    
    def clear_student_enrollments(self, student_id):
        """Clear all course enrollments for a student"""
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