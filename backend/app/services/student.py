"""
Student service containing business logic.
"""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AlreadyExistsException, NotFoundException
from app.models.student import Student
from app.repositories.student import StudentRepository
from app.schemas.student import StudentCreate, StudentUpdate


class StudentService:
    """
    Service layer for Student business logic.
    Orchestrates repositories and implements domain logic.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize student service.

        Args:
            db: Async database session
        """
        self.db = db
        self.repository = StudentRepository(db)

    def _normalize_email(self, email: str) -> str:
        """
        Normalize email address.

        Args:
            email: Raw email address

        Returns:
            Normalized email (lowercase, stripped)
        """
        return email.lower().strip()

    def _normalize_phone(self, phone: str) -> str:
        """
        Normalize phone number.

        Args:
            phone: Raw phone number

        Returns:
            Normalized phone number (stripped)
        """
        return phone.strip()

    async def get_student(self, student_id: int) -> Student:
        """
        Get student by ID.

        Args:
            student_id: Student ID

        Returns:
            Student instance

        Raises:
            NotFoundException: If student not found
        """
        student = await self.repository.get(student_id)
        if not student:
            raise NotFoundException(f"Student with id {student_id} not found")
        return student

    async def get_student_by_email(self, email: str) -> Optional[Student]:
        """
        Get student by email.

        Args:
            email: Student's email address

        Returns:
            Student instance or None
        """
        normalized_email = self._normalize_email(email)
        return await self.repository.get_by_email(normalized_email)

    async def get_students(
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
        Get all students with pagination and optional filters.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            active_only: If True, return only active students
            email: Filter by email (exact match, case-insensitive)
            name: Filter by first or last name (substring match)
            country: Filter by country (exact match, case-insensitive)

        Returns:
            List of students
        """
        # Normalize filters if provided
        if email:
            email = self._normalize_email(email)

        return await self.repository.get_with_filters(
            skip=skip,
            limit=limit,
            active_only=active_only,
            email=email,
            name=name,
            country=country,
        )

    async def create_student(self, student_data: StudentCreate) -> Student:
        """
        Create a new student.

        Args:
            student_data: Student creation data

        Returns:
            Created student instance

        Raises:
            AlreadyExistsException: If email or phone already exists
        """
        # Normalize email and phone
        normalized_email = self._normalize_email(student_data.email)
        normalized_phone = self._normalize_phone(student_data.phone_number)

        # Business logic: Check if email already exists
        if await self.repository.email_exists(normalized_email):
            raise AlreadyExistsException(
                f"Student with email {normalized_email} already exists"
            )

        # Business logic: Check if phone already exists
        if await self.repository.phone_exists(normalized_phone):
            raise AlreadyExistsException(
                f"Student with phone number {normalized_phone} already exists"
            )

        # Create student data dict with normalized values
        student_dict = student_data.model_dump()
        student_dict["email"] = normalized_email
        student_dict["phone_number"] = normalized_phone

        # Create student via repository
        db_obj = self.repository.model(**student_dict)
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)

        return db_obj

    async def update_student(
        self, student_id: int, student_data: StudentUpdate
    ) -> Student:
        """
        Update an existing student.

        Args:
            student_id: Student ID
            student_data: Student update data

        Returns:
            Updated student instance

        Raises:
            NotFoundException: If student not found
            AlreadyExistsException: If email or phone change conflicts with existing student
            ValueError: If wants_daily_message=True but timezone or daily_message_time_local missing
        """
        # Get existing student
        student = await self.get_student(student_id)

        # Normalize email if being changed
        if student_data.email:
            normalized_email = self._normalize_email(student_data.email)
            if normalized_email != student.email:
                if await self.repository.email_exists(
                    normalized_email, exclude_id=student_id
                ):
                    raise AlreadyExistsException(
                        f"Student with email {normalized_email} already exists"
                    )
                student_data.email = normalized_email

        # Normalize phone if being changed
        if student_data.phone_number:
            normalized_phone = self._normalize_phone(student_data.phone_number)
            if normalized_phone != student.phone_number:
                if await self.repository.phone_exists(
                    normalized_phone, exclude_id=student_id
                ):
                    raise AlreadyExistsException(
                        f"Student with phone number {normalized_phone} already exists"
                    )
                student_data.phone_number = normalized_phone

        # Business logic: If updating wants_daily_message to True, validate required fields
        if student_data.wants_daily_message is True:
            # Determine final timezone value (update value or existing value)
            final_timezone = (
                student_data.timezone
                if student_data.timezone is not None
                else student.timezone
            )
            # Determine final daily_message_time_local value
            final_time = (
                student_data.daily_message_time_local
                if student_data.daily_message_time_local is not None
                else student.daily_message_time_local
            )

            if final_timezone is None:
                raise ValueError(
                    "timezone is required when wants_daily_message is True"
                )
            if final_time is None:
                raise ValueError(
                    "daily_message_time_local is required when wants_daily_message is True"
                )

        return await self.repository.update(db_obj=student, obj_in=student_data)

    async def delete_student(self, student_id: int) -> Student:
        """
        Soft delete a student by setting is_active to False.

        Args:
            student_id: Student ID

        Returns:
            Deactivated student instance

        Raises:
            NotFoundException: If student not found
        """
        student = await self.get_student(student_id)

        # Soft delete by setting is_active to False
        return await self.repository.update(
            db_obj=student, obj_in=StudentUpdate(is_active=False)
        )

    async def activate_student(self, student_id: int) -> Student:
        """
        Activate a student by setting is_active to True.

        Args:
            student_id: Student ID

        Returns:
            Activated student instance

        Raises:
            NotFoundException: If student not found
        """
        student = await self.get_student(student_id)

        return await self.repository.update(
            db_obj=student, obj_in=StudentUpdate(is_active=True)
        )
