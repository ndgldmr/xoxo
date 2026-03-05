"""Message repository for pre-generated daily message operations."""
import datetime
from typing import List, Optional

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.db.models.message import Message


class MessageRepository:
    """Repository for Message model — upsert and retrieval by date."""

    def __init__(self, session: Session):
        self.session = session

    def upsert(
        self,
        date: datetime.date,
        level: str,
        theme: str,
        template_params: dict,
        formatted_message: str,
    ) -> Message:
        """
        Insert or replace the message for a given (date, level).

        Uses a get-then-set pattern compatible with both SQLite (dev) and
        PostgreSQL (production), since SQLite does not support ON CONFLICT DO UPDATE
        with the postgresql dialect insert.
        """
        existing = self.get_by_date_and_level(date, level)
        if existing:
            existing.theme = theme
            existing.template_params = template_params
            existing.formatted_message = formatted_message
            self.session.flush()
            return existing

        message = Message(
            date=date,
            level=level,
            theme=theme,
            template_params=template_params,
            formatted_message=formatted_message,
        )
        self.session.add(message)
        self.session.flush()
        return message

    def get_by_date(self, date: datetime.date) -> List[Message]:
        """Return all messages stored for a given date."""
        return (
            self.session.query(Message)
            .filter(Message.date == date)
            .order_by(Message.level)
            .all()
        )

    def get_by_date_and_level(
        self, date: datetime.date, level: str
    ) -> Optional[Message]:
        """Return the stored message for a specific date and level, or None."""
        return (
            self.session.query(Message)
            .filter(Message.date == date, Message.level == level)
            .first()
        )
