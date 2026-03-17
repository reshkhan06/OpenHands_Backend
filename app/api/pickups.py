from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks, UploadFile, File, Form
from sqlmodel import Session, select
import os
import uuid

from app.db.connection import get_session
from app.models.pickup import Pickup, StatusHistoryEntry
from app.models.payment import Payment
from app.models.ngo import NGO
from app.schemas.pickup_sch import (
    PickupCreate,
    PickupStatus,
    PickupStatusUpdate,
)
from app.dependencies.auth import (
    get_current_user,
    get_current_user_or_ngo,
    get_ngo_or_admin_user,
    require_roles,
)
from app.schemas.user_sch import UserRole
from app.services.pickup_service import (
    get_deposit_amount_paise,
    update_pickup_status,
    build_status_history,
    pickup_to_response,
)
from app.services.razorpay_service import create_order, get_razorpay_client, RAZORPAY_KEY_ID
from app.services.send_email import send_pickup_request_to_ngo, send_pickup_status_to_donor
from app.models.user import User

router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED)
def create_pickup(
    body: PickupCreate,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles(UserRole.DONOR, UserRole.ADMIN)),
):
    """Create a pickup request. Creates Razorpay order for deposit. Donor must complete payment separately."""
    statement = select(NGO).where(NGO.ngo_id == body.ngo_id)
    ngo = session.exec(statement).first()
    if not ngo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NGO not found")
    if not ngo.is_verified:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="NGO is not verified")

    pickup = Pickup(
        donor_id=current_user.user_id,
        ngo_id=body.ngo_id,
        pickup_address=body.pickup_address,
        scheduled_time=body.scheduled_time,
        items_description=body.items_description,
    )
    session.add(pickup)
    session.commit()
    session.refresh(pickup)

    # Initial status history
    entry = StatusHistoryEntry(
        pickup_id=pickup.pickup_id,
        status=PickupStatus.REQUESTED.value,
        changed_by_user_id=current_user.user_id,
    )
    session.add(entry)

    amount_paise = get_deposit_amount_paise(session)
    order_result = create_order(amount_paise, receipt=f"pickup_{pickup.pickup_id}")

    if order_result:
        # Real Razorpay order path (when keys are configured)
        order_id, _ = order_result
        payment = Payment(
            pickup_id=pickup.pickup_id,
            razorpay_order_id=order_id,
            amount=amount_paise,
            currency="INR",
            status="pending",
        )
        session.add(payment)
        session.commit()
        payment_status = "pending"
    else:
        # Dummy payment path for development: mark as already paid
        order_id = f"dummy_order_{pickup.pickup_id}"
        payment = Payment(
            pickup_id=pickup.pickup_id,
            razorpay_order_id=order_id,
            razorpay_payment_id=f"dummy_payment_{pickup.pickup_id}",
            amount=amount_paise,
            currency="INR",
            status="paid",
        )
        pickup.payment_status = "paid"
        session.add(payment)
        session.add(pickup)
        session.commit()
        payment_status = "paid"

    session.refresh(pickup)
    donor_name = f"{current_user.fname} {current_user.lname}".strip() or "A donor"
    scheduled_str = pickup.scheduled_time.strftime("%d/%m/%Y, %I:%M %p") if pickup.scheduled_time else ""
    background_tasks.add_task(
        send_pickup_request_to_ngo,
        ngo_email=ngo.email,
        ngo_name=ngo.ngo_name,
        donor_name=donor_name,
        pickup_id=pickup.pickup_id,
        pickup_address=pickup.pickup_address,
        scheduled_time=scheduled_str,
        items_description=pickup.items_description or "",
    )
    return {
        "pickup": pickup_to_response(session, pickup),
        "payment": {
            "order_id": order_id,
            "amount": amount_paise,
            "currency": "INR",
            "status": payment_status,
            "key_id": RAZORPAY_KEY_ID if get_razorpay_client() else None,
        },
    }


@router.post("/with-image", status_code=status.HTTP_201_CREATED)
async def create_pickup_with_image(
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles(UserRole.DONOR, UserRole.ADMIN)),
    image: UploadFile = File(...),
    ngo_id: int = Form(...),
    pickup_address: str = Form(...),
    scheduled_time: Optional[str] = Form(None),
    items_description: Optional[str] = Form(None),
):
    """Create a pickup request with an optional image upload (multipart/form-data)."""
    allowed_types = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
    ctype = (image.content_type or "").lower()
    if ctype == "image/jpg":
        ctype = "image/jpeg"
    if ctype not in allowed_types:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image must be png/jpg/jpeg/webp")

    raw = await image.read()
    if len(raw) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image file is empty")
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image must be <= 5MB")

    # Reuse schema validation for address + types
    body = PickupCreate(
        ngo_id=ngo_id,
        pickup_address=pickup_address,
        scheduled_time=scheduled_time,  # pydantic will coerce if matches ISO, else error
        items_description=items_description,
    )

    ngo = session.exec(select(NGO).where(NGO.ngo_id == body.ngo_id)).first()
    if not ngo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NGO not found")
    if not ngo.is_verified:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="NGO is not verified")

    pickup = Pickup(
        donor_id=current_user.user_id,
        ngo_id=body.ngo_id,
        pickup_address=body.pickup_address,
        scheduled_time=body.scheduled_time,
        items_description=body.items_description,
    )
    session.add(pickup)
    session.commit()
    session.refresh(pickup)

    # Save image
    ext = ".png" if ctype == "image/png" else ".webp" if ctype == "image/webp" else ".jpg"
    upload_dir = os.path.join(os.getcwd(), "uploads", "pickup_images")
    os.makedirs(upload_dir, exist_ok=True)
    fname = f"pickup_{pickup.pickup_id}_{uuid.uuid4().hex}{ext}"
    fpath = os.path.join(upload_dir, fname)
    with open(fpath, "wb") as f:
        f.write(raw)
    pickup.pickup_image_path = f"/uploads/pickup_images/{fname}"
    session.add(pickup)

    entry = StatusHistoryEntry(
        pickup_id=pickup.pickup_id,
        status=PickupStatus.REQUESTED.value,
        changed_by_user_id=current_user.user_id,
    )
    session.add(entry)

    amount_paise = get_deposit_amount_paise(session)
    order_result = create_order(amount_paise, receipt=f"pickup_{pickup.pickup_id}")

    if order_result:
        order_id, _ = order_result
        payment = Payment(
            pickup_id=pickup.pickup_id,
            razorpay_order_id=order_id,
            amount=amount_paise,
            currency="INR",
            status="pending",
        )
        session.add(payment)
        session.commit()
        payment_status = "pending"
    else:
        order_id = f"dummy_order_{pickup.pickup_id}"
        payment = Payment(
            pickup_id=pickup.pickup_id,
            razorpay_order_id=order_id,
            razorpay_payment_id=f"dummy_payment_{pickup.pickup_id}",
            amount=amount_paise,
            currency="INR",
            status="paid",
        )
        pickup.payment_status = "paid"
        session.add(payment)
        session.add(pickup)
        session.commit()
        payment_status = "paid"

    session.refresh(pickup)
    donor_name = f"{current_user.fname} {current_user.lname}".strip() or "A donor"
    scheduled_str = pickup.scheduled_time.strftime("%d/%m/%Y, %I:%M %p") if pickup.scheduled_time else ""
    background_tasks.add_task(
        send_pickup_request_to_ngo,
        ngo_email=ngo.email,
        ngo_name=ngo.ngo_name,
        donor_name=donor_name,
        pickup_id=pickup.pickup_id,
        pickup_address=pickup.pickup_address,
        scheduled_time=scheduled_str,
        items_description=pickup.items_description or "",
    )
    return {
        "pickup": pickup_to_response(session, pickup),
        "payment": {
            "order_id": order_id,
            "amount": amount_paise,
            "currency": "INR",
            "status": payment_status,
            "key_id": RAZORPAY_KEY_ID if get_razorpay_client() else None,
        },
    }


def _get_pickup_or_404(session: Session, pickup_id: int) -> Pickup:
    statement = select(Pickup).where(Pickup.pickup_id == pickup_id)
    pickup = session.exec(statement).first()
    if not pickup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pickup not found")
    return pickup


def _can_access_pickup(pickup: Pickup, user: Optional[User], ngo: Optional[NGO], is_admin: bool) -> bool:
    if is_admin:
        return True
    if user and pickup.donor_id == user.user_id:
        return True
    if ngo and pickup.ngo_id == ngo.ngo_id:
        return True
    return False


@router.get("")
def list_pickups(
    status_filter: Optional[str] = Query(None, alias="status"),
    session: Session = Depends(get_session),
    identity: tuple = Depends(get_current_user_or_ngo),
):
    """List pickups for current user (donor/admin) or NGO. Role-based filtering."""
    user, ngo = identity
    statement = select(Pickup)
    if user:
        if user.role == UserRole.ADMIN:
            pass  # all
        else:
            statement = statement.where(Pickup.donor_id == user.user_id)
    else:
        statement = statement.where(Pickup.ngo_id == ngo.ngo_id)
    if status_filter:
        statement = statement.where(Pickup.current_status == status_filter)
    statement = statement.order_by(Pickup.created_at.desc())
    pickups = session.exec(statement).all()
    ngo_ids = list({p.ngo_id for p in pickups})
    ngo_names = {}
    if ngo_ids:
        for nid in ngo_ids:
            n = session.get(NGO, nid)
            if n:
                ngo_names[nid] = n.ngo_name
    return [
        {
            "pickup_id": p.pickup_id,
            "donor_id": p.donor_id,
            "ngo_id": p.ngo_id,
            "ngo_name": ngo_names.get(p.ngo_id, f"NGO #{p.ngo_id}"),
            "pickup_address": p.pickup_address,
            "current_status": p.current_status,
            "payment_status": p.payment_status,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "items_description": p.items_description,
        }
        for p in pickups
    ]


@router.get("/{pickup_id}")
def get_pickup(
    pickup_id: int,
    session: Session = Depends(get_session),
    identity: tuple = Depends(get_current_user_or_ngo),
):
    """Get pickup detail with status history. Allowed for donor, assigned NGO, or admin."""
    pickup = _get_pickup_or_404(session, pickup_id)
    user, ngo = identity
    is_admin = user and user.role == UserRole.ADMIN
    if not _can_access_pickup(pickup, user, ngo, is_admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to view this pickup")
    return pickup_to_response(session, pickup)


@router.patch("/{pickup_id}/status")
def update_status(
    pickup_id: int,
    body: PickupStatusUpdate,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    identity: tuple = Depends(get_ngo_or_admin_user),
):
    """Update pickup status. Allowed for NGO (own pickups) or Admin. On COMPLETED, refund is triggered."""
    current_user, ngo = identity

    pickup = _get_pickup_or_404(session, pickup_id)
    if ngo and pickup.ngo_id != ngo.ngo_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to update this pickup")

    new_status = body.status
    if new_status == PickupStatus.ACCEPTED and pickup.payment_status != "paid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deposit must be paid before NGO can accept the pickup",
        )

    update_pickup_status(
        session,
        pickup,
        new_status,
        changed_by_user_id=current_user.user_id if current_user else None,
        changed_by_ngo_id=ngo.ngo_id if ngo else None,
        note=body.note,
    )

    if new_status == PickupStatus.COMPLETED:
        # Trigger refund (skip real API call for dummy payments)
        pay_stmt = select(Payment).where(Payment.pickup_id == pickup_id, Payment.status == "paid")
        payment = session.exec(pay_stmt).first()
        if payment and payment.razorpay_payment_id:
            is_dummy = (
                str(payment.razorpay_payment_id).startswith("dummy_")
                or str(payment.razorpay_order_id or "").startswith("dummy_")
            )
            if is_dummy:
                payment.status = "refunded"
                payment.refunded_at = datetime.utcnow()
                pickup.payment_status = "refunded"
                session.add(payment)
                session.add(pickup)
                session.commit()
            else:
                from app.services.razorpay_service import refund_payment
                refund_payment(payment.razorpay_payment_id)
                payment.status = "refund_pending"
                session.add(payment)
                pickup.payment_status = "refund_pending"
                session.add(pickup)
                session.commit()

    session.refresh(pickup)

    donor = session.get(User, pickup.donor_id)
    ngo_entity = session.get(NGO, pickup.ngo_id)
    if donor and ngo_entity:
        donor_name = f"{donor.fname} {donor.lname}".strip() or "Donor"
        background_tasks.add_task(
            send_pickup_status_to_donor,
            donor_email=donor.email,
            donor_name=donor_name,
            pickup_id=pickup.pickup_id,
            new_status=new_status.value,
            ngo_name=ngo_entity.ngo_name,
        )

    return pickup_to_response(session, pickup)


# Optional: allow NGO to "accept" a pickup (same as status update to ACCEPTED)
# Already covered by PATCH /{id}/status with body status=accepted
