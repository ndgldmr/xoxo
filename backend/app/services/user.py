"""
User service containing business logic.
"""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AlreadyExistsException, NotFoundException
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    """
    Service layer for User business logic.
    Orchestrates repositories and implements domain logic.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize user service.

        Args:
            db: Async database session
        """
        self.db = db
        self.repository = UserRepository(db)

    async def get_user(self, user_id: int) -> User:
        """
        Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User instance

        Raises:
            NotFoundException: If user not found
        """
        user = await self.repository.get(user_id)
        if not user:
            raise NotFoundException(f"User with id {user_id} not found")
        return user

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email.

        Args:
            email: User's email address

        Returns:
            User instance or None
        """
        return await self.repository.get_by_email(email)

    async def get_users(self, *, skip: int = 0, limit: int = 100) -> list[User]:
        """
        Get all users with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of users
        """
        return await self.repository.get_multi(skip=skip, limit=limit)

    async def get_active_users(self, *, skip: int = 0, limit: int = 100) -> list[User]:
        """
        Get active users with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of active users
        """
        return await self.repository.get_active_users(skip=skip, limit=limit)

    async def create_user(self, user_data: UserCreate) -> User:
        """
        Create a new user.

        Args:
            user_data: User creation data

        Returns:
            Created user instance

        Raises:
            AlreadyExistsException: If email already exists
        """
        # Business logic: Check if email already exists
        if await self.repository.email_exists(user_data.email):
            raise AlreadyExistsException(f"User with email {user_data.email} already exists")

        # Additional business logic can go here
        # For example: validate phone format, send welcome email, etc.

        return await self.repository.create(obj_in=user_data)

    async def update_user(self, user_id: int, user_data: UserUpdate) -> User:
        """
        Update an existing user.

        Args:
            user_id: User ID
            user_data: User update data

        Returns:
            Updated user instance

        Raises:
            NotFoundException: If user not found
            AlreadyExistsException: If email change conflicts with existing user
        """
        # Get existing user
        user = await self.get_user(user_id)

        # Business logic: If email is being changed, check it doesn't exist
        if user_data.email and user_data.email != user.email:
            if await self.repository.email_exists(user_data.email):
                raise AlreadyExistsException(
                    f"User with email {user_data.email} already exists"
                )

        # Additional business logic can go here
        # For example: audit log, notification, etc.

        return await self.repository.update(db_obj=user, obj_in=user_data)

    async def delete_user(self, user_id: int) -> User:
        """
        Delete a user.

        Args:
            user_id: User ID

        Returns:
            Deleted user instance

        Raises:
            NotFoundException: If user not found
        """
        user = await self.get_user(user_id)

        # Business logic: Could implement soft delete by setting is_active=False
        # For now, we'll do hard delete
        deleted_user = await self.repository.delete(id=user_id)

        if not deleted_user:
            raise NotFoundException(f"User with id {user_id} not found")

        return deleted_user

    async def deactivate_user(self, user_id: int) -> User:
        """
        Deactivate a user (soft delete).

        Args:
            user_id: User ID

        Returns:
            Deactivated user instance

        Raises:
            NotFoundException: If user not found
        """
        user = await self.get_user(user_id)
        return await self.repository.update(
            db_obj=user, obj_in=UserUpdate(is_active=False)
        )
