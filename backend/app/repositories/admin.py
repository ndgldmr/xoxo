"""Admin repository for database operations."""
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models.admin import Admin


class AdminRepository:
    """Repository for Admin model operations."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_email(self, email: str) -> Optional[Admin]:
        """Return the admin with the given email, or None."""
        return self.session.query(Admin).filter(Admin.email == email).first()

    def create(self, email: str, hashed_password: str) -> Admin:
        """Create and flush a new admin record."""
        admin = Admin(email=email, hashed_password=hashed_password)
        self.session.add(admin)
        self.session.flush()
        return admin

    def count(self) -> int:
        """Return the total number of admin records (used by CLI first-run detection)."""
        return self.session.query(Admin).count()
