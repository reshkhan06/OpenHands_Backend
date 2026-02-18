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
    verify_url = f"http://127.0.0.1:8000/user/verify?token={token}"
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


if __name__ == "__main__":
    asyncio.run(
        send_verification_email(
            email="test@example.com", name="Test User", token="sample_token"
        )
    )
