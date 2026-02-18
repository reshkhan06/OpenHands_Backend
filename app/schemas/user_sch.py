from pydantic import BaseModel, EmailStr
from typing import Optional


class UserBase(BaseModel):
    name: str
    contact_number: str
    email: EmailStr


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    name: Optional[str] = None
    contact_number: Optional[str] = None
    email: Optional[EmailStr] = None


class User(UserBase):
    user_id: int

    class Config:
        from_attributes = True
