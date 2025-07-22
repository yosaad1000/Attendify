import logging
from datetime import datetime
import uuid

from models.attendance import Attendance
from services.storage_service import StorageService

logger = logging.getLogger(__name__)

class AttendanceService:
    """Service for attendance-related operations"""
    
    def __init__(self):
        self.storage = StorageService()
    
    def mark_attendance(self, student_id, subject_id, faculty_id=None, status="present"):
        """Mark attendance for a student"""
        try:
            attendance_id = f"att_{uuid.uuid4().hex}"
            attendance = Attendance(
                attendance_id=attendance_id,
                student_id=student_id,
                subject_id=subject_id,
                date=datetime.now(),
                status=status,
                verified_by=faculty_id
            )
            
            # Record the attendance
            self.storage.record_attendance(attendance)
            return True
            
        except Exception as e:
            logger.error(f"Error marking attendance: {e}")
            return False
    
    def get_student_attendance_summary(self, student_id, subject_id=None):
        """Get attendance summary for a student"""
        try:
            attendance_records = self.storage.get_student_attendance(student_id, subject_id)
            
            if not attendance_records:
                return {
                    'student_id': student_id,
                    'total_classes': 0,
                    'present_count': 0,
                    'absent_count': 0,
                    'late_count': 0,
                    'attendance_percentage': 0
                }
            
            present_count = sum(1 for rec in attendance_records if rec.status == 'present')
            absent_count = sum(1 for rec in attendance_records if rec.status == 'absent')
            late_count = sum(1 for rec in attendance_records if rec.status == 'late')
            total_classes = len(attendance_records)
            
            attendance_percentage = (present_count + late_count) / total_classes * 100 if total_classes > 0 else 0
            
            return {
                'student_id': student_id,
                'total_classes': total_classes,
                'present_count': present_count,
                'absent_count': absent_count,
                'late_count': late_count,
                'attendance_percentage': round(attendance_percentage, 2)
            }
        except Exception as e:
            logger.error(f"Error getting student attendance summary: {e}")
            return {
                'student_id': student_id,
                'error': str(e)
            }
    
    def get_subject_attendance_summary(self, subject_id, date=None):
        """Get attendance summary for a subject"""
        try:
            attendance_records = self.storage.get_subject_attendance(subject_id, date)
            
            if not attendance_records:
                return {
                    'subject_id': subject_id,
                    'date': date,
                    'total_students': 0,
                    'present_count': 0,
                    'absent_count': 0,
                    'late_count': 0,
                    'attendance_percentage': 0
                }
            
            present_count = sum(1 for rec in attendance_records if rec.status == 'present')
            absent_count = sum(1 for rec in attendance_records if rec.status == 'absent')
            late_count = sum(1 for rec in attendance_records if rec.status == 'late')
            total_students = len(attendance_records)
            
            attendance_percentage = (present_count + late_count) / total_students * 100 if total_students > 0 else 0
            
            return {
                'subject_id': subject_id,
                'date': date,
                'total_students': total_students,
                'present_count': present_count,
                'absent_count': absent_count,
                'late_count': late_count,
                'attendance_percentage': round(attendance_percentage, 2)
            }
        except Exception as e:
            logger.error(f"Error getting subject attendance summary: {e}")
            return {
                'subject_id': subject_id,
                'error': str(e)
            }