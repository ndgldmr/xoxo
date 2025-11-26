"""
Message repository for data access operations.
"""

from datetime import date
from typing import Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message
from app.repositories.base import BaseRepository
from app.schemas.message import MessageCreate, MessageUpdate


class MessageRepository(BaseRepository[Message, MessageCreate, MessageUpdate]):
    """
    Repository for Message model.
    Extends BaseRepository with Message-specific queries.
    """

    def __init__(self, db: AsyncSession):
        """Initialize message repository."""
        super().__init__(Message, db)

    async def get_by_date(self, message_date: date) -> Optional[Message]:
        """
        Get message by date.

        Args:
            message_date: The calendar date of the message

        Returns:
            Message instance or None if not found
        """
        stmt = select(Message).where(Message.message_date == message_date)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_subject(self, subject: str) -> Optional[Message]:
        """
        Get message by subject.

        Args:
            subject: The English word/phrase

        Returns:
            Message instance or None if not found
        """
        stmt = select(Message).where(Message.subject == subject)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_messages(
        self, *, skip: int = 0, limit: int = 100
    ) -> list[Message]:
        """
        Get all active messages, ordered by message_date descending.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of active messages
        """
        stmt = (
            select(Message)
            .where(Message.is_active)
            .order_by(desc(Message.message_date))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_with_filters(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = True,
        category: Optional[str] = None,
        message_date: Optional[date] = None,
    ) -> list[Message]:
        """
        Get messages with optional filters, ordered by message_date descending.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            active_only: If True, return only active messages (default: True)
            category: Filter by category (exact match)
            message_date: Filter by message_date (exact match)

        Returns:
            List of messages matching filters
        """
        stmt = select(Message)

        # Apply filters
        if active_only:
            stmt = stmt.where(Message.is_active)

        if category:
            stmt = stmt.where(Message.category == category)

        if message_date:
            stmt = stmt.where(Message.message_date == message_date)

        # Order by message_date descending (most recent first)
        stmt = stmt.order_by(desc(Message.message_date))

        # Apply pagination
        stmt = stmt.offset(skip).limit(limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def subject_exists(
        self, subject: str, exclude_id: Optional[int] = None
    ) -> bool:
        """
        Check if subject already exists in database.

        Args:
            subject: Subject to check
            exclude_id: Optional message ID to exclude from check (for updates)

        Returns:
            True if subject exists, False otherwise
        """
        stmt = select(Message).where(Message.subject == subject)

        if exclude_id is not None:
            stmt = stmt.where(Message.id != exclude_id)

        result = await self.db.execute(stmt)
        message = result.scalar_one_or_none()
        return message is not None

    async def date_exists(
        self, message_date: date, exclude_id: Optional[int] = None
    ) -> bool:
        """
        Check if message_date already exists in database.

        Args:
            message_date: Date to check
            exclude_id: Optional message ID to exclude from check (for updates)

        Returns:
            True if date exists, False otherwise
        """
        stmt = select(Message).where(Message.message_date == message_date)

        if exclude_id is not None:
            stmt = stmt.where(Message.id != exclude_id)

        result = await self.db.execute(stmt)
        message = result.scalar_one_or_none()
        return message is not None
