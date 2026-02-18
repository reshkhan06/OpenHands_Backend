from pydantic import BaseModel
from typing import Optional


class AdminBase(BaseModel):
    name: str


class AdminCreate(AdminBase):
    pass


class AdminUpdate(BaseModel):
    name: Optional[str] = None


class Admin(AdminBase):
    admin_id: int

    class Config:
        from_attributes = True
