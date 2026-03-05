"""FastAPI application factory."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.routers.students import router as students_router
from app.api.routers.messages import router as messages_router
from app.api.routers.admin import router as admin_router
from app.api.routers.schedule import router as schedule_router
from app.api.webhook_routes import router as webhook_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.database_url:
        from app.db.session import init_db
        init_db()
    yield


app = FastAPI(
    title="XOXO Education - Word of the Day",
    description="WhatsApp English Word/Phrase of the Day service",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(",") if settings.allowed_origins else ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(students_router)
app.include_router(messages_router)
app.include_router(admin_router)
app.include_router(schedule_router)
app.include_router(webhook_router)


@app.get("/")
async def root():
    """Service info and endpoint listing."""
    return {
        "service": "XOXO Education - Word of the Day",
        "version": "0.1.0",
        "endpoints": {
            # Students
            "list_students": "GET /students",
            "create_student": "POST /students",
            "get_student": "GET /students/{phone_number}",
            "update_student": "PATCH /students/{phone_number}",
            "deactivate_student": "POST /students/{phone_number}/deactivate",
            "reactivate_student": "POST /students/{phone_number}/reactivate",
            "delete_student": "DELETE /students/{phone_number}",
            # Messages
            "send": "POST /send-word-of-day",
            "generate_daily": "POST /messages/generate",
            "today_messages": "GET /messages/today",
            # Schedule
            "get_schedule": "GET /schedule",
            "update_schedule": "PATCH /schedule",
            # Admin
            "health": "GET /health",
            "stats": "GET /stats",
            "audit_log": "GET /audit-log",
        },
    }


@app.get("/health")
async def health():
    """Health check — confirms which services are configured."""
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
