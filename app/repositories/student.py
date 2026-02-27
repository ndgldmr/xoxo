"""Student repository for database operations."""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models.student import Student


class StudentRepository:
    """Repository for Student model CRUD operations."""

    def __init__(self, session: Session):
        """
        Initialize the repository with a database session.

        Args:
            session: SQLAlchemy database session
        """
        self.session = session

    def create(
        self,
        phone_number: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        english_level: str = "beginner",
        whatsapp_messages: bool = True,
    ) -> Student:
        """
        Create a new student.

        Args:
            phone_number: Phone number in E.164 format (e.g., "+5511999999999")
            first_name: Student's first name
            last_name: Student's last name
            english_level: English proficiency level ("beginner" or "intermediate")
            whatsapp_messages: Whether the student has opted in to receive messages

        Returns:
            Created Student instance
        """
        student = Student(
            phone_number=phone_number,
            first_name=first_name,
            last_name=last_name,
            english_level=english_level,
            whatsapp_messages=whatsapp_messages,
            is_active=True,
        )
        self.session.add(student)
        self.session.flush()  # Flush to get any DB-generated values
        return student

    def get_by_phone(self, phone_number: str) -> Optional[Student]:
        """
        Get a student by phone number.

        Args:
            phone_number: Phone number to search for

        Returns:
            Student instance if found, None otherwise
        """
        return self.session.query(Student).filter(Student.phone_number == phone_number).first()

    def get_active_subscribers(self, level: Optional[str] = None) -> List[Student]:
        """
        Get all active students who are subscribed to WhatsApp messages.

        Args:
            level: Optional filter by English level ("beginner" or "intermediate")

        Returns:
            List of Student instances
        """
        query = self.session.query(Student).filter(
            Student.is_active == True,  # noqa: E712
            Student.whatsapp_messages == True,  # noqa: E712
        )

        if level:
            query = query.filter(Student.english_level == level)

        return query.all()

    def update_whatsapp_opt_out(self, phone_number: str) -> bool:
        """
        Mark a student as opted out of WhatsApp messages.

        This is called when a student sends a "STOP" message via WhatsApp.

        Args:
            phone_number: Phone number of the student to opt out

        Returns:
            True if student was found and updated, False otherwise
        """
        student = self.get_by_phone(phone_number)
        if student:
            student.whatsapp_messages = False
            self.session.flush()
            return True
        return False

    def update_whatsapp_opt_in(self, phone_number: str) -> bool:
        """
        Mark a student as opted in to WhatsApp messages.

        This is called when a student sends a "START" message via WhatsApp.

        Args:
            phone_number: Phone number of the student to opt in

        Returns:
            True if student was found and updated, False otherwise
        """
        student = self.get_by_phone(phone_number)
        if student:
            student.whatsapp_messages = True
            self.session.flush()
            return True
        return False

    def deactivate(self, phone_number: str) -> bool:
        """
        Deactivate a student (soft delete).

        Args:
            phone_number: Phone number of the student to deactivate

        Returns:
            True if student was found and deactivated, False otherwise
        """
        student = self.get_by_phone(phone_number)
        if student:
            student.is_active = False
            self.session.flush()
            return True
        return False

    def delete(self, phone_number: str) -> bool:
        """
        Hard delete a student from the database.

        Args:
            phone_number: Phone number of the student to delete

        Returns:
            True if student was found and deleted, False otherwise
        """
        student = self.get_by_phone(phone_number)
        if student:
            self.session.delete(student)
            self.session.flush()
            return True
        return False

    def update(self, phone_number: str, updates: dict) -> Optional[Student]:
        """
        Update a student's fields.

        Args:
            phone_number: Phone number of the student to update
            updates: Dict of field names to new values (only provided fields are changed)

        Returns:
            Updated Student instance if found, None otherwise
        """
        student = self.get_by_phone(phone_number)
        if not student:
            return None
        for key, value in updates.items():
            if hasattr(student, key):
                setattr(student, key, value)
        self.session.flush()
        return student

    def reactivate(self, phone_number: str) -> bool:
        """
        Reactivate a previously deactivated student.

        Args:
            phone_number: Phone number of the student to reactivate

        Returns:
            True if student was found and reactivated, False otherwise
        """
        student = self.get_by_phone(phone_number)
        if student:
            student.is_active = True
            self.session.flush()
            return True
        return False

    def list_all(self, include_inactive: bool = False) -> List[Student]:
        """
        List all students.

        Args:
            include_inactive: Whether to include inactive students

        Returns:
            List of Student instances
        """
        query = self.session.query(Student)
        if not include_inactive:
            query = query.filter(Student.is_active == True)  # noqa: E712
        return query.all()
