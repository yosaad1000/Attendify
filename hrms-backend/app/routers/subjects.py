from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..models.user import User
from ..models.subject import Subject
from ..models.department import Department
from ..models.teacher import Teacher
from ..routers.auth import get_current_user
from pydantic import BaseModel

router = APIRouter()

class SubjectCreate(BaseModel):
    name: str
    code: str
    department_id: str
    teacher_id: Optional[str] = None
    semester: int
    credits: int
    is_elective: bool = False
    description: Optional[str] = None

class SubjectUpdate(BaseModel):
    name: Optional[str] = None
    teacher_id: Optional[str] = None
    credits: Optional[int] = None
    is_elective: Optional[bool] = None
    description: Optional[str] = None

@router.get("/")
async def get_subjects(
    skip: int = 0,
    limit: int = 100,
    department_id: Optional[str] = None,
    semester: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of subjects with optional filters"""
    
    query = db.query(Subject)
    
    if department_id:
        query = query.filter(Subject.department_id == department_id)
    
    if semester:
        query = query.filter(Subject.semester == semester)
    
    # Role-based filtering
    if current_user.role == "teacher":
        teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
        if teacher:
            query = query.filter(Subject.teacher_id == teacher.id)
    
    subjects = query.offset(skip).limit(limit).all()
    
    result = []
    for subject in subjects:
        department = db.query(Department).filter(Department.id == subject.department_id).first()
        teacher = db.query(Teacher).filter(Teacher.id == subject.teacher_id).first() if subject.teacher_id else None
        teacher_user = db.query(User).filter(User.id == teacher.user_id).first() if teacher else None
        
        result.append({
            "id": subject.id,
            "name": subject.name,
            "code": subject.code,
            "department": department.name if department else "",
            "teacher": teacher_user.name if teacher_user else "Not Assigned",
            "semester": subject.semester,
            "credits": subject.credits,
            "is_elective": subject.is_elective,
            "created_at": subject.created_at.isoformat()
        })
    
    return {"success": True, "data": result}

@router.get("/{subject_id}")
async def get_subject(
    subject_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get subject details by ID"""
    
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    department = db.query(Department).filter(Department.id == subject.department_id).first()
    teacher = db.query(Teacher).filter(Teacher.id == subject.teacher_id).first() if subject.teacher_id else None
    teacher_user = db.query(User).filter(User.id == teacher.user_id).first() if teacher else None
    
    return {
        "success": True,
        "data": {
            "id": subject.id,
            "name": subject.name,
            "code": subject.code,
            "department": {
                "id": department.id if department else "",
                "name": department.name if department else "",
                "code": department.code if department else ""
            },
            "teacher": {
                "id": teacher.id if teacher else "",
                "name": teacher_user.name if teacher_user else "",
                "teacher_id": teacher.teacher_id if teacher else ""
            } if teacher else None,
            "semester": subject.semester,
            "credits": subject.credits,
            "is_elective": subject.is_elective,
            "description": subject.description,
            "syllabus_url": subject.syllabus_url,
            "classroom_id": subject.classroom_id,
            "created_at": subject.created_at.isoformat()
        }
    }

@router.post("/")
async def create_subject(
    subject_data: SubjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new subject (Admin only)"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create subjects")
    
    # Check if subject code already exists
    existing_subject = db.query(Subject).filter(Subject.code == subject_data.code).first()
    if existing_subject:
        raise HTTPException(status_code=400, detail="Subject code already exists")
    
    # Verify department exists
    department = db.query(Department).filter(Department.id == subject_data.department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")
    
    # Verify teacher exists if provided
    if subject_data.teacher_id:
        teacher = db.query(Teacher).filter(Teacher.id == subject_data.teacher_id).first()
        if not teacher:
            raise HTTPException(status_code=404, detail="Teacher not found")
    
    # Create subject
    subject = Subject(
        name=subject_data.name,
        code=subject_data.code,
        department_id=subject_data.department_id,
        teacher_id=subject_data.teacher_id,
        semester=subject_data.semester,
        credits=subject_data.credits,
        is_elective=subject_data.is_elective,
        description=subject_data.description
    )
    db.add(subject)
    db.commit()
    
    return {"success": True, "message": "Subject created successfully", "data": {"id": subject.id}}

@router.put("/{subject_id}")
async def update_subject(
    subject_id: str,
    subject_data: SubjectUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update subject information"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update subjects")
    
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    # Update fields
    if subject_data.name:
        subject.name = subject_data.name
    
    if subject_data.teacher_id:
        # Verify teacher exists
        teacher = db.query(Teacher).filter(Teacher.id == subject_data.teacher_id).first()
        if not teacher:
            raise HTTPException(status_code=404, detail="Teacher not found")
        subject.teacher_id = subject_data.teacher_id
    
    if subject_data.credits is not None:
        subject.credits = subject_data.credits
    
    if subject_data.is_elective is not None:
        subject.is_elective = subject_data.is_elective
    
    if subject_data.description:
        subject.description = subject_data.description
    
    db.commit()
    
    return {"success": True, "message": "Subject updated successfully"}

@router.delete("/{subject_id}")
async def delete_subject(
    subject_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a subject (Admin only)"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete subjects")
    
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    db.delete(subject)
    db.commit()
    
    return {"success": True, "message": "Subject deleted successfully"}