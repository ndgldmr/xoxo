"""Shared FastAPI dependencies."""
import re
import logging
from typing import Generator

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_session
from app.integrations.llm_client import LLMClient
from app.integrations.wasender_client import WaSenderClient
from app.integrations.gcp_scheduler import GCPSchedulerClient
from app.logging.audit_log import AuditLog
from app.services.word_of_day_service import WordOfDayService

logger = logging.getLogger(__name__)

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def normalize_phone(raw: str) -> str:
    """Normalize a phone number to E.164 format.

    Strips whitespace and common formatting characters, adds a leading '+' if
    missing, then validates that the result matches E.164: '+' followed by 7–15 digits.

    Raises:
        ValueError: If the result is not a valid E.164 number.
    """
    cleaned = re.sub(r"[\s\-().]", "", raw.strip())
    if not cleaned.startswith("+"):
        cleaned = "+" + cleaned
    if not re.fullmatch(r"\+\d{7,15}", cleaned):
        raise ValueError(
            f"Invalid phone number '{raw}'. "
            "Please use E.164 format, e.g. +5511999999999."
        )
    return cleaned


async def verify_api_key(api_key: str = Security(_api_key_header)) -> None:
    """Verify the X-API-Key header. Skipped if API_KEY is not configured."""
    settings = get_settings()
    if not settings.api_key:
        return
    if api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def get_db() -> Generator[Session, None, None]:
    """Database session dependency with automatic commit/rollback."""
    with get_session() as session:
        yield session


def get_audit_log() -> AuditLog:
    """Return an AuditLog instance."""
    settings = get_settings()
    return AuditLog(log_path=settings.audit_log_path)


def get_service() -> WordOfDayService:
    """Create a WordOfDayService for sending to all active subscribers."""
    settings = get_settings()

    llm_client = LLMClient(
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        timeout=settings.llm_timeout,
    )
    whatsapp_client = WaSenderClient(
        api_key=settings.wasender_api_key,
        dry_run=settings.dry_run,
    )
    audit_log = AuditLog(log_path=settings.audit_log_path)

    db_session = None
    if settings.database_url:
        from app.db.session import _get_session_factory
        db_session = _get_session_factory()()

    return WordOfDayService(
        llm_client=llm_client,
        whatsapp_client=whatsapp_client,
        audit_log=audit_log,
        db_session=db_session,
        send_delay=settings.send_delay_seconds,
    )


def get_gcp_scheduler_client() -> GCPSchedulerClient:
    """Return a GCPSchedulerClient or raise 503 if GCP vars are not configured."""
    settings = get_settings()
    missing = [
        v for v in (
            settings.gcp_project_id,
            settings.gcp_location,
            settings.gcp_scheduler_job_id,
            settings.service_url,
        )
        if not v
    ]
    if missing:
        raise HTTPException(
            status_code=503,
            detail="GCP scheduler not configured",
        )
    return GCPSchedulerClient(
        project_id=settings.gcp_project_id,
        location=settings.gcp_location,
        job_id=settings.gcp_scheduler_job_id,
        service_url=settings.service_url,
        api_key=settings.api_key,
    )


def get_preview_service() -> WordOfDayService:
    """Create a WordOfDayService for preview only (no DB session, no sending)."""
    settings = get_settings()

    llm_client = LLMClient(
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        timeout=settings.llm_timeout,
    )
    whatsapp_client = WaSenderClient(
        api_key=settings.wasender_api_key,
        dry_run=True,  # always dry-run for preview
    )
    audit_log = AuditLog(log_path=settings.audit_log_path)

    return WordOfDayService(
        llm_client=llm_client,
        whatsapp_client=whatsapp_client,
        audit_log=audit_log,
        to_number="+10000000000",  # dummy — preview never sends
    )
