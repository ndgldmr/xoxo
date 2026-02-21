"""FastAPI routes for Word of the Day service."""
from fastapi import FastAPI, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from typing import Optional, List

from app.config import get_settings
from app.integrations.llm_client import LLMClient
from app.integrations.wasender_client import WaSenderClient
from app.logging.audit_log import AuditLog
from app.services.word_of_day_service import WordOfDayService
from app.api.webhook_routes import router as webhook_router
from app.repositories.student import StudentRepository


_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(_api_key_header)):
    """Verify the X-API-Key header. Skipped if API_KEY is not configured."""
    settings = get_settings()
    if not settings.api_key:
        return
    if api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


app = FastAPI(
    title="XOXO Education - Word of the Day",
    description="WhatsApp English Word/Phrase of the Day service",
    version="0.1.0",
)

# Mount webhook router
app.include_router(webhook_router)


class SendRequest(BaseModel):
    """Request model for sending Word of the Day."""
    theme: str = Field(default="daily life", description="Topic theme for message")
    level: str = Field(default="beginner", description="Difficulty level (beginner/intermediate)")
    force: bool = Field(default=False, description="Send even if already sent today")


class SendResponse(BaseModel):
    """Response model for send endpoint."""
    status: str
    sent_count: Optional[int] = None  # For multi-recipient mode
    failed_count: Optional[int] = None  # For multi-recipient mode
    total_recipients: Optional[int] = None  # For multi-recipient mode
    sent: Optional[bool] = None  # For backward compatibility (single-recipient)
    date: Optional[str]
    used_fallback: bool
    validation_errors: List[str]
    provider_message_id: Optional[str] = None  # For single-recipient
    preview: Optional[str]
    sends: Optional[List[dict]] = None  # For multi-recipient mode


class StudentCreate(BaseModel):
    """Request model for creating a student."""
    phone_number: str = Field(..., description="Phone number in E.164 format (e.g., +5511999999999)")
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    english_level: str = Field(default="beginner", description="beginner or intermediate")
    whatsapp_messages: bool = Field(default=True)


class StudentResponse(BaseModel):
    """Response model for student endpoints."""
    phone_number: str
    first_name: Optional[str]
    last_name: Optional[str]
    english_level: str
    whatsapp_messages: bool
    is_active: bool


def get_db_session():
    """Get a database session, raising 503 if database is not configured."""
    settings = get_settings()
    if not settings.database_url:
        raise HTTPException(status_code=503, detail="Database not configured")
    from app.db.session import _get_session_factory
    return _get_session_factory()()


def get_service() -> WordOfDayService:
    """Create and return a WordOfDayService instance with dependencies."""
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

    # Determine if using database mode
    db_session = None
    if settings.database_url:
        from app.db.session import _get_session_factory
        SessionLocal = _get_session_factory()
        db_session = SessionLocal()

    return WordOfDayService(
        llm_client=llm_client,
        whatsapp_client=whatsapp_client,
        audit_log=audit_log,
        db_session=db_session,
        send_delay=settings.send_delay_seconds,
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "XOXO Education - Word of the Day",
        "version": "0.1.0",
        "endpoints": {
            "send": "POST /send-word-of-day",
            "health": "GET /health",
            "list_students": "GET /students",
            "add_student": "POST /students",
            "remove_student": "DELETE /students/{phone_number}",
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    settings = get_settings()

    checks = {
        "llm_configured": bool(settings.llm_api_key),
        "wasender_configured": bool(settings.wasender_api_key),
        "database_configured": bool(settings.database_url),
        "dry_run": settings.dry_run,
    }

    all_ready = checks["llm_configured"] and checks["wasender_configured"]

    return {
        "status": "ready" if all_ready else "not_ready",
        "checks": checks,
    }


@app.post("/send-word-of-day", response_model=SendResponse, dependencies=[Security(verify_api_key)])
async def send_word_of_day(request: SendRequest) -> SendResponse:
    """
    Generate and send a Word of the Day message.

    Args:
        request: SendRequest with theme, level, and force parameters

    Returns:
        SendResponse with status and message details
    """
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
        # Close database session if it exists
        if service.db_session:
            service.db_session.commit()
            service.db_session.close()


@app.get("/students", response_model=List[StudentResponse], dependencies=[Security(verify_api_key)])
async def list_students(include_inactive: bool = False):
    """List all students."""
    session = get_db_session()
    try:
        repo = StudentRepository(session)
        students = repo.list_all(include_inactive=include_inactive)
        return [
            StudentResponse(
                phone_number=s.phone_number,
                first_name=s.first_name,
                last_name=s.last_name,
                english_level=s.english_level,
                whatsapp_messages=s.whatsapp_messages,
                is_active=s.is_active,
            )
            for s in students
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@app.post("/students", response_model=StudentResponse, status_code=201, dependencies=[Security(verify_api_key)])
async def add_student(student: StudentCreate):
    """Add a new student."""
    session = get_db_session()
    try:
        repo = StudentRepository(session)
        if repo.get_by_phone(student.phone_number):
            raise HTTPException(status_code=409, detail="Student with this phone number already exists")
        new_student = repo.create(
            phone_number=student.phone_number,
            first_name=student.first_name,
            last_name=student.last_name,
            english_level=student.english_level,
            whatsapp_messages=student.whatsapp_messages,
        )
        session.commit()
        return StudentResponse(
            phone_number=new_student.phone_number,
            first_name=new_student.first_name,
            last_name=new_student.last_name,
            english_level=new_student.english_level,
            whatsapp_messages=new_student.whatsapp_messages,
            is_active=new_student.is_active,
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@app.delete("/students/{phone_number}", status_code=204, dependencies=[Security(verify_api_key)])
async def remove_student(phone_number: str):
    """Deactivate (soft-delete) a student by phone number."""
    session = get_db_session()
    try:
        repo = StudentRepository(session)
        if not repo.delete(phone_number):
            raise HTTPException(status_code=404, detail="Student not found")
        session.commit()
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()
