from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Feedback(SQLModel, table=True):
    __tablename__ = "feedback"

    feedback_id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str
    category: str
    message: str
    rating: int = 5
    follow_up: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

