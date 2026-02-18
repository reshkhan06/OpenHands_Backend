from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PickupBase(BaseModel):
    user_id: int
    ngo_id: int
    donation_id: int
    address: str
    status: str


class PickupCreate(PickupBase):
    pass


class PickupUpdate(BaseModel):
    address: Optional[str] = None
    status: Optional[str] = None
    ngo_id: Optional[int] = None


class Pickup(PickupBase):
    pickup_id: int
    pickup_date: datetime

    class Config:
        from_attributes = True
