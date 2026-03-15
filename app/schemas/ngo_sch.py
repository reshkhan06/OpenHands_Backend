from pydantic import BaseModel, EmailStr, HttpUrl, field_validator
from typing import Optional
from enum import Enum


# ---------------- ENUM ---------------- #


class NGOType(str, Enum):
    TRUST = "trust"
    SOCIETY = "society"
    SECTION8 = "section8"


# ---------------- BASE MODEL ---------------- #


class NGOBase(BaseModel):
    ngo_name: str
    registration_number: str
    ngo_type: NGOType
    email: EmailStr
    website_url: Optional[HttpUrl] = None
    address: str
    city: str
    state: str
    pincode: str
    mission_statement: str
    bank_name: str
    account_number: str
    ifsc_code: str

    @field_validator("ngo_name")
    @classmethod
    def validate_ngo_name(cls, v):
        if not v.strip():
            raise ValueError("NGO name cannot be empty")
        if len(v.strip()) < 3 or len(v.strip()) > 100:
            raise ValueError("NGO name must be between 3 and 100 characters")
        return v.strip()

    @field_validator("registration_number")
    @classmethod
    def validate_registration_number(cls, v):
        if not v.strip():
            raise ValueError("Registration number cannot be empty")
        return v.strip()

    @field_validator("pincode")
    @classmethod
    def validate_pincode(cls, v):
        if not v.isdigit():
            raise ValueError("Pincode must contain only digits")
        if len(v) != 6:
            raise ValueError("Pincode must be exactly 6 digits")
        return v

    @field_validator("address")
    @classmethod
    def validate_address(cls, v):
        v = (v or "").strip()
        if not v:
            raise ValueError("Address cannot be empty")
        if len(v) < 5 or len(v) > 300:
            raise ValueError("Address must be between 5 and 300 characters")
        if not any(c.isalpha() for c in v):
            raise ValueError("Address must contain at least one letter")
        return v

    @field_validator("ifsc_code")
    @classmethod
    def validate_ifsc(cls, v):
        if len(v) != 11:
            raise ValueError("IFSC code must be 11 characters")
        return v.upper()

    @field_validator("mission_statement")
    @classmethod
    def validate_mission(cls, v):
        if not v.strip():
            raise ValueError("Mission statement cannot be empty")
        if len(v.strip()) < 10:
            raise ValueError("Mission statement must be at least 10 characters")
        return v.strip()


# ---------------- CREATE MODEL ---------------- #


class NGOCreate(NGOBase):
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


# ---------------- UPDATE MODEL ---------------- #


class NGOUpdate(BaseModel):
    ngo_name: Optional[str] = None
    email: Optional[EmailStr] = None
    website_url: Optional[HttpUrl] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    mission_statement: Optional[str] = None


# ---------------- RESPONSE MODEL ---------------- #


class NGO(NGOBase):
    ngo_id: int
    is_verified: bool = False

    class Config:
        from_attributes = True


class NGOMeResponse(NGOBase):
    """Current NGO profile for /ngo/me (no password)."""
    ngo_id: int
    is_verified: bool = False
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


# ---------------- LOGIN MODELS ---------------- #


class NGOLoginRequest(BaseModel):
    email: EmailStr
    password: str


class NGOLoginResponse(BaseModel):
    message: str
    access_token: str
