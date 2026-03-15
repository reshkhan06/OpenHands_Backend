import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import BaseModel, EmailStr
from typing import List

# Load .env from Backend directory so it works when running uvicorn from project root or Backend
_backend_dir = Path(__file__).resolve().parent.parent
load_dotenv(_backend_dir / ".env")
load_dotenv()  # also current working directory

logger = logging.getLogger(__name__)

USER = os.getenv("MAIL_USERNAME") or ""
PASS = os.getenv("MAIL_PASSWORD") or ""
FROM = os.getenv("MAIL_FROM") or ""
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "")  # Admin notified when new NGO registers; optional


def _mail_configured() -> bool:
    """Return True if mail credentials are set (not empty or placeholder)."""
    placeholder = ("your email", "your pass", "your key", "")
    u = (USER or "").strip().lower()
    p = (PASS or "").strip()
    f = (FROM or "").strip().lower()
    if u in placeholder or p in placeholder or f in placeholder:
        return False
    return bool(u and p and f)

# Directory containing .html email templates (same folder as this module)
_TEMPLATES_DIR = Path(__file__).resolve().parent / "email_templates"


def _load_template(filename: str) -> str:
    """Load an HTML template from email_templates/ by filename."""
    path = _TEMPLATES_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"Email template not found: {path}")
    return path.read_text(encoding="utf-8")


class EmailSchema(BaseModel):
    subject: str
    email: List[EmailStr]


conf = ConnectionConfig(
    MAIL_USERNAME=USER,
    MAIL_PASSWORD=PASS,
    MAIL_FROM=FROM,
    MAIL_PORT=465,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=True,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)


async def send_verification_email(email: str, name: str, token: str):
    """Send verification email to user."""
    if not _mail_configured():
        logger.warning(
            "Email not sent (verification): MAIL_USERNAME, MAIL_PASSWORD, or MAIL_FROM not set in .env. "
            "Set them in Backend/.env and use a Gmail App Password if using Gmail."
        )
        return False
    try:
        template = _load_template("verification_email.html")
    except FileNotFoundError as e:
        logger.exception("Email template missing: %s", e)
        return False
    verify_url = f"{FRONTEND_URL}/verify?token={token}"
    email_body = template.format(name=name, url=verify_url)

    message = MessageSchema(
        subject="Verify your email – OpenHands",
        recipients=[email],
        body=email_body,
        subtype=MessageType.html,
    )

    try:
        fm = FastMail(conf)
        await fm.send_message(message=message)
        logger.info("Verification email sent to %s", email)
        return True
    except Exception as e:
        logger.exception("Error sending verification email to %s: %s", email, e)
        return False


# --- Pickup notifications ---

STATUS_LABELS = {
    "requested": "New request",
    "accepted": "Accepted",
    "on_the_way": "On the way",
    "picked_up": "Picked up",
    "completed": "Completed",
    "cancelled": "Cancelled",
}


async def send_pickup_request_to_ngo(
    ngo_email: str,
    ngo_name: str,
    donor_name: str,
    pickup_id: int,
    pickup_address: str,
    scheduled_time: str,
    items_description: str,
):
    """Notify NGO that a donor has requested a pickup."""
    if not _mail_configured():
        logger.warning("Email not sent (pickup to NGO): mail not configured in .env")
        return False
    try:
        template = _load_template("pickup_request_to_ngo.html")
    except FileNotFoundError as e:
        logger.exception("Email template missing: %s", e)
        return False
    dashboard_url = f"{FRONTEND_URL}/dashboard/ngo/pickups/{pickup_id}"
    body = template.format(
        ngo_name=ngo_name,
        donor_name=donor_name,
        pickup_id=pickup_id,
        pickup_address=pickup_address or "—",
        scheduled_time=scheduled_time or "—",
        items_description=(items_description or "—")[:200],
        dashboard_url=dashboard_url,
    )
    message = MessageSchema(
        subject=f"New pickup request #{pickup_id} from {donor_name} – OpenHands",
        recipients=[ngo_email],
        body=body,
        subtype=MessageType.html,
    )
    try:
        fm = FastMail(conf)
        await fm.send_message(message=message)
        logger.info("Pickup request email sent to NGO %s", ngo_email)
        return True
    except Exception as e:
        logger.exception("Error sending pickup notification to NGO %s: %s", ngo_email, e)
        return False


async def send_pickup_status_to_donor(
    donor_email: str,
    donor_name: str,
    pickup_id: int,
    new_status: str,
    ngo_name: str,
):
    """Notify donor that their pickup status was updated by the NGO."""
    if not _mail_configured():
        logger.warning("Email not sent (pickup status to donor): mail not configured in .env")
        return False
    try:
        template = _load_template("pickup_status_to_donor.html")
    except FileNotFoundError as e:
        logger.exception("Email template missing: %s", e)
        return False
    status_label = STATUS_LABELS.get(new_status.lower(), new_status.replace("_", " ").title())
    dashboard_url = f"{FRONTEND_URL}/dashboard/donor/pickups/{pickup_id}"
    body = template.format(
        donor_name=donor_name,
        pickup_id=pickup_id,
        status_label=status_label,
        ngo_name=ngo_name,
        dashboard_url=dashboard_url,
    )
    message = MessageSchema(
        subject=f"Pickup #{pickup_id} – {status_label} – OpenHands",
        recipients=[donor_email],
        body=body,
        subtype=MessageType.html,
    )
    try:
        fm = FastMail(conf)
        await fm.send_message(message=message)
        logger.info("Pickup status email sent to donor %s", donor_email)
        return True
    except Exception as e:
        logger.exception("Error sending pickup status to donor %s: %s", donor_email, e)
        return False


# --- New NGO notification to admin ---

async def send_new_ngo_notification_to_admin(
    ngo_name: str,
    ngo_email: str,
    city: str,
    state: str,
    registration_number: str,
):
    """Notify admin that a new NGO has verified email and is pending approval."""
    if not ADMIN_EMAIL or not ADMIN_EMAIL.strip():
        return False
    if not _mail_configured():
        logger.warning("Email not sent (new NGO to admin): mail not configured in .env")
        return False
    try:
        template = _load_template("new_ngo_to_admin.html")
    except FileNotFoundError as e:
        logger.exception("Email template missing: %s", e)
        return False
    admin_url = f"{FRONTEND_URL}/admin/ngos"
    body = template.format(
        ngo_name=ngo_name,
        ngo_email=ngo_email,
        city=city or "—",
        state=state or "—",
        registration_number=registration_number or "—",
        admin_url=admin_url,
    )
    message = MessageSchema(
        subject=f"New NGO pending approval: {ngo_name} – OpenHands",
        recipients=[ADMIN_EMAIL.strip()],
        body=body,
        subtype=MessageType.html,
    )
    if not _mail_configured():
        logger.warning("Email not sent (new NGO to admin): mail not configured in .env")
        return False
    try:
        fm = FastMail(conf)
        await fm.send_message(message=message)
        logger.info("New NGO notification sent to admin %s", ADMIN_EMAIL.strip())
        return True
    except Exception as e:
        logger.exception("Error sending new NGO notification to admin: %s", e)
        return False


# --- NGO approval / rejection result email ---

async def send_ngo_approval_result(ngo_email: str, ngo_name: str, approved: bool):
    """Send email to NGO after admin approves or rejects their account."""
    if not _mail_configured():
        logger.warning("Email not sent (NGO approval result): mail not configured in .env")
        return False
    try:
        template = _load_template("ngo_approval.html")
    except FileNotFoundError as e:
        logger.exception("Email template missing: %s", e)
        return False
    login_url = f"{FRONTEND_URL}/login"
    if approved:
        body_block = (
            '<div class="body-block success">'
            '<p><strong>Your NGO account has been approved.</strong> '
            'You can now log in and start receiving donation pickups.</p></div>'
        )
    else:
        body_block = (
            '<div class="body-block reject">'
            '<p><strong>Your NGO registration has been reviewed and was not approved.</strong> '
            'If you believe this is an error, please contact support.</p></div>'
        )
    body = template.format(ngo_name=ngo_name, body_block=body_block, login_url=login_url)
    subject = "Your NGO account has been approved – OpenHands" if approved else "NGO registration update – OpenHands"
    message = MessageSchema(
        subject=subject,
        recipients=[ngo_email],
        body=body,
        subtype=MessageType.html,
    )
    try:
        fm = FastMail(conf)
        await fm.send_message(message=message)
        logger.info("NGO approval result email sent to %s", ngo_email)
        return True
    except Exception as e:
        logger.exception("Error sending NGO approval result to %s: %s", ngo_email, e)
        return False


if __name__ == "__main__":
    asyncio.run(
        send_verification_email(
            email="test@example.com", name="Test User", token="sample_token"
        )
    )
