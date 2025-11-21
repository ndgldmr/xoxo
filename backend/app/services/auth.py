"""
Authentication service layer.
Contains business logic for user authentication and token management.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedException
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
)
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.auth import TokenResponse


class AuthService:
    """Service for handling authentication operations."""

    def __init__(self, db: AsyncSession):
        """
        Initialize auth service.

        Args:
            db: Database session
        """
        self.db = db
        self.user_repo = UserRepository(db)

    async def authenticate_user(self, email: str, password: str) -> User:
        """
        Authenticate a user with email and password.

        Args:
            email: User's email address
            password: Plain text password

        Returns:
            Authenticated User model

        Raises:
            UnauthorizedException: If credentials are invalid or user is inactive
        """
        # Get user by email
        user = await self.user_repo.get_by_email(email)

        if not user:
            raise UnauthorizedException("Incorrect email or password")

        # Verify password
        if not verify_password(password, user.hashed_password):
            raise UnauthorizedException("Incorrect email or password")

        # Check if user is active
        if not user.is_active:
            raise UnauthorizedException("User account is inactive")

        return user

    async def create_tokens(self, user: User) -> TokenResponse:
        """
        Create access and refresh tokens for a user.

        Args:
            user: User model to create tokens for

        Returns:
            TokenResponse with access and refresh tokens
        """
        access_token = create_access_token(subject=user.id, is_admin=user.is_admin)

        refresh_token = create_refresh_token(subject=user.id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )

    async def login(self, email: str, password: str) -> TokenResponse:
        """
        Authenticate user and return tokens.

        Args:
            email: User's email address
            password: Plain text password

        Returns:
            TokenResponse with access and refresh tokens

        Raises:
            UnauthorizedException: If authentication fails
        """
        user = await self.authenticate_user(email, password)
        return await self.create_tokens(user)

    async def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """
        Generate new access token from refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            TokenResponse with new access and refresh tokens

        Raises:
            UnauthorizedException: If refresh token is invalid or expired
        """
        # Verify refresh token
        payload = verify_token(refresh_token, token_type="refresh")

        if not payload:
            raise UnauthorizedException("Invalid or expired refresh token")

        # Extract user ID from token
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise UnauthorizedException("Invalid token payload")

        try:
            user_id = int(user_id_str)
        except ValueError:
            raise UnauthorizedException("Invalid token payload")

        # Get user from database
        user = await self.user_repo.get(user_id)

        if not user:
            raise UnauthorizedException("User not found")

        if not user.is_active:
            raise UnauthorizedException("User account is inactive")

        # Create new tokens
        return await self.create_tokens(user)

    async def get_current_user(self, token: str) -> User:
        """
        Get current user from access token.

        Args:
            token: JWT access token

        Returns:
            User model for the authenticated user

        Raises:
            UnauthorizedException: If token is invalid or user not found
        """
        # Verify access token
        payload = verify_token(token, token_type="access")

        if not payload:
            raise UnauthorizedException("Could not validate credentials")

        # Extract user ID from token
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise UnauthorizedException("Could not validate credentials")

        try:
            user_id = int(user_id_str)
        except ValueError:
            raise UnauthorizedException("Could not validate credentials")

        # Get user from database
        user = await self.user_repo.get(user_id)

        if not user:
            raise UnauthorizedException("User not found")

        return user
