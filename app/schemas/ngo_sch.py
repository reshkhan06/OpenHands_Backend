from pydantic import BaseModel
from typing import Optional


class NGOBase(BaseModel):
    name: str
    address: str
    registration_no: str
    contact_number: str
    status: str


class NGOCreate(NGOBase):
    pass


class NGOUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    registration_no: Optional[str] = None
    contact_number: Optional[str] = None
    status: Optional[str] = None


class NGO(NGOBase):
    ngo_id: int

    class Config:
        from_attributes = True
