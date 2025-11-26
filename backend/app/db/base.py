"""
Import all models here so Alembic can detect them.
This file is imported by alembic/env.py to ensure all models are registered.
"""

from app.db.base_class import Base  # noqa: F401

# Import all models here
from app.models.user import User  # noqa: F401
from app.models.student import Student  # noqa: F401
from app.models.message import Message  # noqa: F401

# Add new models here as they are created
# from app.models.volunteer import Volunteer  # noqa: F401
# from app.models.program import Program  # noqa: F401
