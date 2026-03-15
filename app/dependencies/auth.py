from typing import List, Optional, Callable, Tuple, Union

from fastapi import Depends, HTTPException, status, Header
from sqlmodel import Session, select

from app.db.connection import get_session
from app.models.user import User
from app.models.ngo import NGO
from app.schemas.user_sch import UserRole
from app.services.authentication import verify_token


def _extract_token(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
        )

    try:
        scheme, token = authorization.split(" ")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )

    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization scheme",
        )

    return token


def get_current_user(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    session: Session = Depends(get_session),
) -> User:
    """
    Resolve the currently authenticated user from the Bearer token.
    Only tokens created for users (with `user_id`) are supported here.
    """
    token = _extract_token(authorization)
    payload = verify_token(token)

    if not payload or "user_id" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id = payload["user_id"]
    statement = select(User).where(User.user_id == user_id)
    user = session.exec(statement).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User email not verified",
        )
    if not getattr(user, "is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is blocked",
        )

    return user


def require_roles(*roles: UserRole) -> Callable[[User], User]:
    """
    Dependency factory that ensures the current authenticated user
    has one of the required roles.
    """

    required_roles: List[UserRole] = list(roles)

    def _dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return _dependency


def get_current_ngo(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    session: Session = Depends(get_session),
) -> NGO:
    """
    Resolve the currently authenticated NGO from the Bearer token.
    Only tokens created for NGOs (with `ngo_id`) are supported here.
    """
    token = _extract_token(authorization)
    payload = verify_token(token)

    if not payload or "ngo_id" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    ngo_id = payload["ngo_id"]
    statement = select(NGO).where(NGO.ngo_id == ngo_id)
    ngo = session.exec(statement).first()

    if not ngo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="NGO not found",
        )

    if not ngo.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="NGO not verified",
        )

    return ngo


def get_current_user_or_ngo(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    session: Session = Depends(get_session),
) -> Tuple[Optional[User], Optional[NGO]]:
    """
    Resolve current identity as either a User or an NGO from the Bearer token.
    Returns (user, None) for user tokens, (None, ngo) for NGO tokens.
    """
    token = _extract_token(authorization)
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    if "user_id" in payload:
        user_id = payload["user_id"]
        statement = select(User).where(User.user_id == user_id)
        user = session.exec(statement).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        if not user.is_verified:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User email not verified")
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is blocked")
        return (user, None)
    if "ngo_id" in payload:
        ngo_id = payload["ngo_id"]
        statement = select(NGO).where(NGO.ngo_id == ngo_id)
        ngo = session.exec(statement).first()
        if not ngo:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="NGO not found")
        if not ngo.is_verified:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="NGO not verified")
        return (None, ngo)
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


def get_ngo_or_admin_user(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    session: Session = Depends(get_session),
) -> Tuple[Optional[User], Optional[NGO]]:
    """
    Require either NGO token or User with ADMIN role. Returns (user, ngo) with one set.
    """
    token = _extract_token(authorization)
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    if "ngo_id" in payload:
        ngo_id = payload["ngo_id"]
        statement = select(NGO).where(NGO.ngo_id == ngo_id)
        ngo = session.exec(statement).first()
        if not ngo:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="NGO not found")
        if not ngo.is_verified:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="NGO not verified")
        return (None, ngo)
    if "user_id" in payload:
        user_id = payload["user_id"]
        statement = select(User).where(User.user_id == user_id)
        user = session.exec(statement).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        if user.role != UserRole.ADMIN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only NGO or Admin can perform this action")
        if not getattr(user, "is_active", True):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is blocked")
        return (user, None)
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

