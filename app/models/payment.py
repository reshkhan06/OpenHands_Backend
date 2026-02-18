from sqlmodel import Field, SQLModel, Relationship
from typing import Optional
from datetime import datetime


class Payment(SQLModel, table=True):
    __tablename__ = "payments"

    payment_id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.user_id")
    payment_type: str
    status: str
    date_time: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: "User" = Relationship(back_populates="payments")
