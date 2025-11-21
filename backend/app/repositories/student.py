"""
Student repository for data access operations.
"""

from typing import Optional

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.student import Student
from app.repositories.base import BaseRepository
from app.schemas.student import StudentCreate, StudentUpdate


class StudentRepository(BaseRepository[Student, StudentCreate, StudentUpdate]):
    """
    Repository for Student model.
    Extends BaseRepository with Student-specific queries.
    """

    def __init__(self, db: AsyncSession):
        """Initialize student repository."""
        super().__init__(Student, db)

    async def get_by_email(self, email: str) -> Optional[Student]:
        """
        Get student by email address.

        Args:
            email: Student's email address

        Returns:
            Student instance or None if not found
        """
        stmt = select(Student).where(Student.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone_number: str) -> Optional[Student]:
        """
        Get student by phone number.

        Args:
            phone_number: Student's phone number

        Returns:
            Student instance or None if not found
        """
        stmt = select(Student).where(Student.phone_number == phone_number)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_students(
        self, *, skip: int = 0, limit: int = 100
    ) -> list[Student]:
        """
        Get all active students.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of active students
        """
        stmt = (
            select(Student).where(Student.is_active).offset(skip).limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_with_filters(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = False,
        email: Optional[str] = None,
        name: Optional[str] = None,
        country: Optional[str] = None,
    ) -> list[Student]:
        """
        Get students with optional filters.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            active_only: If True, return only active students
            email: Filter by email (exact match, case-insensitive)
            name: Filter by first or last name (substring match, case-insensitive)
            country: Filter by country (exact match, case-insensitive)

        Returns:
            List of students matching filters
        """
        stmt = select(Student)

        # Apply filters
        if active_only:
            stmt = stmt.where(Student.is_active)

        if email:
            stmt = stmt.where(Student.email.ilike(email))

        if name:
            # Search in both first_name and last_name
            search_pattern = f"%{name}%"
            stmt = stmt.where(
                or_(
                    Student.first_name.ilike(search_pattern),
                    Student.last_name.ilike(search_pattern),
                )
            )

        if country:
            stmt = stmt.where(Student.country.ilike(country))

        # Apply pagination
        stmt = stmt.offset(skip).limit(limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def email_exists(self, email: str, exclude_id: Optional[int] = None) -> bool:
        """
        Check if email already exists in database.

        Args:
            email: Email address to check
            exclude_id: Optional student ID to exclude from check (for updates)

        Returns:
            True if email exists, False otherwise
        """
        stmt = select(Student).where(Student.email == email)

        if exclude_id is not None:
            stmt = stmt.where(Student.id != exclude_id)

        result = await self.db.execute(stmt)
        student = result.scalar_one_or_none()
        return student is not None

    async def phone_exists(
        self, phone_number: str, exclude_id: Optional[int] = None
    ) -> bool:
        """
        Check if phone number already exists in database.

        Args:
            phone_number: Phone number to check
            exclude_id: Optional student ID to exclude from check (for updates)

        Returns:
            True if phone number exists, False otherwise
        """
        stmt = select(Student).where(Student.phone_number == phone_number)

        if exclude_id is not None:
            stmt = stmt.where(Student.id != exclude_id)

        result = await self.db.execute(stmt)
        student = result.scalar_one_or_none()
        return student is not None
