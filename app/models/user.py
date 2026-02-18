from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, List
from datetime import datetime


class User(SQLModel, table=True):
    __tablename__ = "users"

    user_id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    contact_number: str
    email: str = Field(unique=True, index=True)
    password: str
    is_verified: bool = Field(default=False)
    verification_token: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    donations: List["Donation"] = Relationship(back_populates="user")
    pickups: List["Pickup"] = Relationship(back_populates="user")
    payments: List["Payment"] = Relationship(back_populates="user")
