from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from enum import Enum
import phonenumbers


class UserRole(str, Enum):
    DONOR = "donor"
    NGO_REPRESENTATIVE = "ngo_representative"


class UserGender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class UserSignUp(BaseModel):
    fname: str
    lname: str
    name: str
    email: EmailStr
    contact_number: str
    password: str
    location: str
    gender: str
    role: str

    @field_validator("fname")
    @classmethod
    def validate_fname(cls, v):
        if not v or not v.strip():
            raise ValueError("First name cannot be empty")
        if len(v) < 2 or len(v) > 50:
            raise ValueError("First name must be between 2 and 50 characters")
        return v.strip()

    @field_validator("lname")
    @classmethod
    def validate_lname(cls, v):
        if not v or not v.strip():
            raise ValueError("Last name cannot be empty")
        if len(v) < 2 or len(v) > 50:
            raise ValueError("Last name must be between 2 and 50 characters")
        return v.strip()

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Full name cannot be empty")
        if len(v) < 3 or len(v) > 100:
            raise ValueError("Full name must be between 3 and 100 characters")
        return v.strip()

    @field_validator("contact_number")
    @classmethod
    def validate_phone_number(cls, v):
        try:
            parsed = phonenumbers.parse(v, "IN")
            if not phonenumbers.is_valid_number(parsed):
                raise ValueError("Invalid phone number")
            return phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.E164
            )
        except Exception:
            raise ValueError(
                "Invalid phone number format. Use format: +91 9370036076 or 9370036076"
            )

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
        if not v or not v.strip():
            raise ValueError("Location cannot be empty")
        if len(v) < 3 or len(v) > 100:
            raise ValueError("Location must be between 3 and 100 characters")
        return v.strip()

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
        valid_roles = ["donor", "ngo_representative"]
        if v.lower() not in valid_roles:
            raise ValueError(f"Role must be one of: {valid_roles}")
        return v.lower()


class UserBase(BaseModel):
    name: str
    contact_number: str
    email: EmailStr
    location: str
    gender: UserGender
    role: UserRole

    @field_validator("contact_number")
    @classmethod
    def validate_phone_number(cls, v):
        try:
            parsed = phonenumbers.parse(
                v, "IN"
            )  # Assuming default country code as India
            if not phonenumbers.is_valid_number(parsed):
                raise ValueError("Invalid phone number")
            return phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.E164
            )
        except Exception:
            raise ValueError("Invalid phone number format")

    @field_validator("location")
    @classmethod
    def validate_location(cls, v):
        if not v.strip():
            raise ValueError("Location cannot be empty")
        if len(v) < 1 or len(v) > 100:
            raise ValueError("Location must be between 1 and 100 characters")
        return v.strip()


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
