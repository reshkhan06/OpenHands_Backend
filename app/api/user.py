from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlmodel import Session, select
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import timedelta

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

router = APIRouter()


# Request/Response Schemas
class UserSignUp(BaseModel):
    fname: str
    lname: str
    email: EmailStr
    contact_number: str
    password: str
    location: str
    gender: str
    role: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    user_id: int
    fname: str
    lname: str
    email: str
    contact_number: str
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


@router.post("/signup", response_model=dict)
async def signup(
    user_data: UserSignUp,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    """Register a new user and send verification email"""

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
        name=full_name,
        email=user_data.email,
        contact_number=user_data.contact_number,
        password=hashed_password,
        location=user_data.location,
        gender=UserGender(user_data.gender),
        role=UserRole(user_data.role),
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
            detail=f" {user.fname} Please verify your email before logging in",
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
