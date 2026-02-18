from pydantic import BaseModel, EmailStr
from typing import List


class EmailSchema(BaseModel):
    subject: str
    email: List[EmailStr]
