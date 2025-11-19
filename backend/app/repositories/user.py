"""
User repository for data access operations.
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.user import UserCreate, UserUpdate


class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
    """
    Repository for User model.
    Extends BaseRepository with User-specific queries.
    """

    def __init__(self, db: AsyncSession):
        """Initialize user repository."""
        super().__init__(User, db)

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.

        Args:
            email: User's email address

        Returns:
            User instance or None if not found
        """
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_users(self, *, skip: int = 0, limit: int = 100) -> list[User]:
        """
        Get all active users.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of active users
        """
        stmt = select(User).where(User.is_active == True).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def email_exists(self, email: str) -> bool:
        """
        Check if email already exists in database.

        Args:
            email: Email address to check

        Returns:
            True if email exists, False otherwise
        """
        user = await self.get_by_email(email)
        return user is not None
