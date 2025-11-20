"""
Authentication endpoints.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user, get_db
from app.core.exceptions import UnauthorizedException
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse
from app.schemas.user import User as UserSchema
from app.services.auth import AuthService


router = APIRouter()


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login",
    description="Authenticate with email and password to receive access and refresh tokens",
)
async def login(
    login_data: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """
    Authenticate user and return JWT tokens.

    - **email**: User's email address
    - **password**: User's password

    Returns access and refresh tokens for subsequent authenticated requests.
    """
    auth_service = AuthService(db)

    try:
        tokens = await auth_service.login(
            email=login_data.email,
            password=login_data.password,
        )
        return tokens

    except UnauthorizedException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description="Use refresh token to obtain new access and refresh tokens",
)
async def refresh_token(
    refresh_data: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """
    Refresh access token using a valid refresh token.

    - **refresh_token**: Valid JWT refresh token

    Returns new access and refresh tokens.
    """
    auth_service = AuthService(db)

    try:
        tokens = await auth_service.refresh_access_token(
            refresh_token=refresh_data.refresh_token
        )
        return tokens

    except UnauthorizedException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get(
    "/me",
    response_model=UserSchema,
    status_code=status.HTTP_200_OK,
    summary="Get current user",
    description="Get the profile of the currently authenticated user",
)
async def get_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """
    Get current authenticated user's profile.

    Requires valid access token in Authorization header.
    """
    return current_user
