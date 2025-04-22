from datetime import datetime

class Student:
    """
    Represents a student
    """
    def __init__(self, student_id, name, email, department_id, 
                 batch_year, current_semester=None, enrollment_date=None , course_enrolled_ids=None):
        self.student_id = student_id        # Student ID (used as document ID)
        self.name = name                    # Student name
        self.email = email                  # Student email
        self.department_id = department_id  # Primary department ID
        self.batch_year = batch_year        # Year of admission
        self.current_semester = current_semester  # Current semester
        self.course_enrolled_ids = course_enrolled_ids or []
        self.enrollment_date = enrollment_date or datetime.now()  # Date of enrollment
    
    @staticmethod
    def from_dict(source):
        """Creates a Student instance from a dictionary"""
        student = Student(
            student_id=source.get('student_id'),
            name=source.get('name'),
            email=source.get('email'),
            department_id=source.get('department_id'),
            batch_year=source.get('batch_year'),
            current_semester=source.get('current_semester'),
            course_enrolled_ids=source.get('course_enrolled_ids'),
            enrollment_date=source.get('enrollment_date')
        )
        return student
    
    def to_dict(self):
        """Returns the student as a dictionary"""
        return {
            'student_id': self.student_id,
            'name': self.name,
            'email': self.email,
            'department_id': self.department_id,
            'batch_year': self.batch_year,
            'current_semester': self.current_semester,
            'course_enrolled_ids': self.course_enrolled_ids,
            'enrollment_date': self.enrollment_date
        }