"""Message generation and sending endpoints."""
import logging

from fastapi import APIRouter, HTTPException, Security

from app.api.deps import verify_api_key, get_service, get_preview_service
from app.api.schemas import SendRequest, SendResponse, PreviewResponse

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
            level=request.level,
            force=request.force,
        )
        return SendResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if service.db_session:
            service.db_session.commit()
            service.db_session.close()


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
