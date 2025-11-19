"""
Health check endpoints.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_db

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK, tags=["Health"])
async def health_check():
    """
    Basic health check endpoint.
    Returns service status.
    """
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
    }


@router.get("/health/db", status_code=status.HTTP_200_OK, tags=["Health"])
async def database_health_check(db: AsyncSession = Depends(get_db)):
    """
    Database health check endpoint.
    Verifies database connectivity.
    """
    try:
        # Execute a simple query to check database connection
        result = await db.execute(text("SELECT 1"))
        result.scalar()

        return {
            "status": "healthy",
            "database": "connected",
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
        }
