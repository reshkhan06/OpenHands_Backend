from sqlmodel import Field, SQLModel, Relationship, Column, JSON
from typing import Optional, List
from datetime import datetime
from app.schemas.pickup_sch import PickupStatus


class StatusHistoryEntry(SQLModel, table=True):
    __tablename__ = "pickup_status_history"

    id: Optional[int] = Field(default=None, primary_key=True)
    pickup_id: int = Field(foreign_key="pickups.pickup_id")
    status: str  # PickupStatus value
    changed_at: datetime = Field(default_factory=datetime.utcnow)
    changed_by_user_id: Optional[int] = Field(default=None, foreign_key="users.user_id")
    changed_by_ngo_id: Optional[int] = Field(default=None, foreign_key="ngos.ngo_id")
    note: Optional[str] = None


class Pickup(SQLModel, table=True):
    __tablename__ = "pickups"

    pickup_id: Optional[int] = Field(default=None, primary_key=True)
    donor_id: int = Field(foreign_key="users.user_id")
    ngo_id: int = Field(foreign_key="ngos.ngo_id")
    pickup_address: str
    scheduled_time: Optional[datetime] = None
    items_description: Optional[str] = None
    pickup_image_path: Optional[str] = Field(default=None)
    current_status: str = Field(default=PickupStatus.REQUESTED.value)
    payment_status: str = Field(default="pending")  # pending, paid, refunded, refund_pending
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
