from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from enum import Enum


class UserRole(str, Enum):
    USER = "user"
    DONOR = "donor"
    NGO_REPRESENTATIVE = "ngo_representative"
    ADMIN = "admin"


class UserGender(str, Enum):
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"


class UserSignUp(BaseModel):
    fname: str
    lname: str
    email: EmailStr
    contact_number: int
    password: str
    location: str
    gender: str
    role: str

    @field_validator("fname")
    @classmethod
    def validate_fname(cls, v):
        if not v or not v.strip():
            raise ValueError("First name cannot be empty")
        if len(v.strip()) < 2 or len(v.strip()) > 50:
            raise ValueError("First name must be between 2 and 50 characters")
        return v.strip()

    @field_validator("lname")
    @classmethod
    def validate_lname(cls, v):
        if not v or not v.strip():
            raise ValueError("Last name cannot be empty")
        if len(v.strip()) < 2 or len(v.strip()) > 50:
            raise ValueError("Last name must be between 2 and 50 characters")
        return v.strip()

    # 10 Digit Contact Number Validation
    @field_validator("contact_number")
    @classmethod
    def validate_contact_number(cls, v):
        if not v.isdigit():
            raise ValueError("Contact number must contain only digits")
        if len(v) != 10:
            raise ValueError("Contact number must be exactly 10 digits")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if not v or len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v

    @field_validator("location")
    @classmethod
    def validate_location(cls, v):
        v = (v or "").strip()
        if not v:
            raise ValueError("Location cannot be empty")
        if len(v) < 3 or len(v) > 100:
            raise ValueError("Location must be between 3 and 100 characters")
        if not any(c.isalpha() for c in v):
            raise ValueError("Location must contain at least one letter")
        return v

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v):
        valid_genders = ["male", "female", "other"]
        if v.lower() not in valid_genders:
            raise ValueError(f"Gender must be one of: {valid_genders}")
        return v.lower()

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        # Only donor (and admin for superuser) - donor donates items; NGO is separate entity
        valid_roles = ["donor", "admin"]
        if v.lower() not in valid_roles:
            raise ValueError(f"Role must be one of: {valid_roles}")
        return v.lower()


class UserBase(BaseModel):
    name: str
    contact_number: int
    email: EmailStr
    location: str
    gender: UserGender
    role: UserRole

    # 10 Digit Contact Number Validation
    @field_validator("contact_number")
    @classmethod
    def validate_contact_number(cls, v):
        if not v.isdigit():
            raise ValueError("Contact number must contain only digits")
        if len(v) != 10:
            raise ValueError("Contact number must be exactly 10 digits")
        return v

    @field_validator("location")
    @classmethod
    def validate_location(cls, v):
        v = (v or "").strip()
        if not v:
            raise ValueError("Location cannot be empty")
        if len(v) < 1 or len(v) > 100:
            raise ValueError("Location must be between 1 and 100 characters")
        if not any(c.isalpha() for c in v):
            raise ValueError("Location must contain at least one letter")
        return v


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    name: Optional[str] = None
    contact_number: Optional[int] = None
    email: Optional[EmailStr] = None


class User(UserBase):
    user_id: int

    class Config:
        from_attributes = True
