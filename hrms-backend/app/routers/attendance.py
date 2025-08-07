from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from datetime import datetime, date
from typing import List, Optional
from ..database import get_db
from ..models.user import User
from ..models.student import Student
from ..models.teacher import Teacher
from ..models.subject import Subject
from ..models.attendance import Attendance, AttendanceStatus
from ..models.enrollment import Enrollment
from ..routers.auth import get_current_user
from ..services.face_recognition import face_recognition_service
from pydantic import BaseModel
import json

router = APIRouter()

class AttendanceCreate(BaseModel):
    student_id: str
    subject_id: str
    date: date
    status: AttendanceStatus
    notes: Optional[str] = None

class BulkAttendanceCreate(BaseModel):
    subject_id: str
    date: date
    attendance_list: List[dict]  # [{"student_id": "...", "status": "..."}]

@router.post("/mark")
async def mark_attendance(
    attendance_data: AttendanceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark attendance for a single student"""
    
    # Verify teacher permission
    if current_user.role != "teacher" and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only teachers can mark attendance")
    
    # Get teacher info
    teacher = None
    if current_user.role == "teacher":
        teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
        if not teacher:
            raise HTTPException(status_code=404, detail="Teacher profile not found")
    
    # Verify student exists
    student = db.query(Student).filter(Student.id == attendance_data.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Verify subject exists
    subject = db.query(Subject).filter(Subject.id == attendance_data.subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    # Check if attendance already marked for this date
    existing_attendance = db.query(Attendance).filter(
        Attendance.student_id == attendance_data.student_id,
        Attendance.subject_id == attendance_data.subject_id,
        Attendance.date == attendance_data.date
    ).first()
    
    if existing_attendance:
        # Update existing attendance
        existing_attendance.status = attendance_data.status
        existing_attendance.notes = attendance_data.notes
        existing_attendance.marked_at = datetime.now()
        if teacher:
            existing_attendance.marked_by = teacher.id
    else:
        # Create new attendance record
        attendance = Attendance(
            student_id=attendance_data.student_id,
            subject_id=attendance_data.subject_id,
            date=attendance_data.date,
            status=attendance_data.status,
            marked_by=teacher.id if teacher else current_user.id,
            marked_at=datetime.now(),
            notes=attendance_data.notes
        )
        db.add(attendance)
    
    db.commit()
    
    return {"success": True, "message": "Attendance marked successfully"}

@router.post("/bulk-mark")
async def bulk_mark_attendance(
    attendance_data: BulkAttendanceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark attendance for multiple students"""
    
    # Verify teacher permission
    if current_user.role != "teacher" and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only teachers can mark attendance")
    
    # Get teacher info
    teacher = None
    if current_user.role == "teacher":
        teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
        if not teacher:
            raise HTTPException(status_code=404, detail="Teacher profile not found")
    
    # Verify subject exists
    subject = db.query(Subject).filter(Subject.id == attendance_data.subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    marked_count = 0
    
    for attendance_item in attendance_data.attendance_list:
        student_id = attendance_item.get("student_id")
        status = attendance_item.get("status")
        
        if not student_id or not status:
            continue
        
        # Check if attendance already marked
        existing_attendance = db.query(Attendance).filter(
            Attendance.student_id == student_id,
            Attendance.subject_id == attendance_data.subject_id,
            Attendance.date == attendance_data.date
        ).first()
        
        if existing_attendance:
            # Update existing
            existing_attendance.status = AttendanceStatus(status)
            existing_attendance.marked_at = datetime.now()
            if teacher:
                existing_attendance.marked_by = teacher.id
        else:
            # Create new
            attendance = Attendance(
                student_id=student_id,
                subject_id=attendance_data.subject_id,
                date=attendance_data.date,
                status=AttendanceStatus(status),
                marked_by=teacher.id if teacher else current_user.id,
                marked_at=datetime.now()
            )
            db.add(attendance)
        
        marked_count += 1
    
    db.commit()
    
    return {
        "success": True, 
        "message": f"Attendance marked for {marked_count} students"
    }

@router.post("/upload-image")
async def upload_attendance_image(
    subject_id: str = Form(...),
    date_str: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload image for automatic attendance marking using face recognition"""
    
    # Verify teacher permission
    if current_user.role != "teacher" and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only teachers can mark attendance")
    
    # Get teacher info
    teacher = None
    if current_user.role == "teacher":
        teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
        if not teacher:
            raise HTTPException(status_code=404, detail="Teacher profile not found")
    
    # Verify subject exists
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    # Parse date
    try:
        attendance_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Read image data
    image_data = await file.read()
    
    # Get enrolled students for this subject
    enrolled_students = db.query(Student).join(
        Enrollment, Student.id == Enrollment.student_id
    ).filter(Enrollment.subject_id == subject_id).all()
    
    if not enrolled_students:
        raise HTTPException(status_code=400, detail="No students enrolled in this subject")
    
    # Prepare known face encodings
    known_encodings = {}
    for student in enrolled_students:
        if student.face_encoding:
            try:
                encoding = json.loads(student.face_encoding)
                known_encodings[student.id] = encoding
            except:
                continue
    
    if not known_encodings:
        raise HTTPException(status_code=400, detail="No face encodings found for enrolled students")
    
    # Recognize faces in the uploaded image
    recognized_faces = face_recognition_service.recognize_faces_in_image(image_data, known_encodings)
    
    # Mark attendance based on recognition results
    present_students = set()
    recognition_results = []
    
    for face in recognized_faces:
        if face['student_id'] and face['confidence'] > 0.5:  # Confidence threshold
            present_students.add(face['student_id'])
            
            # Mark as present
            existing_attendance = db.query(Attendance).filter(
                Attendance.student_id == face['student_id'],
                Attendance.subject_id == subject_id,
                Attendance.date == attendance_date
            ).first()
            
            if existing_attendance:
                existing_attendance.status = AttendanceStatus.PRESENT
                existing_attendance.confidence_score = str(face['confidence'])
                existing_attendance.marked_at = datetime.now()
            else:
                attendance = Attendance(
                    student_id=face['student_id'],
                    subject_id=subject_id,
                    date=attendance_date,
                    status=AttendanceStatus.PRESENT,
                    marked_by=teacher.id if teacher else current_user.id,
                    marked_at=datetime.now(),
                    confidence_score=str(face['confidence'])
                )
                db.add(attendance)
            
            recognition_results.append({
                "student_id": face['student_id'],
                "status": "present",
                "confidence": face['confidence']
            })
    
    # Mark absent students
    for student in enrolled_students:
        if student.id not in present_students:
            existing_attendance = db.query(Attendance).filter(
                Attendance.student_id == student.id,
                Attendance.subject_id == subject_id,
                Attendance.date == attendance_date
            ).first()
            
            if existing_attendance:
                existing_attendance.status = AttendanceStatus.ABSENT
                existing_attendance.marked_at = datetime.now()
            else:
                attendance = Attendance(
                    student_id=student.id,
                    subject_id=subject_id,
                    date=attendance_date,
                    status=AttendanceStatus.ABSENT,
                    marked_by=teacher.id if teacher else current_user.id,
                    marked_at=datetime.now()
                )
                db.add(attendance)
            
            recognition_results.append({
                "student_id": student.id,
                "status": "absent",
                "confidence": 0
            })
    
    db.commit()
    
    # Generate processed image with face rectangles
    processed_image = face_recognition_service.draw_face_rectangles(image_data, recognized_faces)
    
    return {
        "success": True,
        "message": f"Attendance marked for {len(enrolled_students)} students",
        "data": {
            "total_students": len(enrolled_students),
            "present_count": len(present_students),
            "absent_count": len(enrolled_students) - len(present_students),
            "recognition_results": recognition_results
        }
    }

@router.get("/subject/{subject_id}")
async def get_subject_attendance(
    subject_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get attendance records for a subject"""
    
    # Verify subject exists
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    # Build query
    query = db.query(Attendance).filter(Attendance.subject_id == subject_id)
    
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            query = query.filter(Attendance.date >= start_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
            query = query.filter(Attendance.date <= end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")
    
    # Role-based filtering
    if current_user.role == "student":
        student = db.query(Student).filter(Student.user_id == current_user.id).first()
        if student:
            query = query.filter(Attendance.student_id == student.id)
    elif current_user.role == "teacher":
        teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
        if teacher and subject.teacher_id != teacher.id:
            raise HTTPException(status_code=403, detail="Access denied to this subject")
    
    attendances = query.all()
    
    return {
        "success": True,
        "data": [
            {
                "id": att.id,
                "student_id": att.student_id,
                "date": att.date.isoformat(),
                "status": att.status,
                "marked_at": att.marked_at.isoformat(),
                "notes": att.notes,
                "confidence_score": att.confidence_score
            }
            for att in attendances
        ]
    }