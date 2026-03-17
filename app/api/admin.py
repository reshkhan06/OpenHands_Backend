from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlmodel import Session, select
from pydantic import BaseModel

from app.db.connection import get_session
from app.models.user import User
from app.models.ngo import NGO
from app.models.pickup import Pickup, StatusHistoryEntry
from app.models.payment import Payment
from app.models.admin_config import AdminConfig
from app.models.feedback import Feedback
from app.schemas.user_sch import UserRole
from app.dependencies.auth import get_current_user, require_roles
from app.services.pickup_service import pickup_to_response
from app.services.send_email import send_ngo_approval_result

router = APIRouter(prefix="/admin", tags=["Admin"])

AdminUser = Depends(require_roles(UserRole.ADMIN))


class UserUpdateAdmin(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UserDetailResponse(BaseModel):
    user_id: int
    fname: str
    lname: str
    email: str
    contact_number: int
    location: str
    role: str
    is_verified: bool
    is_active: bool
    created_at: Optional[str] = None


@router.get("/users")
def admin_list_users(
    session: Session = Depends(get_session),
    current_user: User = AdminUser,
    role: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
):
    # Donor management page: only list donors (hide admin accounts)
    statement = select(User).where(User.role == UserRole.DONOR)
    if is_active is not None:
        statement = statement.where(User.is_active == is_active)
    if search:
        term = f"%{search}%"
        statement = statement.where(
            (User.email.ilike(term)) | (User.fname.ilike(term)) | (User.lname.ilike(term))
        )
    statement = statement.order_by(User.created_at.desc())
    users = session.exec(statement).all()
    return [
        {
            "user_id": u.user_id,
            "fname": u.fname,
            "lname": u.lname,
            "email": u.email,
            "contact_number": u.contact_number,
            "location": u.location,
            "role": u.role.value if hasattr(u.role, "value") else u.role,
            "is_verified": u.is_verified,
            "is_active": getattr(u, "is_active", True),
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


@router.get("/users/{user_id}", response_model=UserDetailResponse)
def admin_get_user_detail(
    user_id: int,
    session: Session = Depends(get_session),
    current_user: User = AdminUser,
):
    user = session.exec(select(User).where(User.user_id == user_id)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserDetailResponse(
        user_id=user.user_id,
        fname=user.fname,
        lname=user.lname,
        email=user.email,
        contact_number=user.contact_number,
        location=user.location,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        is_verified=user.is_verified,
        is_active=getattr(user, "is_active", True),
        created_at=user.created_at.isoformat() if user.created_at else None,
    )


@router.patch("/users/{user_id}")
def admin_update_user(
    user_id: int,
    body: UserUpdateAdmin,
    session: Session = Depends(get_session),
    current_user: User = AdminUser,
):
    statement = select(User).where(User.user_id == user_id)
    user = session.exec(statement).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if body.role is not None:
        try:
            user.role = UserRole(body.role.lower())
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")
    if body.is_active is not None:
        user.is_active = body.is_active
    session.add(user)
    session.commit()
    session.refresh(user)
    return {"user_id": user.user_id, "role": user.role.value, "is_active": getattr(user, "is_active", True)}


# ---------- NGOs ----------
class NGOUpdateAdmin(BaseModel):
    is_verified: Optional[bool] = None


class NGODetailResponse(BaseModel):
    ngo_id: int
    ngo_name: str
    registration_number: str
    ngo_type: str
    email: str
    website_url: Optional[str] = None
    address: str
    city: str
    state: str
    pincode: str
    mission_statement: str
    bank_name: str
    account_number: str
    ifsc_code: str
    is_verified: bool
    certificate_path: Optional[str] = None
    created_at: Optional[str] = None


@router.get("/ngos")
def admin_list_ngos(
    session: Session = Depends(get_session),
    current_user: User = AdminUser,
    is_verified: Optional[bool] = Query(None),
):
    statement = select(NGO)
    if is_verified is not None:
        statement = statement.where(NGO.is_verified == is_verified)
    statement = statement.order_by(NGO.created_at.desc())
    ngos = session.exec(statement).all()
    return [
        {
            "ngo_id": n.ngo_id,
            "ngo_name": n.ngo_name,
            "email": n.email,
            "city": n.city,
            "state": n.state,
            "is_verified": n.is_verified,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in ngos
    ]


@router.get("/ngos/{ngo_id}", response_model=NGODetailResponse)
def admin_get_ngo_detail(
    ngo_id: int,
    session: Session = Depends(get_session),
    current_user: User = AdminUser,
):
    ngo = session.exec(select(NGO).where(NGO.ngo_id == ngo_id)).first()
    if not ngo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NGO not found")
    return NGODetailResponse(
        ngo_id=ngo.ngo_id,
        ngo_name=ngo.ngo_name,
        registration_number=ngo.registration_number,
        ngo_type=str(ngo.ngo_type),
        email=ngo.email,
        website_url=ngo.website_url,
        address=ngo.address,
        city=ngo.city,
        state=ngo.state,
        pincode=ngo.pincode,
        mission_statement=ngo.mission_statement,
        bank_name=ngo.bank_name,
        account_number=ngo.account_number,
        ifsc_code=ngo.ifsc_code,
        is_verified=ngo.is_verified,
        certificate_path=getattr(ngo, "certificate_path", None),
        created_at=ngo.created_at.isoformat() if ngo.created_at else None,
    )


@router.patch("/ngos/{ngo_id}")
async def admin_update_ngo(
    ngo_id: int,
    body: NGOUpdateAdmin,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user: User = AdminUser,
):
    statement = select(NGO).where(NGO.ngo_id == ngo_id)
    ngo = session.exec(statement).first()
    if not ngo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NGO not found")
    if body.is_verified is not None:
        ngo.is_verified = body.is_verified
    session.add(ngo)
    session.commit()
    session.refresh(ngo)
    # Send email to NGO about approval or rejection
    if body.is_verified is not None:
        background_tasks.add_task(
            send_ngo_approval_result,
            ngo_email=ngo.email,
            ngo_name=ngo.ngo_name,
            approved=body.is_verified,
        )
    return {"ngo_id": ngo.ngo_id, "is_verified": ngo.is_verified}


@router.delete("/ngos/{ngo_id}")
def admin_delete_ngo(
    ngo_id: int,
    session: Session = Depends(get_session),
    current_user: User = AdminUser,
):
    """Delete an NGO and all related pickups, payments, and status history."""
    ngo = session.exec(select(NGO).where(NGO.ngo_id == ngo_id)).first()
    if not ngo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NGO not found")
    pickups = session.exec(select(Pickup).where(Pickup.ngo_id == ngo_id)).all()
    pickup_ids = [p.pickup_id for p in pickups]
    for pid in pickup_ids:
        for pay in session.exec(select(Payment).where(Payment.pickup_id == pid)).all():
            session.delete(pay)
        for hist in session.exec(select(StatusHistoryEntry).where(StatusHistoryEntry.pickup_id == pid)).all():
            session.delete(hist)
    for p in pickups:
        session.delete(p)
    session.delete(ngo)
    session.commit()
    return {"message": "NGO deleted successfully", "ngo_id": ngo_id}


# ---------- Pickups ----------
@router.get("/pickups")
def admin_list_pickups(
    session: Session = Depends(get_session),
    current_user: User = AdminUser,
    status_filter: Optional[str] = Query(None, alias="status"),
):
    statement = select(Pickup)
    if status_filter:
        statement = statement.where(Pickup.current_status == status_filter)
    statement = statement.order_by(Pickup.created_at.desc())
    pickups = session.exec(statement).all()
    return [
        {
            "pickup_id": p.pickup_id,
            "donor_id": p.donor_id,
            "ngo_id": p.ngo_id,
            "pickup_address": p.pickup_address,
            "current_status": p.current_status,
            "payment_status": p.payment_status,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in pickups
    ]


@router.get("/pickups/{pickup_id}")
def admin_get_pickup(
    pickup_id: int,
    session: Session = Depends(get_session),
    current_user: User = AdminUser,
):
    statement = select(Pickup).where(Pickup.pickup_id == pickup_id)
    pickup = session.exec(statement).first()
    if not pickup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pickup not found")
    return pickup_to_response(session, pickup)


# ---------- Config ----------
class ConfigResponse(BaseModel):
    deposit_amount_paise: int


class ConfigUpdate(BaseModel):
    deposit_amount_paise: Optional[int] = None


@router.get("/config")
def admin_get_config(
    session: Session = Depends(get_session),
    current_user: User = AdminUser,
):
    statement = select(AdminConfig).where(AdminConfig.key == "deposit_amount_paise")
    row = session.exec(statement).first()
    value = int(row.value) if row and row.value.isdigit() else 10000
    return {"deposit_amount_paise": value}


@router.put("/config")
def admin_update_config(
    body: ConfigUpdate,
    session: Session = Depends(get_session),
    current_user: User = AdminUser,
):
    if body.deposit_amount_paise is not None:
        if body.deposit_amount_paise < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="deposit_amount_paise must be >= 0")
        statement = select(AdminConfig).where(AdminConfig.key == "deposit_amount_paise")
        row = session.exec(statement).first()
        if row:
            row.value = str(body.deposit_amount_paise)
            session.add(row)
        else:
            session.add(AdminConfig(key="deposit_amount_paise", value=str(body.deposit_amount_paise)))
        session.commit()
    statement = select(AdminConfig).where(AdminConfig.key == "deposit_amount_paise")
    row = session.exec(statement).first()
    value = int(row.value) if row and row.value.isdigit() else 10000
    return {"deposit_amount_paise": value}


# ---------- Dashboard stats ----------
@router.get("/dashboard")
def admin_dashboard(
    session: Session = Depends(get_session),
    current_user: User = AdminUser,
):
    # "users_total" in UI refers to donors (hide admins from donor metrics)
    users_count = session.exec(select(User).where(User.role == UserRole.DONOR)).all()
    users_total = len(users_count)
    ngos_count = session.exec(select(NGO)).all()
    ngos_total = len(ngos_count)
    ngos_pending = len([n for n in ngos_count if not n.is_verified])
    pickups_count = session.exec(select(Pickup)).all()
    pickups_total = len(pickups_count)
    pickups_requested = len([p for p in pickups_count if p.current_status == "requested"])
    payments_paid = session.exec(select(Payment).where(Payment.status == "paid")).all()
    deposits_active = len(payments_paid)
    return {
        "users_total": users_total,
        "ngos_total": ngos_total,
        "ngos_pending": ngos_pending,
        "pickups_total": pickups_total,
        "pickups_requested": pickups_requested,
        "deposits_active": deposits_active,
    }


# ---------- Feedback ----------
@router.get("/feedbacks")
def admin_list_feedbacks(
    session: Session = Depends(get_session),
    current_user: User = AdminUser,
    limit: int = Query(100, ge=1, le=500),
):
    statement = select(Feedback).order_by(Feedback.created_at.desc()).limit(limit)
    rows = session.exec(statement).all()
    return [
        {
            "feedback_id": f.feedback_id,
            "name": f.name,
            "email": f.email,
            "category": f.category,
            "rating": f.rating,
            "follow_up": f.follow_up,
            "message": f.message,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        }
        for f in rows
    ]
