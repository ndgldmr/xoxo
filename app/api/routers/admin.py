"""Admin endpoints: stats and audit log."""
from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Security
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_audit_log, verify_api_key
from app.api.schemas import StatsResponse
from app.logging.audit_log import AuditLog
from app.repositories.student import StudentRepository

router = APIRouter(tags=["admin"])

_auth = [Security(verify_api_key)]


@router.get("/stats", response_model=StatsResponse, dependencies=_auth)
async def get_stats(
    db: Session = Depends(get_db),
    audit_log: AuditLog = Depends(get_audit_log),
) -> StatsResponse:
    """Dashboard statistics: student counts and today's send status."""
    repo = StudentRepository(db)
    all_students = repo.list_all(include_inactive=True)

    active = [s for s in all_students if s.is_active]
    inactive = [s for s in all_students if not s.is_active]
    subscribed = [s for s in active if s.whatsapp_messages]
    opted_out = [s for s in active if not s.whatsapp_messages]

    today_events = audit_log.get_today_events()
    sent_today = any(e.get("sent") for e in today_events)
    sends_today = sum(1 for e in today_events if e.get("sent"))

    return StatsResponse(
        total_students=len(all_students),
        active_students=len(active),
        inactive_students=len(inactive),
        subscribed=len(subscribed),
        opted_out=len(opted_out),
        sent_today=sent_today,
        sends_today=sends_today,
    )


@router.get("/audit-log", dependencies=_auth)
async def list_audit_log(
    date_str: Optional[str] = None,
    phone_number: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    audit_log: AuditLog = Depends(get_audit_log),
) -> Dict[str, Any]:
    """
    List audit log events with optional filtering.

    - **date_str**: ISO date (e.g. `2026-02-26`). Defaults to today.
    - **phone_number**: Filter to a specific recipient.
    - **limit** / **offset**: Pagination controls.
    """
    target_date = date_str or date.today().isoformat()
    events = audit_log.get_events(
        date_str=target_date,
        phone_number=phone_number,
        limit=limit,
        offset=offset,
    )
    return {"date": target_date, "count": len(events), "events": events}
