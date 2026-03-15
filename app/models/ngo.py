from sqlmodel import Field, SQLModel
from typing import Optional
from datetime import datetime
from app.schemas.ngo_sch import NGOType


class NGO(SQLModel, table=True):
    __tablename__ = "ngos"

    ngo_id: Optional[int] = Field(default=None, primary_key=True)
    ngo_name: str
    registration_number: str
    ngo_type: NGOType
    email: str = Field(unique=True, index=True)
    website_url: Optional[str] = None
    address: str
    city: str
    state: str
    pincode: str
    mission_statement: str
    bank_name: str
    account_number: str
    ifsc_code: str
    password: str
    is_verified: bool = Field(default=False)
    verification_token: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
