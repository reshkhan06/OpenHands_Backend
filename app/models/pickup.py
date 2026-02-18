from sqlmodel import Field, SQLModel, Relationship
from typing import Optional
from datetime import datetime


class Pickup(SQLModel, table=True):
    __tablename__ = "pickups"

    pickup_id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.user_id")
    ngo_id: int = Field(foreign_key="ngos.ngo_id")
    donation_id: int = Field(foreign_key="donations.donation_id")
    address: str
    status: str
    pickup_date: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: "User" = Relationship(back_populates="pickups")
    ngo: "NGO" = Relationship(back_populates="pickups")
    donation: "Donation" = Relationship(back_populates="pickups")
