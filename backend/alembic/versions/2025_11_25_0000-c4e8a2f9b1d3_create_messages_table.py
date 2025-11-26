"""Create messages table

Revision ID: c4e8a2f9b1d3
Revises: 336052308553
Create Date: 2025-11-25 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c4e8a2f9b1d3"
down_revision: Union[str, None] = "336052308553"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create messages table for Message of the Day feature."""
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "message_date",
            sa.Date(),
            nullable=False,
            comment="Logical calendar day this message belongs to (one message per day)",
        ),
        sa.Column(
            "category",
            sa.String(length=100),
            nullable=True,
            comment="Optional semantic category (e.g., everyday_phrases, black_history_month)",
        ),
        sa.Column(
            "subject",
            sa.String(length=255),
            nullable=False,
            comment="English word or phrase (must be globally unique)",
        ),
        sa.Column(
            "definition",
            sa.Text(),
            nullable=False,
            comment="Canonical English definition",
        ),
        sa.Column(
            "example",
            sa.Text(),
            nullable=False,
            comment="English example usage",
        ),
        sa.Column(
            "usage_tips",
            sa.Text(),
            nullable=False,
            comment="English usage tips",
        ),
        sa.Column(
            "cultural_notes",
            sa.Text(),
            nullable=True,
            comment="Optional cultural/context notes in English",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            comment="Soft delete flag",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index(op.f("ix_messages_id"), "messages", ["id"], unique=False)
    op.create_index(
        op.f("ix_messages_message_date"), "messages", ["message_date"], unique=True
    )
    op.create_index(
        op.f("ix_messages_category"), "messages", ["category"], unique=False
    )
    op.create_index(
        op.f("ix_messages_subject"), "messages", ["subject"], unique=True
    )


def downgrade() -> None:
    """Drop messages table."""
    op.drop_index(op.f("ix_messages_subject"), table_name="messages")
    op.drop_index(op.f("ix_messages_category"), table_name="messages")
    op.drop_index(op.f("ix_messages_message_date"), table_name="messages")
    op.drop_index(op.f("ix_messages_id"), table_name="messages")
    op.drop_table("messages")
