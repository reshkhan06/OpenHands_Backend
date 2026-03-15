from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlmodel import Session, select

from app.models.ngo import NGO as NGOModel
from app.services.authentication import (
    hash_password,
    verify_password,
    create_access_token,
    create_ngo_verification_token,
)
from app.services.send_email import send_verification_email
from app.db.connection import get_session
from app.dependencies.auth import get_current_ngo
from app.schemas.ngo_sch import (
    NGOCreate,
    NGO as NGOSchema,
    NGOMeResponse,
    NGOLoginRequest,
    NGOLoginResponse,
)

router = APIRouter()


@router.get("/me", response_model=NGOMeResponse)
async def get_current_ngo_profile(current_ngo: NGOModel = Depends(get_current_ngo)):
    """Return the authenticated NGO's profile (no password)."""
    return NGOMeResponse(
        ngo_id=current_ngo.ngo_id,
        ngo_name=current_ngo.ngo_name,
        registration_number=current_ngo.registration_number,
        ngo_type=current_ngo.ngo_type,
        email=current_ngo.email,
        website_url=current_ngo.website_url,
        address=current_ngo.address,
        city=current_ngo.city,
        state=current_ngo.state,
        pincode=current_ngo.pincode,
        mission_statement=current_ngo.mission_statement,
        bank_name=current_ngo.bank_name,
        account_number=current_ngo.account_number,
        ifsc_code=current_ngo.ifsc_code,
        is_verified=current_ngo.is_verified,
        created_at=current_ngo.created_at.isoformat() if getattr(current_ngo, "created_at", None) else None,
    )


@router.get("/list")
async def list_verified_ngos(
    session: Session = Depends(get_session),
):
    """List verified NGOs for donor pickup selection. No auth required."""
    statement = select(NGOModel).where(NGOModel.is_verified == True).order_by(NGOModel.ngo_name)
    ngos = session.exec(statement).all()
    return [
        {"ngo_id": n.ngo_id, "ngo_name": n.ngo_name, "city": n.city, "state": n.state}
        for n in ngos
    ]


@router.post("/register", response_model=NGOSchema)
async def register_ngo(
    ngo_data: NGOCreate,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    """Register a new NGO and send verification email"""
    try:
        # Check if NGO already exists by email
        statement = select(NGOModel).where(NGOModel.email == ngo_data.email)
        existing_ngo = session.exec(statement).first()
        if existing_ngo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # Hash password
        hashed_password = hash_password(ngo_data.password)

        # Create new NGO
        new_ngo = NGOModel(
            ngo_name=ngo_data.ngo_name,
            registration_number=ngo_data.registration_number,
            ngo_type=ngo_data.ngo_type,
            email=ngo_data.email,
            website_url=str(ngo_data.website_url) if ngo_data.website_url else None,
            address=ngo_data.address,
            city=ngo_data.city,
            state=ngo_data.state,
            pincode=ngo_data.pincode,
            mission_statement=ngo_data.mission_statement,
            bank_name=ngo_data.bank_name,
            account_number=ngo_data.account_number,
            ifsc_code=ngo_data.ifsc_code,
            password=hashed_password,
            is_verified=False,
        )

        session.add(new_ngo)
        session.commit()
        session.refresh(new_ngo)

        # Create verification token and send email
        verification_token = create_ngo_verification_token(new_ngo.ngo_id)
        new_ngo.verification_token = verification_token
        session.add(new_ngo)
        session.commit()
        session.refresh(new_ngo)

        background_tasks.add_task(
            send_verification_email,
            email=ngo_data.email,
            name=ngo_data.ngo_name,
            token=verification_token,
        )

        return new_ngo

    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )


@router.post("/login", response_model=NGOLoginResponse)
async def login_ngo(
    credentials: NGOLoginRequest,
    session: Session = Depends(get_session),
):
    """Login NGO with email and password"""
    try:
        # Find NGO by email
        statement = select(NGOModel).where(NGOModel.email == credentials.email)
        ngo = session.exec(statement).first()

        if not ngo:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        # Verify password
        if not verify_password(credentials.password, ngo.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        # NGO must be approved by admin (is_verified) to log in
        if not ngo.is_verified:
            if ngo.verification_token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Please verify your email first. Check your inbox for the verification link.",
                )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Your account is pending admin approval. You will receive an email once approved.",
            )

        # Create access token
        access_token = create_access_token(
            data={"sub": ngo.email, "ngo_id": ngo.ngo_id}
        )

        return NGOLoginResponse(
            message="Login successful",
            access_token=access_token,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login",
        )
