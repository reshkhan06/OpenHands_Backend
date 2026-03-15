from typing import Optional
from sqlmodel import Session, select
from fastapi import HTTPException, status
from datetime import datetime
from app.models.pickup import Pickup, StatusHistoryEntry
from app.schemas.pickup_sch import PickupStatus, ALLOWED_TRANSITIONS


def get_deposit_amount_paise(session: Session) -> int:
    """Get configured deposit amount in paise from admin_config."""
    from app.models.admin_config import AdminConfig
    statement = select(AdminConfig).where(AdminConfig.key == "deposit_amount_paise")
    row = session.exec(statement).first()
    if row and row.value.isdigit():
        return int(row.value)
    return 10000  # default 100 INR in paise


def can_transition(current: PickupStatus, next_status: PickupStatus) -> bool:
    allowed = ALLOWED_TRANSITIONS.get(current, [])
    return next_status in allowed


def update_pickup_status(
    session: Session,
    pickup: Pickup,
    new_status: PickupStatus,
    changed_by_user_id: Optional[int] = None,
    changed_by_ngo_id: Optional[int] = None,
    note: Optional[str] = None,
) -> Pickup:
    current = PickupStatus(pickup.current_status)
    if not can_transition(current, new_status):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition from {current.value} to {new_status.value}",
        )
    pickup.current_status = new_status.value
    pickup.updated_at = datetime.utcnow()
    session.add(pickup)
    entry = StatusHistoryEntry(
        pickup_id=pickup.pickup_id,
        status=new_status.value,
        changed_by_user_id=changed_by_user_id,
        changed_by_ngo_id=changed_by_ngo_id,
        note=note,
    )
    session.add(entry)
    session.commit()
    session.refresh(pickup)
    return pickup


def build_status_history(session: Session, pickup_id: int) -> list:
    statement = (
        select(StatusHistoryEntry)
        .where(StatusHistoryEntry.pickup_id == pickup_id)
        .order_by(StatusHistoryEntry.changed_at)
    )
    entries = session.exec(statement).all()
    return [
        {
            "status": e.status,
            "changed_at": e.changed_at.isoformat() if e.changed_at else None,
            "changed_by_user_id": e.changed_by_user_id,
            "changed_by_ngo_id": e.changed_by_ngo_id,
            "note": e.note,
        }
        for e in entries
    ]


def pickup_to_response(session: Session, pickup: Pickup) -> dict:
    history = build_status_history(session, pickup.pickup_id)
    return {
        "pickup_id": pickup.pickup_id,
        "donor_id": pickup.donor_id,
        "ngo_id": pickup.ngo_id,
        "pickup_address": pickup.pickup_address,
        "scheduled_time": pickup.scheduled_time.isoformat() if pickup.scheduled_time else None,
        "items_description": pickup.items_description,
        "current_status": pickup.current_status,
        "payment_status": pickup.payment_status,
        "status_history": history,
        "created_at": pickup.created_at.isoformat() if pickup.created_at else None,
        "updated_at": pickup.updated_at.isoformat() if pickup.updated_at else None,
    }
