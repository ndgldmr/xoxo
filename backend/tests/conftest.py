"""
Pytest configuration and fixtures.
"""

import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.deps import get_db
from app.db.base import Base
from app.main import app

# Test database URL (using in-memory SQLite for tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create async engine for tests
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
)

# Create async session factory for tests
test_session_maker = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Create an event loop for the test session.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a fresh database session for each test.
    Creates all tables before test and drops them after.
    """
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async with test_session_maker() as session:
        yield session

    # Drop tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Create an async HTTP client for testing API endpoints.
    Overrides the get_db dependency to use test database.
    """

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    # Override dependency
    app.dependency_overrides[get_db] = override_get_db

    # Create client
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as test_client:
        yield test_client

    # Clear overrides
    app.dependency_overrides.clear()


# Example fixture for creating test data
@pytest.fixture
def sample_user_data() -> dict[str, Any]:
    """Sample user data for testing."""
    return {
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "phone": "+1234567890",
        "is_active": True,
        "password": "TestPassword123!",
        "is_admin": False,
    }


@pytest.fixture
def sample_admin_data() -> dict[str, Any]:
    """Sample admin user data for testing."""
    return {
        "email": "admin@xoxoeducation.com",
        "first_name": "Admin",
        "last_name": "User",
        "phone": "+1234567890",
        "is_active": True,
        "password": "AdminPassword123!",
        "is_admin": True,
    }


@pytest.fixture
async def test_user(db_session: AsyncSession, sample_user_data: dict[str, Any]):
    """Create a test user in the database."""
    from app.models.user import User
    from app.core.security import hash_password

    user_data = sample_user_data.copy()
    password = user_data.pop("password")

    user = User(
        **user_data,
        hashed_password=hash_password(password)
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Store password for login tests
    user.plain_password = password

    return user


@pytest.fixture
async def test_admin(db_session: AsyncSession, sample_admin_data: dict[str, Any]):
    """Create a test admin user in the database."""
    from app.models.user import User
    from app.core.security import hash_password

    admin_data = sample_admin_data.copy()
    password = admin_data.pop("password")

    admin = User(
        **admin_data,
        hashed_password=hash_password(password)
    )

    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)

    # Store password for login tests
    admin.plain_password = password

    return admin


@pytest.fixture
async def user_token(test_user):
    """Generate access token for test user."""
    from app.core.security import create_access_token

    return create_access_token(subject=test_user.id, is_admin=test_user.is_admin)


@pytest.fixture
async def admin_token(test_admin):
    """Generate access token for test admin."""
    from app.core.security import create_access_token

    return create_access_token(subject=test_admin.id, is_admin=test_admin.is_admin)
