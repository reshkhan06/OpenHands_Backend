from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, List


class NGO(SQLModel, table=True):
    __tablename__ = "ngos"

    ngo_id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    address: str
    registration_no: str = Field(unique=True, index=True)
    contact_number: str
    status: str

    # Relationships
    donations: List["Donation"] = Relationship(back_populates="ngo")
    pickups: List["Pickup"] = Relationship(back_populates="ngo")
