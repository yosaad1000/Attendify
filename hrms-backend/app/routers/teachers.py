from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..models.user import User
from ..models.teacher import Teacher
from ..models.department import Department
from ..models.subject import Subject
from ..routers.auth import get_current_user
from pydantic import BaseModel

router = APIRouter()

class TeacherCreate(BaseModel):
    name: str
    email: str
    teacher_id: str
    department_id: str
    qualification: str
    experience_years: int
    specialization: Optional[str] = None

class TeacherUpdate(BaseModel):
    name: Optional[str] = None
    department_id: Optional[str] = None
    qualification: Optional[str] = None
    experience_years: Optional[int] = None
    specialization: Optional[str] = None
    bio: Optional[str] = None

@router.get("/")
async def get_teachers(
    skip: int = 0,
    limit: int = 100,
    department_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of teachers with optional filters"""
    
    query = db.query(Teacher).join(User, Teacher.user_id == User.id)
    
    if department_id:
        query = query.filter(Teacher.department_id == department_id)
    
    # Role-based filtering
    if current_user.role == "teacher":
        teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
        if teacher:
            query = query.filter(Teacher.id == teacher.id)
    
    teachers = query.offset(skip).limit(limit).all()
    
    result = []
    for teacher in teachers:
        user = db.query(User).filter(User.id == teacher.user_id).first()
        department = db.query(Department).filter(Department.id == teacher.department_id).first()
        
        # Get subjects taught by this teacher
        subjects = db.query(Subject).filter(Subject.teacher_id == teacher.id).all()
        
        result.append({
            "id": teacher.id,
            "teacher_id": teacher.teacher_id,
            "name": user.name if user else "",
            "email": user.email if user else "",
            "department": department.name if department else "",
            "qualification": teacher.qualification,
            "experience_years": teacher.experience_years,
            "specialization": teacher.specialization,
            "subjects_count": len(subjects),
            "created_at": teacher.created_at.isoformat()
        })
    
    return {"success": True, "data": result}

@router.get("/{teacher_id}")
async def get_teacher(
    teacher_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get teacher details by ID"""
    
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    # Role-based access control
    if current_user.role == "teacher":
        current_teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
        if not current_teacher or current_teacher.id != teacher_id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    user = db.query(User).filter(User.id == teacher.user_id).first()
    department = db.query(Department).filter(Department.id == teacher.department_id).first()
    subjects = db.query(Subject).filter(Subject.teacher_id == teacher.id).all()
    
    return {
        "success": True,
        "data": {
            "id": teacher.id,
            "teacher_id": teacher.teacher_id,
            "name": user.name if user else "",
            "email": user.email if user else "",
            "phone": user.phone if user else "",
            "address": user.address if user else "",
            "department": {
                "id": department.id if department else "",
                "name": department.name if department else "",
                "code": department.code if department else ""
            },
            "qualification": teacher.qualification,
            "experience_years": teacher.experience_years,
            "specialization": teacher.specialization,
            "bio": teacher.bio,
            "subjects": [
                {
                    "id": subject.id,
                    "name": subject.name,
                    "code": subject.code,
                    "semester": subject.semester,
                    "credits": subject.credits
                }
                for subject in subjects
            ],
            "created_at": teacher.created_at.isoformat()
        }
    }

@router.post("/")
async def create_teacher(
    teacher_data: TeacherCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new teacher (Admin only)"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create teachers")
    
    # Check if teacher ID already exists
    existing_teacher = db.query(Teacher).filter(Teacher.teacher_id == teacher_data.teacher_id).first()
    if existing_teacher:
        raise HTTPException(status_code=400, detail="Teacher ID already exists")
    
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == teacher_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already exists")
    
    # Create user account
    user = User(
        email=teacher_data.email,
        name=teacher_data.name,
        role="teacher",
        hashed_password="temp_password"  # Should be set properly
    )
    db.add(user)
    db.flush()  # Get the user ID
    
    # Create teacher profile
    teacher = Teacher(
        user_id=user.id,
        teacher_id=teacher_data.teacher_id,
        department_id=teacher_data.department_id,
        qualification=teacher_data.qualification,
        experience_years=teacher_data.experience_years,
        specialization=teacher_data.specialization
    )
    db.add(teacher)
    db.commit()
    
    return {"success": True, "message": "Teacher created successfully", "data": {"id": teacher.id}}

@router.put("/{teacher_id}")
async def update_teacher(
    teacher_id: str,
    teacher_data: TeacherUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update teacher information"""
    
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    # Role-based access control
    if current_user.role == "teacher":
        current_teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
        if not current_teacher or current_teacher.id != teacher_id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    # Update fields
    if teacher_data.name:
        user = db.query(User).filter(User.id == teacher.user_id).first()
        if user:
            user.name = teacher_data.name
    
    if teacher_data.department_id:
        teacher.department_id = teacher_data.department_id
    
    if teacher_data.qualification:
        teacher.qualification = teacher_data.qualification
    
    if teacher_data.experience_years is not None:
        teacher.experience_years = teacher_data.experience_years
    
    if teacher_data.specialization:
        teacher.specialization = teacher_data.specialization
    
    if teacher_data.bio:
        teacher.bio = teacher_data.bio
    
    db.commit()
    
    return {"success": True, "message": "Teacher updated successfully"}

@router.delete("/{teacher_id}")
async def delete_teacher(
    teacher_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a teacher (Admin only)"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete teachers")
    
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    # Delete associated user account
    user = db.query(User).filter(User.id == teacher.user_id).first()
    if user:
        db.delete(user)
    
    db.delete(teacher)
    db.commit()
    
    return {"success": True, "message": "Teacher deleted successfully"}

@router.get("/{teacher_id}/subjects")
async def get_teacher_subjects(
    teacher_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get subjects taught by a teacher"""
    
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    # Role-based access control
    if current_user.role == "teacher":
        current_teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
        if not current_teacher or current_teacher.id != teacher_id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    subjects = db.query(Subject).filter(Subject.teacher_id == teacher_id).all()
    
    return {
        "success": True,
        "data": [
            {
                "id": subject.id,
                "name": subject.name,
                "code": subject.code,
                "semester": subject.semester,
                "credits": subject.credits,
                "is_elective": subject.is_elective,
                "description": subject.description
            }
            for subject in subjects
        ]
    }