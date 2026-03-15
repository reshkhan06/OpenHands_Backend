import asyncio
import os
from dotenv import load_dotenv
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import BaseModel, EmailStr
from typing import List

load_dotenv()

USER = os.getenv("MAIL_USERNAME")
PASS = os.getenv("MAIL_PASSWORD")
FROM = os.getenv("MAIL_FROM")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


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

html_template = """
<!DOCTYPE html>
<html>
  <head>
    <style>
      .container {{
        font-family: Arial, sans-serif;
        padding: 20px;
        background-color: #f9f9f9;
        border-radius: 8px;
        max-width: 600px;
        margin: auto;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
      }}
      .btn {{
        background-color: #2d8fdd;
        color: white;
        padding: 12px 24px;
        text-decoration: none;
        border-radius: 5px;
        font-weight: bold;
        display: inline-block;
        margin-top: 20px;
      }}
    </style>
  </head>
  <body>
    <div class="container">
      <h2>Hello {name},</h2>
      <p>Thanks for registering! Please click the button below to verify your email address.</p>
      <a href="{url}" class="btn">Verify Email</a>
      <p>If you did not sign up for this account, please ignore this email.</p>
    </div>
  </body>
</html>
"""


async def send_verification_email(email: str, name: str, token: str):
    """Send verification email to user"""
    verify_url = f"{FRONTEND_URL}/verify?token={token}"
    email_body = html_template.format(name=name, url=verify_url)

    message = MessageSchema(
        subject="Account Verification - Donation OpenHand",
        recipients=[email],
        body=email_body,
        subtype=MessageType.html,
    )

    try:
        fm = FastMail(conf)
        await fm.send_message(message=message)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


# --- Pickup notifications ---

PICKUP_REQUEST_TO_NGO_HTML = """
<!DOCTYPE html>
<html>
  <head>
    <style>
      .container {{ font-family: Arial, sans-serif; padding: 20px; background-color: #f9f9f9; border-radius: 8px; max-width: 600px; margin: auto; }}
      .card {{ background: white; padding: 16px; border-radius: 8px; margin: 12px 0; border-left: 4px solid #2d8fdd; }}
      .label {{ font-weight: bold; color: #555; }}
      a {{ color: #2d8fdd; }}
    </style>
  </head>
  <body>
    <div class="container">
      <h2>Hello {ngo_name},</h2>
      <p><strong>{donor_name}</strong> has requested a donation pickup.</p>
      <div class="card">
        <p><span class="label">Pickup #</span> {pickup_id}</p>
        <p><span class="label">Address:</span> {pickup_address}</p>
        <p><span class="label">Scheduled time:</span> {scheduled_time}</p>
        <p><span class="label">Items:</span> {items_description}</p>
      </div>
      <p><a href="{dashboard_url}">View in dashboard</a> to accept and manage this pickup.</p>
    </div>
  </body>
</html>
"""

PICKUP_STATUS_TO_DONOR_HTML = """
<!DOCTYPE html>
<html>
  <head>
    <style>
      .container {{ font-family: Arial, sans-serif; padding: 20px; background-color: #f9f9f9; border-radius: 8px; max-width: 600px; margin: auto; }}
      .card {{ background: white; padding: 16px; border-radius: 8px; margin: 12px 0; border-left: 4px solid #2d8fdd; }}
      .status {{ font-weight: bold; color: #2d8fdd; }}
      a {{ color: #2d8fdd; }}
    </style>
  </head>
  <body>
    <div class="container">
      <h2>Hello {donor_name},</h2>
      <p>Your pickup <strong>#{pickup_id}</strong> (assigned to {ngo_name}) has been updated.</p>
      <div class="card">
        <p><span class="status">Current status: {status_label}</span></p>
      </div>
      <p><a href="{dashboard_url}">View in dashboard</a></p>
    </div>
  </body>
</html>
"""

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
    dashboard_url = f"{FRONTEND_URL}/dashboard/ngo/pickups/{pickup_id}"
    body = PICKUP_REQUEST_TO_NGO_HTML.format(
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
        return True
    except Exception as e:
        print(f"Error sending pickup notification to NGO: {e}")
        return False


async def send_pickup_status_to_donor(
    donor_email: str,
    donor_name: str,
    pickup_id: int,
    new_status: str,
    ngo_name: str,
):
    """Notify donor that their pickup status was updated by the NGO."""
    status_label = STATUS_LABELS.get(new_status.lower(), new_status.replace("_", " ").title())
    dashboard_url = f"{FRONTEND_URL}/dashboard/donor/pickups/{pickup_id}"
    body = PICKUP_STATUS_TO_DONOR_HTML.format(
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
        return True
    except Exception as e:
        print(f"Error sending pickup status to donor: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(
        send_verification_email(
            email="test@example.com", name="Test User", token="sample_token"
        )
    )
