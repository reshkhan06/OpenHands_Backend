from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlmodel import Session, select

from app.db.connection import get_session
from app.models.payment import Payment
from app.models.pickup import Pickup
from app.schemas.payment_sch import PaymentConfirmRequest, PaymentResponse
from app.dependencies.auth import get_current_user_or_ngo
from app.schemas.user_sch import UserRole
from app.services.razorpay_service import verify_payment_signature
from app.models.user import User
from app.models.ngo import NGO

router = APIRouter()


def _payment_to_response(p: Payment) -> dict:
    return {
        "payment_id": p.payment_id,
        "pickup_id": p.pickup_id,
        "razorpay_order_id": p.razorpay_order_id,
        "razorpay_payment_id": p.razorpay_payment_id,
        "amount": p.amount,
        "currency": p.currency,
        "status": p.status,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "paid_at": p.paid_at.isoformat() if p.paid_at else None,
        "refunded_at": p.refunded_at.isoformat() if p.refunded_at else None,
    }


@router.post("/confirm")
def confirm_payment(
    body: PaymentConfirmRequest,
    session: Session = Depends(get_session),
    identity: tuple = Depends(get_current_user_or_ngo),
):
    """Verify Razorpay signature and mark payment as paid. Call after successful checkout."""
    user, ngo = identity
    if not user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only donors can confirm payment")
    # Ensure pickup belongs to this donor
    statement = select(Pickup).where(Pickup.pickup_id == body.pickup_id)
    pickup = session.exec(statement).first()
    if not pickup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pickup not found")
    if pickup.donor_id != user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your pickup")

    pay_stmt = select(Payment).where(
        Payment.pickup_id == body.pickup_id,
        Payment.razorpay_order_id == body.razorpay_order_id,
        Payment.status == "pending",
    )
    payment = session.exec(pay_stmt).first()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    if not verify_payment_signature(
        body.razorpay_order_id,
        body.razorpay_payment_id,
        body.razorpay_signature,
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payment signature")

    payment.razorpay_payment_id = body.razorpay_payment_id
    payment.status = "paid"
    payment.paid_at = datetime.utcnow()
    pickup.payment_status = "paid"
    session.add(payment)
    session.add(pickup)
    session.commit()
    session.refresh(payment)
    return _payment_to_response(payment)


@router.get("/pickup/{pickup_id}")
def get_payment_for_pickup(
    pickup_id: int,
    session: Session = Depends(get_session),
    identity: tuple = Depends(get_current_user_or_ngo),
):
    """Get payment details for a pickup. Allowed for donor, NGO, or admin."""
    statement = select(Pickup).where(Pickup.pickup_id == pickup_id)
    pickup = session.exec(statement).first()
    if not pickup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pickup not found")
    user, ngo = identity
    is_admin = user and user.role == UserRole.ADMIN
    if user and pickup.donor_id == user.user_id:
        pass
    elif ngo and pickup.ngo_id == ngo.ngo_id:
        pass
    elif is_admin:
        pass
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to view this payment")

    pay_stmt = select(Payment).where(Payment.pickup_id == pickup_id)
    payment = session.exec(pay_stmt).first()
    if not payment:
        return {"pickup_id": pickup_id, "payment": None, "payment_status": pickup.payment_status}
    return {"pickup_id": pickup_id, "payment": _payment_to_response(payment), "payment_status": pickup.payment_status}


@router.post("/webhook/razorpay")
async def razorpay_webhook(request: Request, session: Session = Depends(get_session)):
    """Razorpay webhook for payment captured / refund processed. Verify signature using webhook secret."""
    body = await request.body()
    sig = request.headers.get("X-Razorpay-Signature", "")
    import os
    import hmac
    import hashlib
    secret = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
    if secret:
        expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook signature")
    import json
    data = json.loads(body) if isinstance(body, bytes) else body
    event = data.get("event")
    if event == "payment.captured":
        payload = data.get("payload", {}).get("payment", {}).get("entity", {})
        razorpay_payment_id = payload.get("id")
        order_id = payload.get("order_id")
        if order_id:
            statement = select(Payment).where(Payment.razorpay_order_id == order_id)
            payment = session.exec(statement).first()
            if payment and payment.status == "pending":
                payment.razorpay_payment_id = razorpay_payment_id
                payment.status = "paid"
                payment.paid_at = datetime.utcnow()
                session.add(payment)
                pickup_stmt = select(Pickup).where(Pickup.pickup_id == payment.pickup_id)
                pickup = session.exec(pickup_stmt).first()
                if pickup:
                    pickup.payment_status = "paid"
                    session.add(pickup)
                session.commit()
    elif event == "refund.processed" or event == "refund.created":
        payload = data.get("payload", {}).get("refund", {}).get("entity", {})
        payment_id = payload.get("payment_id")
        if payment_id:
            statement = select(Payment).where(Payment.razorpay_payment_id == payment_id)
            payment = session.exec(statement).first()
            if payment:
                payment.status = "refunded"
                payment.refunded_at = datetime.utcnow()
                session.add(payment)
                pickup_stmt = select(Pickup).where(Pickup.pickup_id == payment.pickup_id)
                pickup = session.exec(pickup_stmt).first()
                if pickup:
                    pickup.payment_status = "refunded"
                    session.add(pickup)
                session.commit()
    return {"status": "ok"}
