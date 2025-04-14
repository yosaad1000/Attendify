from datetime import datetime

class StudentSubject:
    """
    Represents the relationship between students and subjects
    Handles students taking subjects from different departments
    and students repeating courses due to backlogs
    """
    def __init__(self, id, student_id, subject_id, academic_year, 
                 semester, status="enrolled", attempt=1, grade=None):
        self.id = id                    # Unique ID for this enrollment
        self.student_id = student_id    # Student ID
        self.subject_id = subject_id    # Subject ID
        self.academic_year = academic_year  # Academic year
        self.semester = semester        # Semester
        self.status = status            # Status: enrolled, completed, backlog
        self.attempt = attempt          # Attempt number (for repeating courses)
        self.grade = grade              # Grade obtained
        self.timestamp = datetime.now() # Enrollment timestamp
    
    @staticmethod
    def from_dict(source):
        """Creates a StudentSubject instance from a dictionary"""
        student_subject = StudentSubject(
            id=source.get('id'),
            student_id=source.get('student_id'),
            subject_id=source.get('subject_id'),
            academic_year=source.get('academic_year'),
            semester=source.get('semester'),
            status=source.get('status', 'enrolled'),
            attempt=source.get('attempt', 1),
            grade=source.get('grade')
        )
        if source.get('timestamp'):
            student_subject.timestamp = source.get('timestamp')
        return student_subject
    
    def to_dict(self):
        """Returns the student-subject relationship as a dictionary"""
        return {
            'id': self.id,
            'student_id': self.student_id,
            'subject_id': self.subject_id,
            'academic_year': self.academic_year,
            'semester': self.semester,
            'status': self.status,
            'attempt': self.attempt,
            'grade': self.grade,
            'timestamp': self.timestamp
        }