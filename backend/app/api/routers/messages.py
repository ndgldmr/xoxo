"""Message generation and sending endpoints."""
import logging
import time
from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Security
from sqlalchemy.orm import Session

from app.api.deps import verify_api_key, get_service, get_preview_service, get_db, get_gcp_scheduler_client
from app.api.schemas import (
    SendRequest, SendResponse,
    BroadcastRequest, BroadcastResponse,
    GenerateRequest, GenerateResponse, GeneratedMessageResponse,
    TodayMessagesResponse, StoredMessageResponse,
)
from app.db.models.message import LEVELS
from app.integrations.gcp_scheduler import GCPSchedulerClient, GCPSchedulerError
from app.repositories.message import MessageRepository

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



@router.post("/messages/generate", response_model=GenerateResponse, dependencies=_auth)
async def generate_daily_messages(
    request: GenerateRequest,
    db: Annotated[Session, Depends(get_db)],
) -> GenerateResponse:
    """
    Generate and store today's messages for all levels (or a single level).

    Called automatically by the GCP generate job. Admins can also call this
    to regenerate messages (e.g. if they want a fresh batch before the send job runs).

    If theme is omitted, reads it from the GCP send job config.
    """
    from app.config import get_settings

    settings = get_settings()
    theme = request.theme

    # If no theme provided, read from GCP send job config
    if not theme:
        if not settings.gcp_project_id:
            theme = "daily life"
        else:
            try:
                gcp_client = get_gcp_scheduler_client()
                config = gcp_client.get_config()
                theme = config.get("theme") or "daily life"
            except Exception:
                theme = "daily life"

    target_levels = [request.level] if request.level else LEVELS

    service = get_preview_service()
    repo = MessageRepository(db)
    today = date.today()
    results = []

    for level in target_levels:
        result = service.generate_message(theme=theme, level=level, db_session=db)

        if result["valid"]:
            repo.upsert(
                date=today,
                level=level,
                theme=theme,
                template_params=result["template_params"],
                formatted_message=result["formatted_message"],
            )

        results.append(GeneratedMessageResponse(
            level=level,
            theme=theme,
            formatted_message=result["formatted_message"],
            valid=result["valid"],
            validation_errors=result["validation_errors"],
        ))

    return GenerateResponse(date=today.isoformat(), results=results)


@router.get("/messages/today", response_model=TodayMessagesResponse, dependencies=_auth)
async def get_today_messages(
    db: Annotated[Session, Depends(get_db)],
) -> TodayMessagesResponse:
    """Return today's pre-generated messages from the messages table."""
    repo = MessageRepository(db)
    today = date.today()
    messages = repo.get_by_date(today)

    return TodayMessagesResponse(
        date=today.isoformat(),
        messages=[
            StoredMessageResponse(
                level=m.level,
                theme=m.theme,
                formatted_message=m.formatted_message,
                generated_at=m.updated_at.isoformat(),
            )
            for m in messages
        ],
    )
