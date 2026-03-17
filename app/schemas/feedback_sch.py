from datetime import datetime
import re

from pydantic import BaseModel, EmailStr, field_validator


class FeedbackCreate(BaseModel):
    name: str
    email: EmailStr
    category: str
    message: str
    rating: int = 5
    follow_up: bool = True

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str):
        v = (v or "").strip()
        if not v:
            raise ValueError("Name cannot be empty")
        if len(v) < 2 or len(v) > 100:
            raise ValueError("Name must be between 2 and 100 characters")
        if not re.fullmatch(r"[A-Za-z\s]+", v):
            raise ValueError("Name must contain only letters and spaces")
        return v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str):
        v = (v or "").strip()
        if not v:
            raise ValueError("Category is required")
        if len(v) > 50:
            raise ValueError("Category is too long")
        return v

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str):
        v = (v or "").strip()
        if not v:
            raise ValueError("Message is required")
        if len(v) < 10:
            raise ValueError("Message must be at least 10 characters")
        if len(v) > 2000:
            raise ValueError("Message is too long")
        return v

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: int):
        if v < 1 or v > 5:
            raise ValueError("Rating must be between 1 and 5")
        return v


class FeedbackResponse(BaseModel):
    feedback_id: int
    message: str = "Feedback submitted successfully"
    created_at: datetime

