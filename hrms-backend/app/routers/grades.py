from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from ..database import get_db
from ..models.user import User
from ..models.student import Student
from ..models.teacher import Teacher
from ..models.subject import Subject
from ..models.grade import Grade, ExamType
from ..routers.auth import get_current_user
from pydantic import BaseModel

router = APIRouter()

class GradeCreate(BaseModel):
    student_id: str
    subject_id: str
    exam_type: ExamType
    marks_obtained: float
    max_marks: float
    comments: Optional[str] = None

class GradeUpdate(BaseModel):
    marks_obtained: Optional[float] = None
    max_marks: Optional[float] = None
    grade_letter: Optional[str] = None
    grade_points: Optional[float] = None
    comments: Optional[str] = None

def calculate_grade_letter(percentage: float) -> str:
    """Calculate grade letter based on percentage"""
    if percentage >= 90:
        return "A+"
    elif percentage >= 85:
        return "A"
    elif percentage >= 80:
        return "A-"
    elif percentage >= 75:
        return "B+"
    elif percentage >= 70:
        return "B"
    elif percentage >= 65:
        return "B-"
    elif percentage >= 60:
        return "C+"
    elif percentage >= 55:
        return "C"
    elif percentage >= 50:
        return "C-"
    elif percentage >= 45:
        return "D"
    else:
        return "F"

def calculate_grade_points(grade_letter: str) -> float:
    """Calculate grade points based on grade letter"""
    grade_points_map = {
        "A+": 4.0, "A": 4.0, "A-": 3.7,
        "B+": 3.3, "B": 3.0, "B-": 2.7,
        "C+": 2.3, "C": 2.0, "C-": 1.7,
        "D": 1.0, "F": 0.0
    }
    return grade_points_map.get(grade_letter, 0.0)

@router.post("/")
async def create_grade(
    grade_data: GradeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new grade record"""
    
    # Verify teacher permission
    if current_user.role != "teacher" and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only teachers can create grades")
    
    # Get teacher info
    teacher = None
    if current_user.role == "teacher":
        teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
        if not teacher:
            raise HTTPException(status_code=404, detail="Teacher profile not found")
    
    # Verify student exists
    student = db.query(Student).filter(Student.id == grade_data.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Verify subject exists
    subject = db.query(Subject).filter(Subject.id == grade_data.subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    # Check if teacher is assigned to this subject
    if teacher and subject.teacher_id != teacher.id:
        raise HTTPException(status_code=403, detail="You are not assigned to this subject")
    
    # Calculate percentage and grade
    percentage = (grade_data.marks_obtained / grade_data.max_marks) * 100
    grade_letter = calculate_grade_letter(percentage)
    grade_points = calculate_grade_points(grade_letter)
    
    # Check if grade already exists for this combination
    existing_grade = db.query(Grade).filter(
        Grade.student_id == grade_data.student_id,
        Grade.subject_id == grade_data.subject_id,
        Grade.exam_type == grade_data.exam_type
    ).first()
    
    if existing_grade:
        # Update existing grade
        existing_grade.marks_obtained = grade_data.marks_obtained
        existing_grade.max_marks = grade_data.max_marks
        existing_grade.grade_letter = grade_letter
        existing_grade.grade_points = grade_points
        existing_grade.comments = grade_data.comments
        existing_grade.graded_at = datetime.now()
        if teacher:
            existing_grade.graded_by = teacher.id
    else:
        # Create new grade
        grade = Grade(
            student_id=grade_data.student_id,
            subject_id=grade_data.subject_id,
            exam_type=grade_data.exam_type,
            marks_obtained=grade_data.marks_obtained,
            max_marks=grade_data.max_marks,
            grade_letter=grade_letter,
            grade_points=grade_points,
            graded_by=teacher.id if teacher else current_user.id,
            graded_at=datetime.now(),
            comments=grade_data.comments
        )
        db.add(grade)
    
    db.commit()
    
    return {"success": True, "message": "Grade recorded successfully"}

@router.get("/{grade_id}")
async def get_grade(
    grade_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get grade details by ID"""
    
    grade = db.query(Grade).filter(Grade.id == grade_id).first()
    if not grade:
        raise HTTPException(status_code=404, detail="Grade not found")
    
    # Role-based access control
    if current_user.role == "student":
        student = db.query(Student).filter(Student.user_id == current_user.id).first()
        if not student or student.id != grade.student_id:
            raise HTTPException(status_code=403, detail="Access denied")
    elif current_user.role == "teacher":
        teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
        if teacher and grade.graded_by != teacher.id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    # Get related data
    student = db.query(Student).filter(Student.id == grade.student_id).first()
    student_user = db.query(User).filter(User.id == student.user_id).first() if student else None
    subject = db.query(Subject).filter(Subject.id == grade.subject_id).first()
    teacher = db.query(Teacher).filter(Teacher.id == grade.graded_by).first()
    teacher_user = db.query(User).filter(User.id == teacher.user_id).first() if teacher else None
    
    return {
        "success": True,
        "data": {
            "id": grade.id,
            "student": {
                "id": student.id if student else "",
                "name": student_user.name if student_user else "",
                "student_id": student.student_id if student else ""
            },
            "subject": {
                "id": subject.id if subject else "",
                "name": subject.name if subject else "",
                "code": subject.code if subject else ""
            },
            "exam_type": grade.exam_type,
            "marks_obtained": grade.marks_obtained,
            "max_marks": grade.max_marks,
            "percentage": (grade.marks_obtained / grade.max_marks) * 100,
            "grade_letter": grade.grade_letter,
            "grade_points": grade.grade_points,
            "graded_by": teacher_user.name if teacher_user else "",
            "graded_at": grade.graded_at.isoformat(),
            "comments": grade.comments
        }
    }

@router.put("/{grade_id}")
async def update_grade(
    grade_id: str,
    grade_data: GradeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update grade information"""
    
    grade = db.query(Grade).filter(Grade.id == grade_id).first()
    if not grade:
        raise HTTPException(status_code=404, detail="Grade not found")
    
    # Verify teacher permission
    if current_user.role != "teacher" and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only teachers can update grades")
    
    # Check if teacher is the one who graded this
    if current_user.role == "teacher":
        teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
        if teacher and grade.graded_by != teacher.id:
            raise HTTPException(status_code=403, detail="You can only update grades you created")
    
    # Update fields
    if grade_data.marks_obtained is not None:
        grade.marks_obtained = grade_data.marks_obtained
    
    if grade_data.max_marks is not None:
        grade.max_marks = grade_data.max_marks
    
    # Recalculate grade if marks changed
    if grade_data.marks_obtained is not None or grade_data.max_marks is not None:
        percentage = (grade.marks_obtained / grade.max_marks) * 100
        grade.grade_letter = calculate_grade_letter(percentage)
        grade.grade_points = calculate_grade_points(grade.grade_letter)
    
    if grade_data.grade_letter:
        grade.grade_letter = grade_data.grade_letter
        grade.grade_points = calculate_grade_points(grade_data.grade_letter)
    
    if grade_data.grade_points is not None:
        grade.grade_points = grade_data.grade_points
    
    if grade_data.comments:
        grade.comments = grade_data.comments
    
    grade.graded_at = datetime.now()
    db.commit()
    
    return {"success": True, "message": "Grade updated successfully"}

@router.delete("/{grade_id}")
async def delete_grade(
    grade_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a grade record"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete grades")
    
    grade = db.query(Grade).filter(Grade.id == grade_id).first()
    if not grade:
        raise HTTPException(status_code=404, detail="Grade not found")
    
    db.delete(grade)
    db.commit()
    
    return {"success": True, "message": "Grade deleted successfully"}

@router.get("/subject/{subject_id}")
async def get_subject_grades(
    subject_id: str,
    exam_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all grades for a subject"""
    
    # Verify subject exists
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    # Role-based access control
    if current_user.role == "teacher":
        teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
        if teacher and subject.teacher_id != teacher.id:
            raise HTTPException(status_code=403, detail="Access denied to this subject")
    
    # Build query
    query = db.query(Grade).filter(Grade.subject_id == subject_id)
    
    if exam_type:
        query = query.filter(Grade.exam_type == exam_type)
    
    grades = query.all()
    
    result = []
    for grade in grades:
        student = db.query(Student).filter(Student.id == grade.student_id).first()
        student_user = db.query(User).filter(User.id == student.user_id).first() if student else None
        
        result.append({
            "id": grade.id,
            "student": {
                "id": student.id if student else "",
                "name": student_user.name if student_user else "",
                "student_id": student.student_id if student else ""
            },
            "exam_type": grade.exam_type,
            "marks_obtained": grade.marks_obtained,
            "max_marks": grade.max_marks,
            "percentage": (grade.marks_obtained / grade.max_marks) * 100,
            "grade_letter": grade.grade_letter,
            "grade_points": grade.grade_points,
            "graded_at": grade.graded_at.isoformat()
        })
    
    return {"success": True, "data": result}

@router.post("/bulk-upload")
async def bulk_upload_grades(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Bulk upload grades from CSV file"""
    
    if current_user.role != "teacher" and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only teachers can upload grades")
    
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    # Read and process CSV
    import csv
    import io
    
    content = await file.read()
    csv_content = content.decode('utf-8')
    csv_reader = csv.DictReader(io.StringIO(csv_content))
    
    processed_count = 0
    errors = []
    
    for row_num, row in enumerate(csv_reader, start=2):
        try:
            # Expected columns: student_id, subject_id, exam_type, marks_obtained, max_marks, comments
            student_id = row.get('student_id', '').strip()
            subject_id = row.get('subject_id', '').strip()
            exam_type = row.get('exam_type', '').strip()
            marks_obtained = float(row.get('marks_obtained', 0))
            max_marks = float(row.get('max_marks', 100))
            comments = row.get('comments', '').strip()
            
            if not all([student_id, subject_id, exam_type]):
                errors.append(f"Row {row_num}: Missing required fields")
                continue
            
            # Verify student and subject exist
            student = db.query(Student).filter(Student.student_id == student_id).first()
            if not student:
                errors.append(f"Row {row_num}: Student {student_id} not found")
                continue
            
            subject = db.query(Subject).filter(Subject.code == subject_id).first()
            if not subject:
                errors.append(f"Row {row_num}: Subject {subject_id} not found")
                continue
            
            # Create grade record
            grade_data = GradeCreate(
                student_id=student.id,
                subject_id=subject.id,
                exam_type=ExamType(exam_type.lower()),
                marks_obtained=marks_obtained,
                max_marks=max_marks,
                comments=comments if comments else None
            )
            
            # Use the create_grade logic
            percentage = (marks_obtained / max_marks) * 100
            grade_letter = calculate_grade_letter(percentage)
            grade_points = calculate_grade_points(grade_letter)
            
            # Get teacher info
            teacher = None
            if current_user.role == "teacher":
                teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
            
            grade = Grade(
                student_id=student.id,
                subject_id=subject.id,
                exam_type=ExamType(exam_type.lower()),
                marks_obtained=marks_obtained,
                max_marks=max_marks,
                grade_letter=grade_letter,
                grade_points=grade_points,
                graded_by=teacher.id if teacher else current_user.id,
                graded_at=datetime.now(),
                comments=comments if comments else None
            )
            db.add(grade)
            processed_count += 1
            
        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Processed {processed_count} grades",
        "data": {
            "processed_count": processed_count,
            "errors": errors
        }
    }