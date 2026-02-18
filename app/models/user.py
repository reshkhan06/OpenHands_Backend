from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, List
from datetime import datetime


class User(SQLModel, table=True):
    __tablename__ = "users"

    user_id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    contact_number: str
    email: str = Field(unique=True, index=True)

    # Relationships
    donations: List["Donation"] = Relationship(back_populates="user")
    pickups: List["Pickup"] = Relationship(back_populates="user")
    payments: List["Payment"] = Relationship(back_populates="user")
