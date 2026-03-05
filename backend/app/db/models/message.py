"""Message model for storing pre-generated daily messages."""
import datetime

from sqlalchemy import Date, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base, TimestampMixin

LEVELS = ["beginner", "intermediate", "advanced"]


class Message(Base, TimestampMixin):
    """
    Pre-generated daily message for a specific English level.

    One row per (date, level) — upserted by the generate job and read by the send job.
    """

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    theme: Mapped[str] = mapped_column(String(255), nullable=False)
    template_params: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False
    )
    formatted_message: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        UniqueConstraint("date", "level", name="uq_messages_date_level"),
    )

    def __repr__(self) -> str:
        return f"<Message(date={self.date}, level='{self.level}', theme='{self.theme}')>"
