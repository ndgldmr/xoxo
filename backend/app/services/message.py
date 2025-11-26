"""
Message service containing business logic.
"""

from datetime import date
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AlreadyExistsException, NotFoundException
from app.models.message import Message
from app.repositories.message import MessageRepository
from app.schemas.message import MessageCreate, MessageUpdate


class MessageService:
    """
    Service layer for Message business logic.
    Orchestrates repositories and implements domain logic.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize message service.

        Args:
            db: Async database session
        """
        self.db = db
        self.repository = MessageRepository(db)

    def _normalize_subject(self, subject: str) -> str:
        """
        Normalize subject (strip whitespace).

        Args:
            subject: Raw subject

        Returns:
            Normalized subject
        """
        return subject.strip()

    async def get_message(self, message_id: int) -> Message:
        """
        Get message by ID.

        Args:
            message_id: Message ID

        Returns:
            Message instance

        Raises:
            NotFoundException: If message not found
        """
        message = await self.repository.get(message_id)
        if not message:
            raise NotFoundException(f"Message with id {message_id} not found")
        return message

    async def get_message_by_date(self, message_date: date) -> Optional[Message]:
        """
        Get message by date.

        Args:
            message_date: The calendar date of the message

        Returns:
            Message instance or None
        """
        return await self.repository.get_by_date(message_date)

    async def get_message_by_subject(self, subject: str) -> Optional[Message]:
        """
        Get message by subject.

        Args:
            subject: The English word/phrase

        Returns:
            Message instance or None
        """
        normalized_subject = self._normalize_subject(subject)
        return await self.repository.get_by_subject(normalized_subject)

    async def get_messages(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = True,
        category: Optional[str] = None,
        message_date: Optional[date] = None,
    ) -> list[Message]:
        """
        Get all messages with pagination and optional filters.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            active_only: If True, return only active messages (default: True)
            category: Filter by category (exact match)
            message_date: Filter by message_date (exact match)

        Returns:
            List of messages, ordered by message_date descending
        """
        return await self.repository.get_with_filters(
            skip=skip,
            limit=limit,
            active_only=active_only,
            category=category,
            message_date=message_date,
        )

    async def create_message(self, message_data: MessageCreate) -> Message:
        """
        Create a new message.

        Args:
            message_data: Message creation data

        Returns:
            Created message instance

        Raises:
            AlreadyExistsException: If subject or message_date already exists
        """
        # Normalize subject
        normalized_subject = self._normalize_subject(message_data.subject)

        # Business logic: Check if subject already exists
        if await self.repository.subject_exists(normalized_subject):
            raise AlreadyExistsException(
                f"Message with subject '{normalized_subject}' already exists"
            )

        # Business logic: Check if date already exists
        if await self.repository.date_exists(message_data.message_date):
            raise AlreadyExistsException(
                f"Message for date {message_data.message_date} already exists. "
                "Only one message per day is allowed."
            )

        # Create message data dict with normalized subject
        message_dict = message_data.model_dump()
        message_dict["subject"] = normalized_subject

        # Create message via repository
        db_obj = self.repository.model(**message_dict)
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)

        return db_obj

    async def update_message(
        self, message_id: int, message_data: MessageUpdate
    ) -> Message:
        """
        Update an existing message.

        Args:
            message_id: Message ID
            message_data: Message update data

        Returns:
            Updated message instance

        Raises:
            NotFoundException: If message not found
            AlreadyExistsException: If subject or message_date change conflicts with existing message
        """
        # Get existing message
        message = await self.get_message(message_id)

        # Normalize subject if being changed
        if message_data.subject:
            normalized_subject = self._normalize_subject(message_data.subject)
            if normalized_subject != message.subject:
                if await self.repository.subject_exists(
                    normalized_subject, exclude_id=message_id
                ):
                    raise AlreadyExistsException(
                        f"Message with subject '{normalized_subject}' already exists"
                    )
                message_data.subject = normalized_subject

        # Business logic: Check if message_date is being changed
        if message_data.message_date:
            if message_data.message_date != message.message_date:
                if await self.repository.date_exists(
                    message_data.message_date, exclude_id=message_id
                ):
                    raise AlreadyExistsException(
                        f"Message for date {message_data.message_date} already exists. "
                        "Only one message per day is allowed."
                    )

        return await self.repository.update(db_obj=message, obj_in=message_data)

    async def delete_message(self, message_id: int) -> Message:
        """
        Soft delete a message by setting is_active to False.

        Args:
            message_id: Message ID

        Returns:
            Deactivated message instance

        Raises:
            NotFoundException: If message not found
        """
        message = await self.get_message(message_id)

        # Soft delete by setting is_active to False
        return await self.repository.update(
            db_obj=message, obj_in=MessageUpdate(is_active=False)
        )

    async def activate_message(self, message_id: int) -> Message:
        """
        Activate a message by setting is_active to True.

        Args:
            message_id: Message ID

        Returns:
            Activated message instance

        Raises:
            NotFoundException: If message not found
        """
        message = await self.get_message(message_id)

        return await self.repository.update(
            db_obj=message, obj_in=MessageUpdate(is_active=True)
        )
