from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date
from ..database import get_db
from ..models.user import User
from ..models.student import Student
from ..models.fee import Fee, FeeType, PaymentStatus
from ..routers.auth import get_current_user
from pydantic import BaseModel

router = APIRouter()

class FeeCreate(BaseModel):
    student_id: str
    fee_type: FeeType
    amount: float
    due_date: date
    description: Optional[str] = None

class FeeUpdate(BaseModel):
    amount: Optional[float] = None
    due_date: Optional[date] = None
    status: Optional[PaymentStatus] = None
    description: Optional[str] = None

class PaymentProcess(BaseModel):
    payment_method: str  # card, bank_transfer, cash
    transaction_id: Optional[str] = None

@router.get("/")
async def get_fees(
    skip: int = 0,
    limit: int = 100,
    student_id: Optional[str] = None,
    status: Optional[str] = None,
    fee_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of fees with optional filters"""
    
    query = db.query(Fee)
    
    if student_id:
        query = query.filter(Fee.student_id == student_id)
    
    if status:
        query = query.filter(Fee.status == status)
    
    if fee_type:
        query = query.filter(Fee.fee_type == fee_type)
    
    # Role-based filtering
    if current_user.role == "student":
        student = db.query(Student).filter(Student.user_id == current_user.id).first()
        if student:
            query = query.filter(Fee.student_id == student.id)
    
    fees = query.offset(skip).limit(limit).all()
    
    result = []
    for fee in fees:
        student = db.query(Student).filter(Student.id == fee.student_id).first()
        student_user = db.query(User).filter(User.id == student.user_id).first() if student else None
        
        result.append({
            "id": fee.id,
            "student": {
                "id": student.id if student else "",
                "name": student_user.name if student_user else "",
                "student_id": student.student_id if student else ""
            },
            "fee_type": fee.fee_type,
            "amount": fee.amount,
            "due_date": fee.due_date.isoformat(),
            "paid_date": fee.paid_date.isoformat() if fee.paid_date else None,
            "status": fee.status,
            "description": fee.description,
            "late_fee": fee.late_fee,
            "discount": fee.discount,
            "created_at": fee.created_at.isoformat()
        })
    
    return {"success": True, "data": result}

@router.get("/{fee_id}")
async def get_fee(
    fee_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get fee details by ID"""
    
    fee = db.query(Fee).filter(Fee.id == fee_id).first()
    if not fee:
        raise HTTPException(status_code=404, detail="Fee not found")
    
    # Role-based access control
    if current_user.role == "student":
        student = db.query(Student).filter(Student.user_id == current_user.id).first()
        if not student or student.id != fee.student_id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    student = db.query(Student).filter(Student.id == fee.student_id).first()
    student_user = db.query(User).filter(User.id == student.user_id).first() if student else None
    
    return {
        "success": True,
        "data": {
            "id": fee.id,
            "student": {
                "id": student.id if student else "",
                "name": student_user.name if student_user else "",
                "student_id": student.student_id if student else ""
            },
            "fee_type": fee.fee_type,
            "amount": fee.amount,
            "due_date": fee.due_date.isoformat(),
            "paid_date": fee.paid_date.isoformat() if fee.paid_date else None,
            "status": fee.status,
            "payment_method": fee.payment_method,
            "transaction_id": fee.transaction_id,
            "description": fee.description,
            "late_fee": fee.late_fee,
            "discount": fee.discount,
            "created_at": fee.created_at.isoformat()
        }
    }

@router.post("/")
async def create_fee(
    fee_data: FeeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new fee record (Admin only)"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create fees")
    
    # Verify student exists
    student = db.query(Student).filter(Student.id == fee_data.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Calculate late fee if due date has passed
    late_fee = 0.0
    if fee_data.due_date < date.today():
        days_late = (date.today() - fee_data.due_date).days
        late_fee = min(days_late * 10, fee_data.amount * 0.1)  # $10 per day, max 10% of amount
    
    # Create fee record
    fee = Fee(
        student_id=fee_data.student_id,
        fee_type=fee_data.fee_type,
        amount=fee_data.amount,
        due_date=fee_data.due_date,
        status=PaymentStatus.OVERDUE if fee_data.due_date < date.today() else PaymentStatus.PENDING,
        description=fee_data.description,
        late_fee=late_fee
    )
    db.add(fee)
    db.commit()
    
    return {"success": True, "message": "Fee created successfully", "data": {"id": fee.id}}

@router.put("/{fee_id}")
async def update_fee(
    fee_id: str,
    fee_data: FeeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update fee information (Admin only)"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update fees")
    
    fee = db.query(Fee).filter(Fee.id == fee_id).first()
    if not fee:
        raise HTTPException(status_code=404, detail="Fee not found")
    
    # Update fields
    if fee_data.amount is not None:
        fee.amount = fee_data.amount
    
    if fee_data.due_date:
        fee.due_date = fee_data.due_date
        # Recalculate late fee
        if fee_data.due_date < date.today() and fee.status != PaymentStatus.PAID:
            days_late = (date.today() - fee_data.due_date).days
            fee.late_fee = min(days_late * 10, fee.amount * 0.1)
            fee.status = PaymentStatus.OVERDUE
    
    if fee_data.status:
        fee.status = fee_data.status
    
    if fee_data.description:
        fee.description = fee_data.description
    
    db.commit()
    
    return {"success": True, "message": "Fee updated successfully"}

@router.delete("/{fee_id}")
async def delete_fee(
    fee_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a fee record (Admin only)"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete fees")
    
    fee = db.query(Fee).filter(Fee.id == fee_id).first()
    if not fee:
        raise HTTPException(status_code=404, detail="Fee not found")
    
    if fee.status == PaymentStatus.PAID:
        raise HTTPException(status_code=400, detail="Cannot delete paid fees")
    
    db.delete(fee)
    db.commit()
    
    return {"success": True, "message": "Fee deleted successfully"}

@router.post("/{fee_id}/pay")
async def process_payment(
    fee_id: str,
    payment_data: PaymentProcess,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Process fee payment"""
    
    fee = db.query(Fee).filter(Fee.id == fee_id).first()
    if not fee:
        raise HTTPException(status_code=404, detail="Fee not found")
    
    # Role-based access control
    if current_user.role == "student":
        student = db.query(Student).filter(Student.user_id == current_user.id).first()
        if not student or student.id != fee.student_id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    if fee.status == PaymentStatus.PAID:
        raise HTTPException(status_code=400, detail="Fee already paid")
    
    # Process payment (integrate with Stripe or other payment gateway)
    # For now, we'll simulate payment processing
    
    total_amount = fee.amount + fee.late_fee - fee.discount
    
    # Update fee record
    fee.status = PaymentStatus.PAID
    fee.paid_date = date.today()
    fee.payment_method = payment_data.payment_method
    fee.transaction_id = payment_data.transaction_id or f"TXN_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Update student fee status
    student = db.query(Student).filter(Student.id == fee.student_id).first()
    if student:
        # Check if all fees are paid
        pending_fees = db.query(Fee).filter(
            Fee.student_id == student.id,
            Fee.status.in_([PaymentStatus.PENDING, PaymentStatus.OVERDUE])
        ).count()
        
        if pending_fees == 0:
            student.fee_status = "paid"
        else:
            student.fee_status = "pending"
    
    db.commit()
    
    return {
        "success": True,
        "message": "Payment processed successfully",
        "data": {
            "transaction_id": fee.transaction_id,
            "amount_paid": total_amount,
            "payment_date": fee.paid_date.isoformat()
        }
    }

@router.get("/student/{student_id}/summary")
async def get_student_fee_summary(
    student_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get fee summary for a student"""
    
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Role-based access control
    if current_user.role == "student":
        current_student = db.query(Student).filter(Student.user_id == current_user.id).first()
        if not current_student or current_student.id != student_id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    # Get fee statistics
    from sqlalchemy import func
    
    total_fees = db.query(func.sum(Fee.amount)).filter(Fee.student_id == student_id).scalar() or 0
    paid_fees = db.query(func.sum(Fee.amount)).filter(
        Fee.student_id == student_id,
        Fee.status == PaymentStatus.PAID
    ).scalar() or 0
    pending_fees = db.query(func.sum(Fee.amount + Fee.late_fee - Fee.discount)).filter(
        Fee.student_id == student_id,
        Fee.status.in_([PaymentStatus.PENDING, PaymentStatus.OVERDUE])
    ).scalar() or 0
    
    overdue_count = db.query(Fee).filter(
        Fee.student_id == student_id,
        Fee.status == PaymentStatus.OVERDUE
    ).count()
    
    return {
        "success": True,
        "data": {
            "student_id": student_id,
            "total_fees": total_fees,
            "paid_fees": paid_fees,
            "pending_fees": pending_fees,
            "overdue_count": overdue_count,
            "payment_percentage": (paid_fees / total_fees * 100) if total_fees > 0 else 0
        }
    }