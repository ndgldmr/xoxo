"""
Unit tests for Message API endpoints.

These tests verify basic API contract and admin authorization.
Detailed business logic is tested in test_services/test_message.py.
"""

from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.message import MessageCreate, MessageUpdate


class TestMessageSchemas:
    """Tests for Message Pydantic schemas."""

    def test_message_create_valid(self):
        """Test creating valid MessageCreate schema."""
        data = MessageCreate(
            message_date=date(2025, 11, 25),
            category="Black History Month",
            subject="Perseverance",
            definition="The quality of continuing to try",
            example="She showed great perseverance",
            usage_tips="Use when describing determination",
            cultural_notes="Important in civil rights history",
        )

        # Verify category was normalized
        assert data.category == "black_history_month"
        assert data.subject == "Perseverance"

    def test_message_create_category_normalization(self):
        """Test category normalization to slug format."""
        test_cases = [
            ("Black History Month", "black_history_month"),
            ("Everyday Phrases", "everyday_phrases"),
            ("Halloween", "halloween"),
            ("BUSINESS-ENGLISH", "business_english"),
            ("Test  Multiple   Spaces", "test_multiple_spaces"),
        ]

        for input_cat, expected_cat in test_cases:
            data = MessageCreate(
                message_date=date(2025, 11, 25),
                category=input_cat,
                subject="Test",
                definition="Test definition",
                example="Test example",
                usage_tips="Test tips",
            )
            assert data.category == expected_cat

    def test_message_create_empty_subject_fails(self):
        """Test that empty subject raises ValidationError."""
        with pytest.raises(ValidationError, match="Subject cannot be empty"):
            MessageCreate(
                message_date=date(2025, 11, 25),
                subject="   ",  # Only whitespace
                definition="Test definition",
                example="Test example",
                usage_tips="Test tips",
            )

    def test_message_create_empty_required_field_fails(self):
        """Test that empty required fields raise ValidationError."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            MessageCreate(
                message_date=date(2025, 11, 25),
                subject="Test",
                definition="   ",  # Empty required field
                example="Test example",
                usage_tips="Test tips",
            )

    def test_message_create_cultural_notes_optional(self):
        """Test that cultural_notes is optional."""
        data = MessageCreate(
            message_date=date(2025, 11, 25),
            subject="Test",
            definition="Test definition",
            example="Test example",
            usage_tips="Test tips",
            cultural_notes=None,
        )
        assert data.cultural_notes is None

    def test_message_update_all_fields_optional(self):
        """Test that all fields are optional in MessageUpdate."""
        data = MessageUpdate()
        assert data.message_date is None
        assert data.category is None
        assert data.subject is None

    def test_message_update_partial(self):
        """Test updating only some fields."""
        data = MessageUpdate(
            definition="Updated definition",
            is_active=False,
        )
        assert data.definition == "Updated definition"
        assert data.is_active is False
        assert data.subject is None  # Not provided

    def test_message_update_category_normalization(self):
        """Test category normalization in update schema."""
        data = MessageUpdate(category="Test Category")
        assert data.category == "test_category"

    def test_message_update_empty_subject_fails(self):
        """Test that providing empty subject in update fails."""
        with pytest.raises(
            ValidationError, match="cannot be empty or only whitespace"
        ):
            MessageUpdate(subject="   ")

    def test_message_create_with_defaults(self):
        """Test MessageCreate with default values."""
        data = MessageCreate(
            message_date=date(2025, 11, 25),
            subject="Test",
            definition="Test definition",
            example="Test example",
            usage_tips="Test tips",
        )
        # Verify defaults
        assert data.is_active is True
        assert data.category is None
        assert data.cultural_notes is None

    def test_message_create_invalid_category(self):
        """Test that category with only special characters fails."""
        with pytest.raises(
            ValidationError, match="Category must contain at least one alphanumeric"
        ):
            MessageCreate(
                message_date=date(2025, 11, 25),
                category="@@@",  # Only special characters
                subject="Test",
                definition="Test definition",
                example="Test example",
                usage_tips="Test tips",
            )
