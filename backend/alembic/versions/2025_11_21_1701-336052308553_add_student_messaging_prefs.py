"""Add student messaging preferences

Revision ID: 336052308553
Revises: f7cef4dac3fa
Create Date: 2025-11-21 17:01:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "336052308553"
down_revision: Union[str, None] = "f7cef4dac3fa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add messaging preference columns to students table
    op.add_column(
        "students",
        sa.Column(
            "proficiency_level",
            sa.String(length=20),
            nullable=False,
            server_default="beginner",
            comment="English proficiency: beginner, intermediate, advanced",
        ),
    )
    op.add_column(
        "students",
        sa.Column(
            "native_language",
            sa.String(length=10),
            nullable=False,
            server_default="pt-BR",
            comment="Student's native language (e.g., pt-BR)",
        ),
    )
    op.add_column(
        "students",
        sa.Column(
            "wants_daily_message",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="Whether student wants daily AI-generated messages",
        ),
    )
    op.add_column(
        "students",
        sa.Column(
            "daily_message_time_local",
            sa.Time(),
            nullable=True,
            comment="Preferred time for daily message in student's local timezone",
        ),
    )
    op.add_column(
        "students",
        sa.Column(
            "timezone",
            sa.String(length=50),
            nullable=True,
            comment="IANA timezone (e.g., America/Sao_Paulo)",
        ),
    )

    # Remove server defaults after adding columns (for future inserts to use application defaults)
    op.alter_column("students", "proficiency_level", server_default=None)
    op.alter_column("students", "native_language", server_default=None)
    op.alter_column("students", "wants_daily_message", server_default=None)


def downgrade() -> None:
    # Remove messaging preference columns
    op.drop_column("students", "timezone")
    op.drop_column("students", "daily_message_time_local")
    op.drop_column("students", "wants_daily_message")
    op.drop_column("students", "native_language")
    op.drop_column("students", "proficiency_level")
