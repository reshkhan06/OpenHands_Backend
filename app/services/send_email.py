import asyncio
import os
from dotenv import load_dotenv
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

from fastapi import (
    BackgroundTasks,
    UploadFile,
    File,
    Form,
    Depends,
    HTTPException,
    status,
)

# from app.services.authentication import token_encode

from pydantic import BaseModel, EmailStr
from typing import List


class EmailSchema(BaseModel):
    subject: str
    email: List[EmailStr]


load_dotenv()

USER = os.getenv("MAIL_USERNAME")
PASS = os.getenv("MAIL_PASSWORD")
FROM = os.getenv("MAIL_FROM")

print()

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

html = """
<!DOCTYPE html>
<html>
  <head>
    <style>
      .container {
        font-family: Arial, sans-serif;
        padding: 20px;
        background-color: #f9f9f9;
        border-radius: 8px;
        max-width: 600px;
        margin: auto;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
      }
      .btn {
        background-color: #2d8fdd;
        color: white;
        padding: 12px 24px;
        text-decoration: none;
        border-radius: 5px;
        font-weight: bold;
        display: inline-block;
        margin-top: 20px;
      }
    </style>
  </head>
  <body>
    <div class="container">
      <h2>Hello {{name}},</h2>
      <p>Thanks for registering! Please click the button below to verify your email address.</p>
      <a href="{{url}}" class="btn">Verify Email</a>
      <p>If you did not sign up for this account, please ignore this email.</p>
    </div>
  </body>
</html>
"""


async def send_email(email: EmailSchema):
    # token_data = {"id": user_id, "name": user_name}
    # token = token_encode(data=token_data)
    token = "sample_token"  # Replace with actual token generation

    verify_url = f"http://127.0.0.1:8000/user/verification?token={token}"

    email_body = html.replace("{{name}}", "User").replace("{{url}}", verify_url)

    message = MessageSchema(
        subject="Account verification email",
        recipients=email.email,
        body=email_body,
        subtype=MessageType.html,  # Important: use HTML
    )

    fm = FastMail(conf)
    await fm.send_message(message=message)
    return "Email sent"


if __name__ == "__main__":
    data = {
        "subject": "user register",
        "email": ["faizack619@gmail.com"],
    }
    email_data = EmailSchema(**data)
    asyncio.run(send_email(email_data))  # Add () to call the function
