"""Rename student fields: proficiency_level to english_level, wants_daily_message to whatsapp_messages, remove daily_message_time_local

Revision ID: 6904e90a9791
Revises: 336052308553
Create Date: 2025-12-01 18:46:55.978104

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '6904e90a9791'
down_revision: Union[str, None] = '336052308553'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename proficiency_level to english_level
    op.alter_column('students', 'proficiency_level', new_column_name='english_level')

    # Rename wants_daily_message to whatsapp_messages
    op.alter_column('students', 'wants_daily_message', new_column_name='whatsapp_messages')

    # Update comment for whatsapp_messages
    op.alter_column('students', 'whatsapp_messages',
                    comment='Whether student wants daily AI-generated WhatsApp messages',
                    existing_type=sa.Boolean(),
                    existing_nullable=False)

    # Drop daily_message_time_local column (no longer needed)
    op.drop_column('students', 'daily_message_time_local')


def downgrade() -> None:
    # Re-add daily_message_time_local column
    op.add_column('students', sa.Column('daily_message_time_local', postgresql.TIME(),
                                        autoincrement=False, nullable=True,
                                        comment="Preferred time for daily message in student's local timezone"))

    # Rename whatsapp_messages back to wants_daily_message
    op.alter_column('students', 'whatsapp_messages',
                    comment='Whether student wants daily AI-generated messages',
                    existing_type=sa.Boolean(),
                    existing_nullable=False)
    op.alter_column('students', 'whatsapp_messages', new_column_name='wants_daily_message')

    # Rename english_level back to proficiency_level
    op.alter_column('students', 'english_level', new_column_name='proficiency_level')
