"""Unified email verification for both User (donor) and NGO."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.db.connection import get_session
from app.models.user import User
from app.models.ngo import NGO as NGOModel
from app.services.authentication import verify_token

router = APIRouter()


@router.get("/verify")
async def verify_email_token(token: str, session: Session = Depends(get_session)):
    """
    Verify email using token. Supports both donor (user) and NGO tokens.
    Link in email: {FRONTEND_URL}/verify?token=...
    """
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    token_type = payload.get("type")

    if token_type == "ngo_verification" and "ngo_id" in payload:
        ngo_id = payload["ngo_id"]
        statement = select(NGOModel).where(NGOModel.ngo_id == ngo_id)
        ngo = session.exec(statement).first()
        if not ngo:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NGO not found")
        if ngo.is_verified:
            return {"message": "NGO email already verified. You can log in."}
        ngo.is_verified = True
        ngo.verification_token = None
        session.add(ngo)
        session.commit()
        return {"message": "NGO email verified successfully. You can now log in."}

    if token_type == "verification" and "user_id" in payload:
        user_id = payload["user_id"]
        statement = select(User).where(User.user_id == user_id)
        user = session.exec(statement).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if user.is_verified:
            return {"message": "Email already verified"}
        user.is_verified = True
        user.verification_token = None
        session.add(user)
        session.commit()
        return {"message": "Email verified successfully. You can now login."}

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid token format",
    )
