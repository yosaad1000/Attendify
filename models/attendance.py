from datetime import datetime
import firebase_admin
from firebase_admin import firestore

class Attendance:
    """
    Represents student attendance for a subject
    """
    def __init__(self, attendance_id, student_id, subject_id, 
                 date=None, status="present", verified_by=None):
        self.attendance_id = attendance_id  # Unique attendance ID
        self.student_id = student_id        # Student ID
        self.subject_id = subject_id        # Subject ID
        self.date = date                    # Date of attendance (will use Firestore SERVER_TIMESTAMP)
        self.status = status                # Status: present, absent, late
        self.verified_by = verified_by      # Faculty ID who verified
        self.timestamp = datetime.now()     # Timestamp of record
    
    @staticmethod
    def from_dict(source):
        """Creates an Attendance instance from a dictionary"""
        attendance = Attendance(
            attendance_id=source.get('attendance_id'),
            student_id=source.get('student_id'),
            subject_id=source.get('subject_id'),
            date=source.get('date'),
            status=source.get('status', 'present'),
            verified_by=source.get('verified_by')
        )
        if source.get('timestamp'):
            attendance.timestamp = source.get('timestamp')
        return attendance
    
    def to_dict(self):
        """Returns the attendance as a dictionary"""
        # Use current timestamp if date is not provided
        date_field = self.date if self.date is not None else firestore.SERVER_TIMESTAMP
        
        return {
            'attendance_id': self.attendance_id,
            'student_id': self.student_id,
            'subject_id': self.subject_id,
            'date': date_field,
            'status': self.status,
            'verified_by': self.verified_by,
            'timestamp': self.timestamp
        }