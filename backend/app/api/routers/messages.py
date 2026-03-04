"""Message generation and sending endpoints."""
import logging
import time

from fastapi import APIRouter, HTTPException, Security

from app.api.deps import verify_api_key, get_service, get_preview_service
from app.api.schemas import SendRequest, SendResponse, PreviewResponse, BroadcastRequest, BroadcastResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["messages"])

_auth = [Security(verify_api_key)]


@router.post("/send-word-of-day", response_model=SendResponse, dependencies=_auth)
async def send_word_of_day(request: SendRequest) -> SendResponse:
    """Generate and send a Word of the Day to all active subscribers."""
    service = get_service()
    try:
        result = service.run_daily_job(
            theme=request.theme,
            force=request.force,
        )
        return SendResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if service.db_session:
            service.db_session.commit()
            service.db_session.close()


@router.post("/broadcast", response_model=BroadcastResponse, dependencies=_auth)
async def broadcast_message(request: BroadcastRequest) -> BroadcastResponse:
    """Send a custom message to all active WhatsApp subscribers, optionally filtered by level."""
    from app.config import get_settings
    from app.integrations.wasender_client import WaSenderClient
    from app.repositories.student import StudentRepository

    settings = get_settings()

    if not settings.database_url:
        raise HTTPException(status_code=503, detail="Database not configured")

    whatsapp_client = WaSenderClient(
        api_key=settings.wasender_api_key,
        dry_run=settings.dry_run,
    )

    from app.db.session import _get_session_factory
    db_session = _get_session_factory()()
    try:
        repo = StudentRepository(db_session)
        students = repo.get_active_subscribers(level=request.level)

        sent = 0
        failed = 0
        for student in students:
            try:
                whatsapp_client.send_message(student.phone_number, request.message)
                sent += 1
            except Exception as e:
                logger.warning("Broadcast failed for %s: %s", student.phone_number, e)
                failed += 1
            if settings.send_delay_seconds > 0:
                time.sleep(settings.send_delay_seconds)

        return BroadcastResponse(
            sent_count=sent,
            failed_count=failed,
            total_recipients=len(students),
        )
    finally:
        db_session.close()


@router.get("/preview", response_model=PreviewResponse, dependencies=_auth)
async def preview_message(
    theme: str = "daily life",
    level: str = "beginner",
) -> PreviewResponse:
    """Generate and validate a message without sending it."""
    service = get_preview_service()
    try:
        result = service.preview_message(theme=theme, level=level)
        return PreviewResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
