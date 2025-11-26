"""
Pydantic schemas for AI-powered message generation.
These schemas handle AI output validation and generation request handling.
"""

from datetime import date

from pydantic import BaseModel, Field, field_validator


class MessageGenerationPayload(BaseModel):
    """
    Schema representing AI-generated message content.
    This is the structured output we expect from the LLM.
    """

    subject: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="English word or phrase (must be globally unique)",
    )
    definition: str = Field(..., min_length=1, description="Canonical English definition")
    example: str = Field(..., min_length=1, description="English example usage")
    usage_tips: str = Field(..., min_length=1, description="English usage tips")
    cultural_notes: str | None = Field(
        None, description="Optional cultural/context notes in English"
    )

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
    def validate_cultural_notes(cls, v: str | None) -> str | None:
        """Validate cultural_notes if provided, otherwise allow None."""
        if v is None:
            return v
        stripped = v.strip()
        return stripped if stripped else None


class MessageGenerateRequest(BaseModel):
    """
    Schema for requesting AI-powered message generation.
    Used by the POST /messages/generate endpoint.
    """

    message_date: date = Field(
        ..., description="Target date for the generated message (YYYY-MM-DD)"
    )
    category: str | None = Field(
        None,
        max_length=100,
        description="Optional semantic category (e.g., everyday_phrases, black_history_month)",
    )

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str | None) -> str | None:
        """Validate category if provided."""
        if v is None:
            return v
        stripped = v.strip()
        if not stripped:
            raise ValueError("Category cannot be empty if provided")
        return stripped


class AIGenerationError(BaseModel):
    """
    Schema for AI generation error responses.
    Provides structured error information to admins without exposing sensitive details.
    """

    error_type: str = Field(
        ...,
        description="Error type code (e.g., AI_TIMEOUT, AI_JSON_PARSE_ERROR, AI_SUBJECT_CONFLICT)",
    )
    message: str = Field(..., description="Human-readable error message")
    details: dict | None = Field(
        None, description="Optional additional context (non-sensitive)"
    )
