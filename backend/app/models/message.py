"""
Message ORM model for Message of the Day (MOTD) feature.
"""

from datetime import date
from typing import Optional

from sqlalchemy import Date, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base, TimestampMixin


class Message(Base, TimestampMixin):
    """
    Message model representing daily English learning messages.

    Each message is a canonical daily message containing an English word/phrase
    with definition, examples, usage tips, and optional cultural notes.

    Future phases will integrate AI generation and WhatsApp delivery.
    """

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)

    message_date: Mapped[date] = mapped_column(
        Date,
        unique=True,
        index=True,
        nullable=False,
        comment="Logical calendar day this message belongs to (one message per day)",
    )

    category: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Optional semantic category (e.g., everyday_phrases, black_history_month)",
    )

    subject: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        comment="English word or phrase (must be globally unique)",
    )

    definition: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Canonical English definition",
    )

    example: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="English example usage",
    )

    usage_tips: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="English usage tips",
    )

    cultural_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional cultural/context notes in English",
    )

    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        comment="Soft delete flag",
    )

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, date='{self.message_date}', subject='{self.subject}')>"
