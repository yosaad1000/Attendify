from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from ..database import get_db
from ..models.user import User
from ..models.student import Student
from ..models.teacher import Teacher
from ..models.subject import Subject
from ..models.attendance import Attendance, AttendanceStatus
from ..models.grade import Grade
from ..models.fee import Fee, PaymentStatus
from ..routers.auth import get_current_user

router = APIRouter()

@router.get("/dashboard/{role}")
async def get_dashboard_stats(
    role: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics based on user role"""
    
    if role == "admin":
        # Admin dashboard stats
        total_students = db.query(Student).count()
        total_teachers = db.query(Teacher).count()
        total_subjects = db.query(Subject).count()
        
        # Pending fees
        pending_fees = db.query(func.sum(Fee.amount)).filter(
            Fee.status == PaymentStatus.PENDING
        ).scalar() or 0
        
        # Attendance data for chart (last 6 months)
        six_months_ago = datetime.now() - timedelta(days=180)
        attendance_data = []
        for i in range(6):
            month_start = six_months_ago + timedelta(days=30*i)
            month_end = month_start + timedelta(days=30)
            
            total_attendance = db.query(Attendance).filter(
                and_(
                    Attendance.date >= month_start.date(),
                    Attendance.date < month_end.date()
                )
            ).count()
            
            present_count = db.query(Attendance).filter(
                and_(
                    Attendance.date >= month_start.date(),
                    Attendance.date < month_end.date(),
                    Attendance.status == AttendanceStatus.PRESENT
                )
            ).count()
            
            attendance_rate = (present_count / total_attendance * 100) if total_attendance > 0 else 0
            
            attendance_data.append({
                "month": month_start.strftime("%b"),
                "attendance": round(attendance_rate, 1)
            })
        
        # Performance data (mock data for now)
        performance_data = [
            {"month": "Jan", "performance": 85},
            {"month": "Feb", "performance": 87},
            {"month": "Mar", "performance": 89},
            {"month": "Apr", "performance": 86},
            {"month": "May", "performance": 90},
            {"month": "Jun", "performance": 88},
        ]
        
        # Recent activities (mock data)
        recent_activities = [
            {"message": "New student registered", "time": "2 hours ago"},
            {"message": "Attendance marked for CS101", "time": "4 hours ago"},
            {"message": "Grades updated for MATH201", "time": "1 day ago"},
            {"message": "Fee payment received", "time": "2 days ago"},
        ]
        
        return {
            "success": True,
            "data": {
                "totalStudents": total_students,
                "totalTeachers": total_teachers,
                "totalSubjects": total_subjects,
                "pendingFees": pending_fees,
                "attendanceData": attendance_data,
                "performanceData": performance_data,
                "recentActivities": recent_activities
            }
        }
    
    elif role == "teacher":
        # Teacher dashboard stats
        teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
        if not teacher:
            raise HTTPException(status_code=404, detail="Teacher profile not found")
        
        total_classes = db.query(Subject).filter(Subject.teacher_id == teacher.id).count()
        
        # Get students in teacher's subjects
        teacher_subjects = db.query(Subject).filter(Subject.teacher_id == teacher.id).all()
        subject_ids = [s.id for s in teacher_subjects]
        
        # Count unique students
        total_students = db.query(Student).join(
            Attendance, Student.id == Attendance.student_id
        ).filter(Attendance.subject_id.in_(subject_ids)).distinct().count()
        
        # Calculate attendance rate for teacher's subjects
        total_attendance = db.query(Attendance).filter(
            Attendance.subject_id.in_(subject_ids)
        ).count()
        
        present_count = db.query(Attendance).filter(
            and_(
                Attendance.subject_id.in_(subject_ids),
                Attendance.status == AttendanceStatus.PRESENT
            )
        ).count()
        
        attendance_rate = (present_count / total_attendance * 100) if total_attendance > 0 else 0
        
        return {
            "success": True,
            "data": {
                "totalClasses": total_classes,
                "totalStudents": total_students,
                "attendanceRate": round(attendance_rate, 1),
                "attendanceData": [],  # Can be populated with specific data
                "performanceData": [],
                "recentActivities": []
            }
        }
    
    elif role == "student":
        # Student dashboard stats
        student = db.query(Student).filter(Student.user_id == current_user.id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student profile not found")
        
        # Enrolled subjects count
        enrolled_subjects = db.query(Subject).join(
            Attendance, Subject.id == Attendance.subject_id
        ).filter(Attendance.student_id == student.id).distinct().count()
        
        # Student's attendance rate
        total_attendance = db.query(Attendance).filter(
            Attendance.student_id == student.id
        ).count()
        
        present_count = db.query(Attendance).filter(
            and_(
                Attendance.student_id == student.id,
                Attendance.status == AttendanceStatus.PRESENT
            )
        ).count()
        
        attendance_rate = (present_count / total_attendance * 100) if total_attendance > 0 else 0
        
        # Pending fees
        pending_fees = db.query(func.sum(Fee.amount)).filter(
            and_(
                Fee.student_id == student.id,
                Fee.status == PaymentStatus.PENDING
            )
        ).scalar() or 0
        
        return {
            "success": True,
            "data": {
                "enrolledSubjects": enrolled_subjects,
                "attendanceRate": round(attendance_rate, 1),
                "pendingFees": pending_fees,
                "attendanceData": [],
                "performanceData": [],
                "recentActivities": []
            }
        }
    
    else:
        raise HTTPException(status_code=400, detail="Invalid role")

@router.get("/attendance")
async def get_attendance_report(
    start_date: str = None,
    end_date: str = None,
    subject_id: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get attendance report with filters"""
    
    query = db.query(Attendance)
    
    if start_date:
        query = query.filter(Attendance.date >= datetime.strptime(start_date, "%Y-%m-%d").date())
    
    if end_date:
        query = query.filter(Attendance.date <= datetime.strptime(end_date, "%Y-%m-%d").date())
    
    if subject_id:
        query = query.filter(Attendance.subject_id == subject_id)
    
    # Role-based filtering
    if current_user.role == "teacher":
        teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
        if teacher:
            teacher_subjects = db.query(Subject).filter(Subject.teacher_id == teacher.id).all()
            subject_ids = [s.id for s in teacher_subjects]
            query = query.filter(Attendance.subject_id.in_(subject_ids))
    
    elif current_user.role == "student":
        student = db.query(Student).filter(Student.user_id == current_user.id).first()
        if student:
            query = query.filter(Attendance.student_id == student.id)
    
    attendances = query.all()
    
    return {
        "success": True,
        "data": [
            {
                "id": att.id,
                "student_id": att.student_id,
                "subject_id": att.subject_id,
                "date": att.date.isoformat(),
                "status": att.status,
                "marked_at": att.marked_at.isoformat()
            }
            for att in attendances
        ]
    }

@router.get("/grades")
async def get_grade_report(
    subject_id: str = None,
    exam_type: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get grade report with filters"""
    
    query = db.query(Grade)
    
    if subject_id:
        query = query.filter(Grade.subject_id == subject_id)
    
    if exam_type:
        query = query.filter(Grade.exam_type == exam_type)
    
    # Role-based filtering
    if current_user.role == "teacher":
        teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
        if teacher:
            query = query.filter(Grade.graded_by == teacher.id)
    
    elif current_user.role == "student":
        student = db.query(Student).filter(Student.user_id == current_user.id).first()
        if student:
            query = query.filter(Grade.student_id == student.id)
    
    grades = query.all()
    
    return {
        "success": True,
        "data": [
            {
                "id": grade.id,
                "student_id": grade.student_id,
                "subject_id": grade.subject_id,
                "exam_type": grade.exam_type,
                "marks_obtained": grade.marks_obtained,
                "max_marks": grade.max_marks,
                "grade_letter": grade.grade_letter,
                "graded_at": grade.graded_at.isoformat()
            }
            for grade in grades
        ]
    }

@router.get("/fees")
async def get_fee_report(
    status: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get fee report with filters"""
    
    query = db.query(Fee)
    
    if status:
        query = query.filter(Fee.status == status)
    
    # Role-based filtering
    if current_user.role == "student":
        student = db.query(Student).filter(Student.user_id == current_user.id).first()
        if student:
            query = query.filter(Fee.student_id == student.id)
    
    fees = query.all()
    
    return {
        "success": True,
        "data": [
            {
                "id": fee.id,
                "student_id": fee.student_id,
                "fee_type": fee.fee_type,
                "amount": fee.amount,
                "due_date": fee.due_date.isoformat(),
                "status": fee.status,
                "paid_date": fee.paid_date.isoformat() if fee.paid_date else None
            }
            for fee in fees
        ]
    }