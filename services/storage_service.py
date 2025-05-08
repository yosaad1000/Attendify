import logging
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from pinecone import Pinecone, ServerlessSpec
import numpy as np
from datetime import datetime
import uuid

from config import config

logger = logging.getLogger(__name__)

class StorageService:
    """
    Service for database and vector storage operations
    """
    def __init__(self):
        # Initialize Firebase if not already initialized
        if not firebase_admin._apps:
            cred = credentials.Certificate(config.FIREBASE_CREDENTIALS)
            firebase_admin.initialize_app(cred)
        
        self.db = firestore.client()
        
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
        """
        Store student face encoding in Pinecone
        
        Args:
            student_id: Student ID
            name: Student name
            face_encoding: Face encoding as numpy array
        """
        self.face_index.upsert(vectors=[{
            "id": student_id,
            "values": face_encoding.tolist(),
            "metadata": {
                "name": name,
                "student_id": student_id
            }
        }])
    
    def find_matching_face(self, face_encoding):
        """
        Find a matching face in Pinecone
        
        Args:
            face_encoding: Face encoding as numpy array
        
        Returns:
            (student_id, name, score) or (None, "Unknown", 1.0) if no match
        """
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
        """Add a department to Firestore"""
        return self.db.collection('departments').document(department.dept_id).set(department.to_dict())
    
    def get_department(self, dept_id):
        """Get a department from Firestore"""
        doc = self.db.collection('departments').document(dept_id).get()
        if doc.exists:
            from models.department import Department
            return Department.from_dict(doc.to_dict())
        return None
    
    def add_faculty(self, faculty):
        """Add a faculty member to Firestore"""
        return self.db.collection('faculty').document(faculty.faculty_id).set(faculty.to_dict())
    
    def add_subject(self, subject):
        """Add a subject to Firestore"""
        return self.db.collection('subjects').document(subject.subject_id).set(subject.to_dict())
    
    def add_student(self, student):
        """Add a student to Firestore"""
        return self.db.collection('students').document(student.student_id).set(student.to_dict())
    
    def student_exists(self, student_id):
        """Check if a student exists in Firestore"""
        return self.db.collection('students').document(student_id).get().exists
    
    def enroll_student_in_subject(self, student_subject):
        """Enroll a student in a subject"""
        return self.db.collection('student_subjects').document(student_subject.id).set(student_subject.to_dict())
    
    def record_attendance(self, attendance):
        """Record student attendance"""
        return self.db.collection('attendance').document(attendance.attendance_id).set(attendance.to_dict())
    
    def get_student_attendance(self, student_id, subject_id=None, start_date=None, end_date=None):
        """
        Get attendance records for a student
        
        Args:
            student_id: Student ID
            subject_id: Optional subject ID to filter by
            start_date: Optional start date
            end_date: Optional end date
        
        Returns:
            List of attendance records
        """
        query = self.db.collection('attendance').where(filter=FieldFilter('student_id', '==', student_id))
        
        if subject_id:
            query = query.where(filter=FieldFilter('subject_id', '==', subject_id))
        
        if start_date:
            query = query.where(filter=FieldFilter('date', '>=', start_date))
        
        if end_date:
            query = query.where(filter=FieldFilter('date', '<=', end_date))
        
        from models.attendance import Attendance
        return [Attendance.from_dict(doc.to_dict()) for doc in query.stream()]
    
    def get_subject_attendance(self, subject_id, date=None):
        """
        Get attendance records for a subject
        
        Args:
            subject_id: Subject ID
            date: Optional date to filter by
        
        Returns:
            List of attendance records
        """
        query = self.db.collection('attendance').where(filter=FieldFilter('subject_id', '==', subject_id))
        
        if date:
            query = query.where(filter=FieldFilter('date', '==', date))
        
        from models.attendance import Attendance
        return [Attendance.from_dict(doc.to_dict()) for doc in query.stream()]
    
    def get_all_students(self):
        """Get all students"""
        from models.student import Student
        return [Student.from_dict(doc.to_dict()) for doc in self.db.collection('students').stream()]
    
    def get_all_subjects(self):
        """Get all subjects"""
        from models.subject import Subject
        return [Subject.from_dict(doc.to_dict()) for doc in self.db.collection('subjects').stream()]
    
    def get_all_departments(self):
        """Get all departments"""
        from models.department import Department
        return [Department.from_dict(doc.to_dict()) for doc in self.db.collection('departments').stream()]
    

    def get_student(self, student_id):
        """Get a student from Firestore by ID"""
        doc = self.db.collection('students').document(student_id).get()
        if doc.exists:
            from models.student import Student
            return Student.from_dict(doc.to_dict())
        return None

    def update_student(self, student):
        """Update a student in Firestore"""
        return self.db.collection('students').document(student.student_id).update(student.to_dict())

    def update_student_semester(self, student_id, new_semester):
        """
        Update a student's current semester

        Args:
            student_id: Student ID
            new_semester: New semester number

        Returns:
            True if successful, False otherwise
        """
        try:
            self.db.collection('students').document(student_id).update({
                'current_semester': new_semester
            })
            return True
        except Exception as e:
            logger.error(f"Error updating student semester: {e}")
            return False

    def get_courses_by_department_semester(self, department_id, semester):
        """
        Get all courses for a specific department and semester

        Args:
            department_id: Department ID
            semester: Semester number

        Returns:
            List of subjects (courses)
        """
        query = self.db.collection('subjects').where(
            filter=FieldFilter('department_id', '==', department_id)
        ).where(
            filter=FieldFilter('semester', '==', semester)
        )

        from models.subject import Subject
        return [Subject.from_dict(doc.to_dict()) for doc in query.stream()]

    def enroll_student_in_courses(self, student_id, course_ids):
     """
     Enroll a student in multiple courses at once
 
     Args:
         student_id: Student ID
         course_ids: List of course IDs
 
     Returns:
         True if successful, False otherwise
     """
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
             course_ref = self.db.collection('subjects').document(course_id)
             course_doc = course_ref.get()
             
             if not course_doc.exists:
                 logger.error(f"Course {course_id} not found")
                 continue
                 
             # Get current course data
             course_data = course_doc.to_dict()
             enrolled_students = course_data.get('enrolled_students', [])
             
             # Add student if not already enrolled
             if student_id not in enrolled_students:
                 enrolled_students.append(student_id)
                 course_ref.update({'enrolled_students': enrolled_students})
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
        """
        Clear all course enrollments for a student
    
        Args:
            student_id: Student ID
    
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get the student record
            student = self.get_student(student_id)
            if not student:
                logger.error(f"Student {student_id} not found")
                return False
            
            # Clear the student's course enrollments
            student.course_enrolled_ids = []
            self.update_student(student)
            
            # Find all subjects that have this student enrolled
            subjects = self.db.collection('subjects').stream()
            
            for subject_doc in subjects:
                subject_data = subject_doc.to_dict()
                enrolled_students = subject_data.get('enrolled_students', [])
                
                # If student is enrolled in this subject, remove them
                if student_id in enrolled_students:
                    enrolled_students.remove(student_id)
                    self.db.collection('subjects').document(subject_doc.id).update({
                        'enrolled_students': enrolled_students
                    })
                    
            return True
        except Exception as e:
            logger.error(f"Error clearing student enrollments: {e}")
            return False
    