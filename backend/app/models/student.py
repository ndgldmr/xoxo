"""
Student ORM model.
"""

from datetime import time
from typing import Optional

from sqlalchemy import String, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base, TimestampMixin


class Student(Base, TimestampMixin):
    """
    Student model representing students tracked in the system.
    Students are NOT system users (no authentication).
    """

    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone_number: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False
    )
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    proficiency_level: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="English proficiency: beginner, intermediate, advanced"
    )
    native_language: Mapped[str] = mapped_column(
        String(10), nullable=False, default="pt-BR", comment="Student's native language (e.g., pt-BR)"
    )
    wants_daily_message: Mapped[bool] = mapped_column(
        default=False, nullable=False, comment="Whether student wants daily AI-generated messages"
    )
    daily_message_time_local: Mapped[Optional[time]] = mapped_column(
        Time, nullable=True, comment="Preferred time for daily message in student's local timezone"
    )
    timezone: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="IANA timezone (e.g., America/Sao_Paulo)"
    )

    def __repr__(self) -> str:
        return f"<Student(id={self.id}, email='{self.email}', name='{self.first_name} {self.last_name}')>"

    @property
    def full_name(self) -> str:
        """Get student's full name."""
        return f"{self.first_name} {self.last_name}"
