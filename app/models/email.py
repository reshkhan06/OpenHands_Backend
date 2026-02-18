from sqlmodel import Field, SQLModel


class Email(SQLModel, table=True):
    __tablename__ = "emails"

    email_id: int = Field(default=None, primary_key=True)
    recipient: str = Field(index=True)
    subject: str
    body: str
    sent_at: str = Field(default=None, nullable=True)
