from fastapi import APIRouter, Depends, status, BackgroundTasks
from sqlmodel import Session

from app.db.connection import get_session
from app.models.feedback import Feedback as FeedbackModel
from app.schemas.feedback_sch import FeedbackCreate, FeedbackResponse
from app.services.send_email import send_contact_message_to_admin

router = APIRouter()


@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    body: FeedbackCreate,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    fb = FeedbackModel(
        name=body.name,
        email=str(body.email),
        category=body.category,
        message=body.message,
        rating=body.rating,
        follow_up=body.follow_up,
    )
    session.add(fb)
    session.commit()
    session.refresh(fb)

    # Fire-and-forget email to admin (if configured)
    background_tasks.add_task(
        send_contact_message_to_admin,
        name=body.name,
        email=str(body.email),
        subject=body.category,
        message_text=body.message,
        phone=None,
    )

    return FeedbackResponse(feedback_id=fb.feedback_id, created_at=fb.created_at)

