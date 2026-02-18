from sqlmodel import Field, SQLModel


class Admin(SQLModel, table=True):
    __tablename__ = "admins"

    admin_id: int = Field(default=None, primary_key=True)
    name: str
