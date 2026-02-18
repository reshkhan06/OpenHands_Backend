from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PaymentBase(BaseModel):
    user_id: int
    payment_type: str
    status: str


class PaymentCreate(PaymentBase):
    pass


class PaymentUpdate(BaseModel):
    payment_type: Optional[str] = None
    status: Optional[str] = None


class Payment(PaymentBase):
    payment_id: int
    date_time: datetime

    class Config:
        from_attributes = True
