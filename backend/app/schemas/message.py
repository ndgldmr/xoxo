"""
Pydantic schemas for Message model.
These schemas handle request validation and response serialization.
"""

import re
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# Shared properties
class MessageBase(BaseModel):
    """Base Message schema with shared properties."""

    message_date: date = Field(..., description="Logical calendar day for this message")
    category: Optional[str] = Field(
        None,
        max_length=100,
        description="Optional semantic category (e.g., everyday_phrases, black_history_month)",
    )
    subject: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="English word or phrase (must be globally unique)",
    )
    definition: str = Field(..., min_length=1, description="Canonical English definition")
    example: str = Field(..., min_length=1, description="English example usage")
    usage_tips: str = Field(..., min_length=1, description="English usage tips")
    cultural_notes: Optional[str] = Field(
        None, description="Optional cultural/context notes in English"
    )
    is_active: bool = Field(default=True, description="Whether message is active")


# Properties to receive on creation
class MessageCreate(MessageBase):
    """Schema for creating a new message (admin-only operation)."""

    @field_validator("category")
    @classmethod
    def normalize_category(cls, v: Optional[str]) -> Optional[str]:
        """
        Normalize category to slug format (lowercase, underscores).
        Examples: "Black History Month" -> "black_history_month"
                  "Everyday Phrases" -> "everyday_phrases"
        """
        if v is None:
            return v

        # Convert to lowercase, replace spaces/hyphens with underscores, remove special chars
        normalized = v.lower().strip()
        normalized = re.sub(r"[\s\-]+", "_", normalized)  # spaces/hyphens -> underscores
        normalized = re.sub(r"[^a-z0-9_]", "", normalized)  # remove non-alphanumeric except _
        normalized = re.sub(r"_+", "_", normalized)  # collapse multiple underscores
        normalized = normalized.strip("_")  # remove leading/trailing underscores

        if not normalized:
            raise ValueError("Category must contain at least one alphanumeric character")

        return normalized

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, v: str) -> str:
        """Validate subject is non-empty after stripping whitespace."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("Subject cannot be empty or only whitespace")
        return stripped

    @field_validator("definition", "example", "usage_tips")
    @classmethod
    def validate_required_fields(cls, v: str) -> str:
        """Validate required content fields are non-empty after stripping."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("This field cannot be empty or only whitespace")
        return stripped

    @field_validator("cultural_notes")
    @classmethod
    def validate_cultural_notes(cls, v: Optional[str]) -> Optional[str]:
        """Validate cultural_notes if provided, otherwise allow None."""
        if v is None:
            return v
        stripped = v.strip()
        # Allow empty string to be converted to None
        return stripped if stripped else None


# Properties to receive on update
class MessageUpdate(BaseModel):
    """Schema for updating an existing message. All fields are optional (PATCH-style)."""

    message_date: Optional[date] = Field(
        None, description="Logical calendar day for this message"
    )
    category: Optional[str] = Field(
        None,
        max_length=100,
        description="Optional semantic category (e.g., everyday_phrases, black_history_month)",
    )
    subject: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="English word or phrase (must be globally unique)",
    )
    definition: Optional[str] = Field(
        None, min_length=1, description="Canonical English definition"
    )
    example: Optional[str] = Field(None, min_length=1, description="English example usage")
    usage_tips: Optional[str] = Field(None, min_length=1, description="English usage tips")
    cultural_notes: Optional[str] = Field(
        None, description="Optional cultural/context notes in English"
    )
    is_active: Optional[bool] = Field(None, description="Whether message is active")

    @field_validator("category")
    @classmethod
    def normalize_category(cls, v: Optional[str]) -> Optional[str]:
        """Normalize category to slug format if provided."""
        if v is None:
            return v

        normalized = v.lower().strip()
        normalized = re.sub(r"[\s\-]+", "_", normalized)
        normalized = re.sub(r"[^a-z0-9_]", "", normalized)
        normalized = re.sub(r"_+", "_", normalized)
        normalized = normalized.strip("_")

        if not normalized:
            raise ValueError("Category must contain at least one alphanumeric character")

        return normalized

    @field_validator("subject", "definition", "example", "usage_tips")
    @classmethod
    def validate_non_empty_if_provided(cls, v: Optional[str]) -> Optional[str]:
        """Validate that if field is provided, it's not empty after stripping."""
        if v is None:
            return v
        stripped = v.strip()
        if not stripped:
            raise ValueError("Field cannot be empty or only whitespace if provided")
        return stripped

    @field_validator("cultural_notes")
    @classmethod
    def validate_cultural_notes(cls, v: Optional[str]) -> Optional[str]:
        """Validate cultural_notes if provided."""
        if v is None:
            return v
        stripped = v.strip()
        return stripped if stripped else None


# Properties shared by models stored in DB
class MessageInDBBase(MessageBase):
    """Base schema for Message data from database."""

    id: int = Field(..., description="Message ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


# Properties to return to client
class Message(MessageInDBBase):
    """
    Message schema for API responses.
    This is what clients receive when fetching message data.
    """

    pass
