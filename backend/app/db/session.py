"""Database session management."""
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

# Global engine and session factory (initialized on first use)
_engine = None
_SessionLocal = None


def _get_engine():
    """Get or create the database engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        database_url = getattr(settings, "database_url", "sqlite:///./xoxo.db")
        _engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False} if database_url.startswith("sqlite") else {},
        )
    return _engine


def _get_session_factory():
    """Get or create the session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        engine = _get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.

    Usage:
        with get_session() as session:
            # Use session here
            session.query(...)
    """
    SessionLocal = _get_session_factory()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Initialize database by creating all tables."""
    from app.db.base import Base
    # Import all models to ensure they're registered with Base
    from app.db.models import student, message, admin  # noqa: F401

    engine = _get_engine()
    Base.metadata.create_all(bind=engine)
