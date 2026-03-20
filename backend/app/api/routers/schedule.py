"""Schedule configuration endpoints — reads/writes the GCP Cloud Scheduler job."""
import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_gcp_scheduler_client, verify_jwt
from app.api.schemas import ScheduleConfigResponse, ScheduleConfigUpdate
from app.integrations.gcp_scheduler import GCPSchedulerClient, GCPSchedulerError

router = APIRouter(tags=["schedule"], dependencies=[Depends(verify_jwt)])

_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


@router.get("/schedule", response_model=ScheduleConfigResponse)
async def get_schedule(
    gcp_client: Annotated[GCPSchedulerClient, Depends(get_gcp_scheduler_client)],
) -> ScheduleConfigResponse:
    """Return the current schedule config from the GCP Cloud Scheduler job."""
    try:
        config = gcp_client.get_config()
    except GCPSchedulerError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return ScheduleConfigResponse(**config)


@router.patch("/schedule", response_model=ScheduleConfigResponse)
async def update_schedule(
    body: ScheduleConfigUpdate,
    gcp_client: Annotated[GCPSchedulerClient, Depends(get_gcp_scheduler_client)],
) -> ScheduleConfigResponse:
    """Partially update the schedule config in the GCP Cloud Scheduler job."""
    # Validate provided fields
    if body.send_time is not None and not _TIME_RE.match(body.send_time):
        raise HTTPException(
            status_code=422,
            detail="send_time must match HH:MM (e.g. '09:00')",
        )

    # Fetch current config to fill in unset fields
    try:
        current = gcp_client.get_config()
    except GCPSchedulerError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    # Merge: only override fields that were explicitly provided
    merged = {
        "theme": body.theme if body.theme is not None else current["theme"],
        "send_time": body.send_time if body.send_time is not None else current["send_time"],
        "timezone": body.timezone if body.timezone is not None else current["timezone"],
    }

    try:
        gcp_client.update_job(**merged)
    except GCPSchedulerError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    # Keep the generate job's theme and timezone in sync if it is configured
    from app.config import get_settings
    settings = get_settings()
    if settings.gcp_generate_job_id:
        try:
            gcp_client.update_job_theme_and_timezone(
                job_id=settings.gcp_generate_job_id,
                theme=merged["theme"],
                timezone=merged["timezone"],
            )
        except GCPSchedulerError as exc:
            # Non-fatal: log the error but don't fail the request
            import logging
            logging.getLogger(__name__).warning(
                "Failed to sync generate job theme/timezone: %s", exc
            )

    return ScheduleConfigResponse(**merged)
