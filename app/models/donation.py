from sqlmodel import Field, SQLModel, Relationship
from typing import Optional
from datetime import datetime


class Donation(SQLModel, table=True):
    __tablename__ = "donations"

    donation_id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.user_id")
    ngo_id: int = Field(foreign_key="ngos.ngo_id")
    transaction_id: str = Field(unique=True, index=True)
    amount: float
    status: str
    type: str
    date_time: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: "User" = Relationship(back_populates="donations")
    ngo: "NGO" = Relationship(back_populates="donations")
    pickups: list["Pickup"] = Relationship(back_populates="donation")
