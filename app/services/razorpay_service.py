import os
import hmac
import hashlib
from typing import Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")


def get_razorpay_client():
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        return None
    try:
        import razorpay
        return razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    except Exception:
        return None


def create_order(amount_paise: int, currency: str = "INR", receipt: Optional[str] = None) -> Optional[Tuple[str, dict]]:
    """
    Dummy order creator for development.

    For now we do NOT call Razorpay at all and always return None,
    so the backend will treat this as "no deposit required" and
    the frontend will skip opening the Razorpay checkout.
    """
    return None


def verify_payment_signature(order_id: str, payment_id: str, signature: str) -> bool:
    payload = f"{order_id}|{payment_id}"
    expected = hmac.new(
        RAZORPAY_KEY_SECRET.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def refund_payment(payment_id: str, amount_paise: Optional[int] = None) -> Optional[dict]:
    """Refund full or partial amount. amount_paise None = full refund. Returns refund dict or None."""
    if not payment_id or str(payment_id).strip().startswith("dummy_"):
        return None
    client = get_razorpay_client()
    if not client:
        return None
    data = {} if amount_paise is None else {"amount": amount_paise}
    return client.payment.refund(payment_id, data)
