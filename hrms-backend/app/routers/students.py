from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..models.user import User
from ..models.student import Student
from ..models.department import Department
from ..routers.auth import get_current_user
from ..services.face_recognition import face_recognition_service
from pydantic import BaseModel
import json

router = APIRouter()

class StudentCreate(BaseModel):
    name: str
    email: str
    student_id: str
    department_id: str
    semester: int
    batch_year: int

class StudentUpdate(BaseModel):
    name: Optional[str] = None
    department_id: Optional[str] = None
    semester: Optional[int] = None
    cgpa: Optional[float] = None

@router.get("/")
async def get_students(
    skip: int = 0,
    limit: int = 100,
    department_id: Optional[str] = None,
    semester: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of students with optional filters"""
    
    query = db.query(Student).join(User, Student.user_id == User.id)
    
    if department_id:
        query = query.filter(Student.department_id == department_id)
    
    if semester:
        query = query.filter(Student.semester == semester)
    
    # Role-based filtering
    if current_user.role == "student":
        student = db.query(Student).filter(Student.user_id == current_user.id).first()
        if student:
            query = query.filter(Student.id == student.id)
    
    students = query.offset(skip).limit(limit).all()
    
    result = []
    for student in students:
        user = db.query(User).filter(User.id == student.user_id).first()
        department = db.query(Department).filter(Department.id == student.department_id).first()
        
        result.append({
            "id": student.id,
            "student_id": student.student_id,
            "name": user.name if user else "",
            "email": user.email if user else "",
            "department": department.name if department else "",
            "semester": student.semester,
            "batch_year": student.batch_year,
            "cgpa": student.cgpa,
            "fee_status": student.fee_status,
            "created_at": student.created_at.isoformat()
        })
    
    return {"success": True, "data": result}

@router.get("/{student_id}")
async def get_student(
    student_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get student details by ID"""
    
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Role-based access control
    if current_user.role == "student":
        current_student = db.query(Student).filter(Student.user_id == current_user.id).first()
        if not current_student or current_student.id != student_id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    user = db.query(User).filter(User.id == student.user_id).first()
    department = db.query(Department).filter(Department.id == student.department_id).first()
    
    return {
        "success": True,
        "data": {
            "id": student.id,
            "student_id": student.student_id,
            "name": user.name if user else "",
            "email": user.email if user else "",
            "phone": user.phone if user else "",
            "address": user.address if user else "",
            "department": {
                "id": department.id if department else "",
                "name": department.name if department else "",
                "code": department.code if department else ""
            },
            "semester": student.semester,
            "batch_year": student.batch_year,
            "cgpa": student.cgpa,
            "total_credits": student.total_credits,
            "fee_status": student.fee_status,
            "has_face_encoding": bool(student.face_encoding),
            "created_at": student.created_at.isoformat()
        }
    }

@router.post("/")
async def create_student(
    student_data: StudentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new student (Admin only)"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create students")
    
    # Check if student ID already exists
    existing_student = db.query(Student).filter(Student.student_id == student_data.student_id).first()
    if existing_student:
        raise HTTPException(status_code=400, detail="Student ID already exists")
    
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == student_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already exists")
    
    # Create user account
    user = User(
        email=student_data.email,
        name=student_data.name,
        role="student",
        hashed_password="temp_password"  # Should be set properly
    )
    db.add(user)
    db.flush()  # Get the user ID
    
    # Create student profile
    student = Student(
        user_id=user.id,
        student_id=student_data.student_id,
        department_id=student_data.department_id,
        semester=student_data.semester,
        batch_year=student_data.batch_year
    )
    db.add(student)
    db.commit()
    
    return {"success": True, "message": "Student created successfully", "data": {"id": student.id}}

@router.put("/{student_id}")
async def update_student(
    student_id: str,
    student_data: StudentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update student information"""
    
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Role-based access control
    if current_user.role == "student":
        current_student = db.query(Student).filter(Student.user_id == current_user.id).first()
        if not current_student or current_student.id != student_id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    # Update fields
    if student_data.name:
        user = db.query(User).filter(User.id == student.user_id).first()
        if user:
            user.name = student_data.name
    
    if student_data.department_id:
        student.department_id = student_data.department_id
    
    if student_data.semester:
        student.semester = student_data.semester
    
    if student_data.cgpa is not None:
        student.cgpa = student_data.cgpa
    
    db.commit()
    
    return {"success": True, "message": "Student updated successfully"}

@router.delete("/{student_id}")
async def delete_student(
    student_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a student (Admin only)"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete students")
    
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Delete associated user account
    user = db.query(User).filter(User.id == student.user_id).first()
    if user:
        db.delete(user)
    
    db.delete(student)
    db.commit()
    
    return {"success": True, "message": "Student deleted successfully"}

@router.post("/{student_id}/upload-photo")
async def upload_student_photo(
    student_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload student photo for face recognition"""
    
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Role-based access control
    if current_user.role == "student":
        current_student = db.query(Student).filter(Student.user_id == current_user.id).first()
        if not current_student or current_student.id != student_id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    # Validate file type
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Read image data
    image_data = await file.read()
    
    # Extract face encoding
    face_encoding = face_recognition_service.extract_face_encoding(image_data)
    if not face_encoding:
        raise HTTPException(status_code=400, detail="No face detected in the image")
    
    # Save face encoding to student record
    student.face_encoding = json.dumps(face_encoding)
    db.commit()
    
    # Also save to file system for backup
    face_recognition_service.save_face_encoding(student.student_id, face_encoding)
    
    return {"success": True, "message": "Face encoding saved successfully"}

@router.get("/{student_id}/attendance")
async def get_student_attendance(
    student_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get attendance records for a student"""
    
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Role-based access control
    if current_user.role == "student":
        current_student = db.query(Student).filter(Student.user_id == current_user.id).first()
        if not current_student or current_student.id != student_id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    from ..models.attendance import Attendance
    from datetime import datetime
    
    query = db.query(Attendance).filter(Attendance.student_id == student_id)
    
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            query = query.filter(Attendance.date >= start_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format")
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
            query = query.filter(Attendance.date <= end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format")
    
    attendances = query.all()
    
    return {
        "success": True,
        "data": [
            {
                "id": att.id,
                "subject_id": att.subject_id,
                "date": att.date.isoformat(),
                "status": att.status,
                "marked_at": att.marked_at.isoformat()
            }
            for att in attendances
        ]
    }

@router.get("/{student_id}/grades")
async def get_student_grades(
    student_id: str,
    semester: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get grade records for a student"""
    
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Role-based access control
    if current_user.role == "student":
        current_student = db.query(Student).filter(Student.user_id == current_user.id).first()
        if not current_student or current_student.id != student_id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    from ..models.grade import Grade
    
    query = db.query(Grade).filter(Grade.student_id == student_id)
    
    if semester:
        # Join with subject to filter by semester
        from ..models.subject import Subject
        query = query.join(Subject, Grade.subject_id == Subject.id).filter(Subject.semester == semester)
    
    grades = query.all()
    
    return {
        "success": True,
        "data": [
            {
                "id": grade.id,
                "subject_id": grade.subject_id,
                "exam_type": grade.exam_type,
                "marks_obtained": grade.marks_obtained,
                "max_marks": grade.max_marks,
                "grade_letter": grade.grade_letter,
                "grade_points": grade.grade_points,
                "graded_at": grade.graded_at.isoformat()
            }
            for grade in grades
        ]
    }

@router.get("/{student_id}/fees")
async def get_student_fees(
    student_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get fee records for a student"""
    
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Role-based access control
    if current_user.role == "student":
        current_student = db.query(Student).filter(Student.user_id == current_user.id).first()
        if not current_student or current_student.id != student_id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    from ..models.fee import Fee
    
    fees = db.query(Fee).filter(Fee.student_id == student_id).all()
    
    return {
        "success": True,
        "data": [
            {
                "id": fee.id,
                "fee_type": fee.fee_type,
                "amount": fee.amount,
                "due_date": fee.due_date.isoformat(),
                "paid_date": fee.paid_date.isoformat() if fee.paid_date else None,
                "status": fee.status,
                "description": fee.description
            }
            for fee in fees
        ]
    }