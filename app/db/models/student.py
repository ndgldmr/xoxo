"""Student model for managing WhatsApp message recipients."""
from typing import Optional

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Student(Base, TimestampMixin):
    """
    Student model representing a WhatsApp message recipient.

    Attributes:
        phone_number: Unique phone number in E.164 format (e.g., "+5511999999999")
        first_name: Student's first name (optional)
        last_name: Student's last name (optional)
        english_level: Student's English proficiency level ("beginner" or "intermediate")
        whatsapp_messages: Whether the student has opted in to receive WhatsApp messages
        is_active: Whether the student is active (for soft deletes)
        created_at: Timestamp when the student was created (from TimestampMixin)
        updated_at: Timestamp when the student was last updated (from TimestampMixin)
    """

    __tablename__ = "students"

    phone_number: Mapped[str] = mapped_column(String(20), primary_key=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    english_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default="beginner"
    )
    whatsapp_messages: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        """String representation of the student."""
        return (
            f"<Student(phone_number='{self.phone_number}', "
            f"name='{self.first_name} {self.last_name}', "
            f"level='{self.english_level}', "
            f"active={self.is_active})>"
        )
