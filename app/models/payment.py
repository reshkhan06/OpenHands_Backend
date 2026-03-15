from sqlmodel import Field, SQLModel
from typing import Optional
from datetime import datetime


class Payment(SQLModel, table=True):
    __tablename__ = "payments"

    payment_id: Optional[int] = Field(default=None, primary_key=True)
    pickup_id: int = Field(foreign_key="pickups.pickup_id")
    razorpay_order_id: str = Field(unique=True, index=True)
    razorpay_payment_id: Optional[str] = Field(default=None, index=True)
    razorpay_refund_id: Optional[str] = None
    amount: int = Field(description="Amount in paise")
    currency: str = Field(default="INR")
    status: str = Field(default="pending")  # pending, paid, refunded, refund_pending, failed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    paid_at: Optional[datetime] = None
    refunded_at: Optional[datetime] = None
