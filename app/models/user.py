from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, List
from datetime import datetime
from app.schemas.user_sch import UserRole, UserGender


class User(SQLModel, table=True):
    __tablename__ = "users"

    user_id: Optional[int] = Field(default=None, primary_key=True)
    fname: str
    lname: str
    name: str
    contact_number: str
    email: str = Field(unique=True, index=True)
    password: str
    is_verified: bool = Field(default=False)
    verification_token: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    location: str
    gender: UserGender = Field(default=UserGender.MALE)
    role: UserRole = Field(default=UserRole.DONOR)
