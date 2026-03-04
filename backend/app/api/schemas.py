"""Shared Pydantic schemas for the API."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.api.deps import normalize_phone


# ---------------------------------------------------------------------------
# Student schemas
# ---------------------------------------------------------------------------

class StudentCreate(BaseModel):
    """Request body for creating a student."""
    phone_number: str = Field(..., description="Phone number in E.164 format (e.g., +5511999999999)")
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    english_level: str = Field(default="beginner", description="beginner or intermediate")
    whatsapp_messages: bool = Field(default=True)

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        return normalize_phone(v)


class StudentUpdate(BaseModel):
    """Request body for updating a student. Only provided fields are changed."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    english_level: Optional[str] = None
    whatsapp_messages: Optional[bool] = None


class StudentResponse(BaseModel):
    """Response model for student endpoints."""
    phone_number: str
    first_name: Optional[str]
    last_name: Optional[str]
    english_level: str
    whatsapp_messages: bool
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Message schemas
# ---------------------------------------------------------------------------

class SendRequest(BaseModel):
    """Request body for the send-word-of-day endpoint."""
    theme: str = Field(default="daily life", description="Topic theme for message")
    force: bool = Field(default=False, description="Send even if already sent today")


class SendResponse(BaseModel):
    """Response model for the send-word-of-day endpoint."""
    status: str
    sent_count: Optional[int] = None
    failed_count: Optional[int] = None
    total_recipients: Optional[int] = None
    sent: Optional[bool] = None
    date: Optional[str] = None
    used_fallback: bool
    validation_errors: List[str]
    provider_message_id: Optional[str] = None
    preview: Optional[str] = None
    sends: Optional[List[Dict[str, Any]]] = None


class PreviewResponse(BaseModel):
    """Response model for the preview endpoint."""
    valid: bool
    content: Optional[Dict[str, str]] = None
    validation_errors: List[str]


class BroadcastRequest(BaseModel):
    """Request body for the broadcast endpoint."""
    message: str = Field(..., min_length=1, description="Message to send to all active subscribers")
    level: Optional[str] = Field(None, description="Filter by English level (beginner/intermediate/advanced). Omit to send to all.")


class BroadcastResponse(BaseModel):
    """Response model for the broadcast endpoint."""
    sent_count: int
    failed_count: int
    total_recipients: int


# ---------------------------------------------------------------------------
# Schedule schemas
# ---------------------------------------------------------------------------

class ScheduleConfigUpdate(BaseModel):
    """Request body for PATCH /schedule — all fields optional."""
    theme: Optional[str] = None
    send_time: Optional[str] = None   # "HH:MM" validated in the router
    timezone: Optional[str] = None    # IANA string e.g. "America/Sao_Paulo"


class ScheduleConfigResponse(BaseModel):
    """Response model for schedule endpoints."""
    theme: str
    send_time: str   # HH:MM
    timezone: str


# ---------------------------------------------------------------------------
# Admin schemas
# ---------------------------------------------------------------------------

class StatsResponse(BaseModel):
    """Response model for the stats endpoint."""
    total_students: int
    active_students: int
    inactive_students: int
    subscribed: int
    opted_out: int
    sent_today: bool
    sends_today: int
