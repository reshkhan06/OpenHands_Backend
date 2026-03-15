from sqlmodel import Field, SQLModel
from typing import Optional


class AdminConfig(SQLModel, table=True):
    __tablename__ = "admin_config"

    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(unique=True, index=True)
    value: str = Field(description="JSON or string value")
