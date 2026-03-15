from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PaymentStatus:
    PENDING = "pending"
    PAID = "paid"
    REFUNDED = "refunded"
    REFUND_PENDING = "refund_pending"
    FAILED = "failed"


class CreateOrderResponse(BaseModel):
    order_id: str
    amount: int  # in paise
    currency: str


class PaymentConfirmRequest(BaseModel):
    pickup_id: int
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class PaymentResponse(BaseModel):
    payment_id: int
    pickup_id: int
    razorpay_order_id: str
    razorpay_payment_id: Optional[str] = None
    amount: int
    currency: str
    status: str
    created_at: datetime
    paid_at: Optional[datetime] = None
    refunded_at: Optional[datetime] = None

    class Config:
        from_attributes = True
