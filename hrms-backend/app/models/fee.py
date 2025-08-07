from sqlalchemy import Column, String, ForeignKey, Float, Date, Enum, DateTime, Text
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum

class FeeType(str, enum.Enum):
    TUITION = "tuition"
    LIBRARY = "library"
    LAB = "lab"
    EXAM = "exam"
    HOSTEL = "hostel"
    TRANSPORT = "transport"
    OTHER = "other"

class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"

class Fee(BaseModel):
    __tablename__ = "fees"
    
    student_id = Column(String, ForeignKey("students.id"), nullable=False)
    fee_type = Column(Enum(FeeType), nullable=False)
    amount = Column(Float, nullable=False)
    due_date = Column(Date, nullable=False)
    paid_date = Column(Date, nullable=True)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    
    # Payment details
    payment_method = Column(String, nullable=True)  # card, bank_transfer, cash
    transaction_id = Column(String, nullable=True)
    stripe_payment_intent_id = Column(String, nullable=True)
    
    # Additional info
    description = Column(Text, nullable=True)
    late_fee = Column(Float, default=0.0)
    discount = Column(Float, default=0.0)
    
    # Relationships
    student = relationship("Student", back_populates="fees")