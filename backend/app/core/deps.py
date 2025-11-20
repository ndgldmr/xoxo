"""
FastAPI dependencies for dependency injection.
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.db.session import async_session_maker
from app.models.user import User
from app.services.auth import AuthService


# Security scheme for JWT Bearer tokens
security = HTTPBearer()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides an async database session.
    The session is automatically closed after the request completes.

    Usage in endpoint:
        @router.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Dependency that extracts and validates JWT token, returning the current user.

    Args:
        credentials: HTTP Bearer token credentials
        db: Database session

    Returns:
        Current authenticated User

    Raises:
        HTTPException: 401 if token is invalid or user not found

    Usage in endpoint:
        @router.get("/protected")
        async def protected_route(current_user: User = Depends(get_current_user)):
            ...
    """
    auth_service = AuthService(db)

    try:
        # Extract token from credentials
        token = credentials.credentials

        # Get user from token
        user = await auth_service.get_current_user(token)

        return user

    except UnauthorizedException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Dependency that ensures the current user is active.

    Args:
        current_user: Current authenticated user

    Returns:
        Current active User

    Raises:
        HTTPException: 403 if user is inactive

    Usage in endpoint:
        @router.get("/active-only")
        async def active_only_route(current_user: User = Depends(get_current_active_user)):
            ...
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return current_user


async def require_admin(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """
    Dependency that requires the current user to be an admin.

    Args:
        current_user: Current authenticated and active user

    Returns:
        Current admin User

    Raises:
        HTTPException: 403 if user is not an admin

    Usage in endpoint:
        @router.post("/admin-only")
        async def admin_only_route(admin_user: User = Depends(require_admin)):
            ...
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    return current_user
