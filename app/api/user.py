from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlmodel import Session, select
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, Union
from datetime import timedelta
import re

from app.models.user import User
from app.db.connection import get_session
from app.services.authentication import (
    hash_password,
    verify_password,
    create_access_token,
    create_verification_token,
    verify_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from app.services.send_email import send_verification_email
from app.schemas.user_sch import UserRole, UserGender, UserSignUp
from app.dependencies.auth import get_current_user

router = APIRouter()


# Request/Response Schemas
class UserSignUp(BaseModel):
    fname: str
    lname: str
    email: EmailStr
    contact_number: Union[int, str]
    password: str
    location: str
    gender: str
    role: str
    dob: Optional[str] = None

    @field_validator("fname")
    @classmethod
    def validate_fname(cls, v):
        v = (v or "").strip()
        if not v:
            raise ValueError("First name cannot be empty")
        if len(v) < 2 or len(v) > 50:
            raise ValueError("First name must be between 2 and 50 characters")
        if not re.fullmatch(r"[A-Za-z\s]+", v):
            raise ValueError("First name must contain only letters and spaces")
        return v

    @field_validator("lname")
    @classmethod
    def validate_lname(cls, v):
        v = (v or "").strip()
        if not v:
            raise ValueError("Last name cannot be empty")
        if len(v) < 2 or len(v) > 50:
            raise ValueError("Last name must be between 2 and 50 characters")
        if not re.fullmatch(r"[A-Za-z\s]+", v):
            raise ValueError("Last name must contain only letters and spaces")
        return v

    @field_validator("contact_number", mode="before")
    @classmethod
    def coerce_contact_number(cls, v):
        if v is None:
            raise ValueError("Contact number is required")
        s = str(v).strip()
        if not s.isdigit():
            raise ValueError("Contact number must contain only digits")
        if len(s) != 10:
            raise ValueError("Contact number must be exactly 10 digits")
        return int(s)

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        valid_roles = ["donor", "admin"]
        if v.lower() not in valid_roles:
            raise ValueError(f"Role must be one of: {valid_roles}")
        return v.lower()


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v):
        if not v or len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserResponse(BaseModel):
    user_id: int
    fname: str
    lname: str
    email: str
    contact_number: int
    location: str
    gender: str
    role: str
    is_verified: bool

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class UserProfileResponse(BaseModel):
    user_id: int
    fname: str
    lname: str
    email: str
    contact_number: int
    location: str
    gender: str
    role: str
    is_verified: bool
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return UserProfileResponse(
        user_id=current_user.user_id,
        fname=current_user.fname,
        lname=current_user.lname,
        email=current_user.email,
        contact_number=current_user.contact_number,
        location=current_user.location,
        gender=current_user.gender.value if hasattr(current_user.gender, "value") else str(current_user.gender),
        role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        is_verified=current_user.is_verified,
        created_at=current_user.created_at.isoformat() if getattr(current_user, "created_at", None) else None,
    )


@router.post("/signup", response_model=dict)
async def signup(
    user_data: UserSignUp,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    """Register a new user and send verification email"""
    try:
        # Check if user already exists
        statement = select(User).where(User.email == user_data.email)
        existing_user = session.exec(statement).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # Hash password
        hashed_password = hash_password(user_data.password)

        # Create full name from fname and lname
        full_name = f"{user_data.fname} {user_data.lname}"

        # Create new user first to get user_id
        new_user = User(
            fname=user_data.fname,
            lname=user_data.lname,
            email=user_data.email,
            contact_number=user_data.contact_number,
            password=hashed_password,
            location=user_data.location,
            gender=UserGender(user_data.gender.capitalize()),
            role=UserRole(user_data.role.lower()),
            is_verified=False,
        )

        session.add(new_user)
        session.commit()
        session.refresh(new_user)

        # Create verification token with user_id
        verification_token = create_verification_token(new_user.user_id)

        # Update user with verification token
        new_user.verification_token = verification_token
        session.add(new_user)
        session.commit()

        # Send verification email in background (won't block if email fails)
        background_tasks.add_task(
            send_verification_email,
            email=user_data.email,
            name=full_name,
            token=verification_token,
        )

        return {
            "message": "User registered successfully. Verification email sent.",
            "user_id": new_user.user_id,
            "email": new_user.email,
        }

    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    session: Session = Depends(get_session),
):
    """Login user with email and password"""

    # Find user by email
    statement = select(User).where(User.email == credentials.email)
    user = session.exec(statement).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Verify password
    if not verify_password(credentials.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Check if email is verified
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in. Check your inbox for the verification link.",
        )

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.user_id},
        expires_delta=access_token_expires,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.from_orm(user),
    }


@router.get("/verify")
async def verify_email(token: str, session: Session = Depends(get_session)):
    """Verify user email using token"""

    # Decode token
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token format",
        )

    # Find user by user_id and verify
    statement = select(User).where(User.user_id == user_id)
    user = session.exec(statement).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.is_verified:
        return {"message": "Email already verified"}

    # Mark user as verified
    user.is_verified = True
    user.verification_token = None
    session.add(user)
    session.commit()

    return {"message": "Email verified successfully. You can now login."}


@router.post("/change-password", response_model=dict)
async def change_password(
    body: ChangePasswordRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Change password for the authenticated user. Requires current password."""
    statement = select(User).where(User.user_id == current_user.user_id)
    user = session.exec(statement).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not verify_password(body.current_password, user.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    user.password = hash_password(body.new_password)
    session.add(user)
    session.commit()
    return {"message": "Password updated successfully"}


# Delete User by Email
@router.delete("/delete", response_model=dict)
async def delete_user(
    email: EmailStr,
    session: Session = Depends(get_session),
):
    """Delete user by email"""

    # Check if user exists
    statement = select(User).where(User.email == email)
    user = session.exec(statement).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Delete user
    session.delete(user)
    session.commit()

    return {
        "message": f"User {user.fname} {user.lname} deleted successfully",
        "email": user.email,
    }
