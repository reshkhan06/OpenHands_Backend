from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import StaticPool
import os
from dotenv import load_dotenv

load_dotenv()

# Database URL - Using SQLite for development
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./donation.db")

# Engine configuration
if DATABASE_URL.startswith("sqlite"):
    # SQLite specific settings
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=True,  # Set to False in production
    )
else:
    # PostgreSQL or MySQL
    engine = create_engine(
        DATABASE_URL,
        echo=True,  # Set to False in production
        future=True,
    )


def create_db_and_tables():
    """Create all tables in the database"""
    # Import models to register them with SQLModel
    from app.models.user import User
    from app.models.admin import Admin
    from app.models.ngo import NGO
    from app.models.donation import Donation
    from app.models.pickup import Pickup
    from app.models.payment import Payment
    from app.models.email import Email

    SQLModel.metadata.create_all(engine)
    print("Database tables created successfully!")


def get_session():
    """Get database session for dependency injection"""
    with Session(engine) as session:
        yield session


# Create tables on startup
if __name__ == "__main__":
    create_db_and_tables()
