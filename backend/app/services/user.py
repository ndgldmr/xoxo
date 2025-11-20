"""
User service containing business logic.
"""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AlreadyExistsException, NotFoundException, ValidationException
from app.core.security import hash_password, validate_password_strength
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
        Create a new user with hashed password.

        Args:
            user_data: User creation data (includes plain password)

        Returns:
            Created user instance

        Raises:
            AlreadyExistsException: If email already exists
            ValidationException: If password doesn't meet security requirements
        """
        # Business logic: Check if email already exists
        if await self.repository.email_exists(user_data.email):
            raise AlreadyExistsException(f"User with email {user_data.email} already exists")

        # Validate password strength
        is_valid, error_message = validate_password_strength(user_data.password)
        if not is_valid:
            raise ValidationException(error_message or "Password does not meet security requirements")

        # Hash the password
        hashed_password = hash_password(user_data.password)

        # Create user data dict with hashed password
        # We need to exclude the plain password and add hashed_password
        user_dict = user_data.model_dump(exclude={"password"})
        user_dict["hashed_password"] = hashed_password

        # Create user via repository with modified data
        # We pass a dict instead of the schema since we've modified the data
        from app.schemas.user import UserInDB
        db_obj = self.repository.model(**user_dict)
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)

        # Additional business logic can go here
        # For example: send welcome email, audit log, etc.

        return db_obj

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
