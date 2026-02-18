from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DonationBase(BaseModel):
    user_id: int
    ngo_id: int
    transaction_id: str
    amount: float
    status: str
    type: str


class DonationCreate(DonationBase):
    pass


class DonationUpdate(BaseModel):
    amount: Optional[float] = None
    status: Optional[str] = None
    type: Optional[str] = None
    ngo_id: Optional[int] = None


class Donation(DonationBase):
    donation_id: int
    date_time: datetime

    class Config:
        from_attributes = True
