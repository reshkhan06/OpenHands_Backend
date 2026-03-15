from sqlmodel import SQLModel, create_engine, Session, select
from sqlalchemy.pool import StaticPool
from sqlalchemy import text
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


def _migrate_add_user_is_active():
    """Add is_active column to users table if it doesn't exist (for existing DBs)."""
    if not DATABASE_URL.startswith("sqlite"):
        return
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM pragma_table_info('users') WHERE name='is_active'"))
        if result.scalar() == 0:
            conn.execute(text("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1"))
            conn.commit()
            print("Migration: added users.is_active column.")


def _seed_default_admin_if_missing():
    """Create default admin user if no user with admin@gmail.com exists."""
    from app.models.user import User
    from app.schemas.user_sch import UserRole, UserGender
    from app.services.authentication import hash_password

    with Session(engine) as session:
        existing = session.exec(select(User).where(User.email == "admin@gmail.com")).first()
        if existing:
            return
        hashed = hash_password("Admin@123")
        admin_user = User(
            fname="Admin",
            lname="User",
            email="admin@gmail.com",
            contact_number=9999999999,
            password=hashed,
            location="Admin",
            gender=UserGender.OTHER,
            role=UserRole.ADMIN,
            is_verified=True,
            is_active=True,
        )
        session.add(admin_user)
        session.commit()
        print("Seed: added default admin (admin@gmail.com, password: Admin@123)")


def _seed_ngos_if_empty():
    """Insert test NGOs for UI testing if the ngos table is empty."""
    from app.models.ngo import NGO
    from app.schemas.ngo_sch import NGOType
    from app.services.authentication import hash_password

    with Session(engine) as session:
        existing = session.exec(select(NGO)).first()
        if existing:
            return
        test_password = hash_password("Test@1234")
        for data in [
            {
                "ngo_name": "Hope Foundation",
                "registration_number": "REG/TEST/001",
                "ngo_type": NGOType.TRUST,
                "email": "ngo1@test.com",
                "address": "123 Charity Lane",
                "city": "Mumbai",
                "state": "Maharashtra",
                "pincode": "400001",
                "mission_statement": "Supporting underprivileged communities with education and healthcare.",
                "bank_name": "Test Bank",
                "account_number": "1234567890",
                "ifsc_code": "TEST0000001",
                "password": test_password,
                "is_verified": True,
            },
            {
                "ngo_name": "Green Earth Society",
                "registration_number": "REG/TEST/002",
                "ngo_type": NGOType.SOCIETY,
                "email": "ngo2@test.com",
                "address": "456 Green Avenue",
                "city": "Pune",
                "state": "Maharashtra",
                "pincode": "411001",
                "mission_statement": "Environmental conservation and sustainable development initiatives.",
                "bank_name": "Test Bank",
                "account_number": "0987654321",
                "ifsc_code": "TEST0000002",
                "password": test_password,
                "is_verified": True,
            },
        ]:
            session.add(NGO(**data))
        session.commit()
        print("Seed: added test NGOs (ngo1@test.com, ngo2@test.com, password: Test@1234)")


def create_db_and_tables():
    """Create all tables in the database"""
    # Import models to register them with SQLModel
    from app.models.user import User
    from app.models.ngo import NGO
    from app.models.email import Email
    from app.models.pickup import Pickup, StatusHistoryEntry
    from app.models.payment import Payment
    from app.models.admin_config import AdminConfig

    SQLModel.metadata.create_all(engine)
    _migrate_add_user_is_active()
    _seed_default_admin_if_missing()
    _seed_ngos_if_empty()
    print("Database tables created successfully!")


def get_session():
    """Get database session for dependency injection"""
    with Session(engine) as session:
        yield session


# Create tables on startup
if __name__ == "__main__":
    create_db_and_tables()
