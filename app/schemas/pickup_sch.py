from enum import Enum
from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime


class PickupStatus(str, Enum):
    REQUESTED = "requested"
    ACCEPTED = "accepted"
    ON_THE_WAY = "on_the_way"
    PICKED_UP = "picked_up"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# Allowed transitions: from -> list of valid next statuses
ALLOWED_TRANSITIONS = {
    PickupStatus.REQUESTED: [PickupStatus.ACCEPTED, PickupStatus.CANCELLED],
    PickupStatus.ACCEPTED: [PickupStatus.ON_THE_WAY, PickupStatus.CANCELLED],
    PickupStatus.ON_THE_WAY: [PickupStatus.PICKED_UP],
    PickupStatus.PICKED_UP: [PickupStatus.COMPLETED],
    PickupStatus.COMPLETED: [],
    PickupStatus.CANCELLED: [],
}


class PickupCreate(BaseModel):
    ngo_id: int
    pickup_address: str
    scheduled_time: Optional[datetime] = None
    items_description: Optional[str] = None

    @field_validator("pickup_address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        v = (v or "").strip()
        if len(v) < 5:
            raise ValueError("Pickup address must be at least 5 characters")
        if len(v) > 500:
            raise ValueError("Pickup address must be at most 500 characters")
        if not any(c.isalpha() for c in v):
            raise ValueError("Address must contain at least one letter")
        return v


class StatusHistoryEntry(BaseModel):
    status: PickupStatus
    changed_at: datetime
    changed_by_user_id: Optional[int] = None
    changed_by_ngo_id: Optional[int] = None
    note: Optional[str] = None

    class Config:
        from_attributes = True


class PickupResponse(BaseModel):
    pickup_id: int
    donor_id: int
    ngo_id: int
    pickup_address: str
    scheduled_time: Optional[datetime] = None
    items_description: Optional[str] = None
    pickup_image_path: Optional[str] = None
    current_status: PickupStatus
    payment_status: str  # pending, paid, refunded
    status_history: List[StatusHistoryEntry] = []
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PickupListEntry(BaseModel):
    pickup_id: int
    donor_id: int
    ngo_id: int
    pickup_address: str
    pickup_image_path: Optional[str] = None
    current_status: PickupStatus
    payment_status: str
    created_at: datetime

    class Config:
        from_attributes = True


class PickupStatusUpdate(BaseModel):
    status: PickupStatus
    note: Optional[str] = None
