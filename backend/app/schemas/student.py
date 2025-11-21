"""
Pydantic schemas for Student model.
These schemas handle request validation and response serialization.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# Shared properties
class StudentBase(BaseModel):
    """Base Student schema with shared properties."""

    email: EmailStr = Field(..., description="Student's email address")
    first_name: str = Field(..., min_length=1, max_length=100, description="First name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Last name")
    phone_number: str = Field(
        ...,
        min_length=10,
        max_length=20,
        description="Phone number in E.164 format (e.g., +17038590314)",
    )
    country: Optional[str] = Field(None, max_length=100, description="Country")
    is_active: bool = Field(default=True, description="Whether student is active")


# Properties to receive on creation
class StudentCreate(StudentBase):
    """Schema for creating a new student (admin-only operation)."""

    @field_validator("phone_number")
    @classmethod
    def validate_phone_e164(cls, v: str) -> str:
        """
        Validate phone number is in E.164 format.
        E.164 format: +[country code][number] (e.g., +17038590314)
        Max 15 digits total including country code.
        """
        import re

        # E.164 regex: + followed by 1-15 digits
        e164_pattern = r"^\+[1-9]\d{1,14}$"

        if not re.match(e164_pattern, v):
            raise ValueError(
                "Phone number must be in E.164 format: "
                "+[country code][number] with 1-15 total digits (e.g., +17038590314)"
            )

        return v


# Properties to receive on update
class StudentUpdate(BaseModel):
    """Schema for updating an existing student. All fields are optional."""

    email: Optional[EmailStr] = Field(None, description="Student's email address")
    first_name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="First name"
    )
    last_name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Last name"
    )
    phone_number: Optional[str] = Field(
        None, min_length=10, max_length=20, description="Phone number in E.164 format"
    )
    country: Optional[str] = Field(None, max_length=100, description="Country")
    is_active: Optional[bool] = Field(None, description="Whether student is active")

    @field_validator("phone_number")
    @classmethod
    def validate_phone_e164(cls, v: Optional[str]) -> Optional[str]:
        """Validate phone number is in E.164 format if provided."""
        if v is None:
            return v

        import re

        e164_pattern = r"^\+[1-9]\d{1,14}$"

        if not re.match(e164_pattern, v):
            raise ValueError(
                "Phone number must be in E.164 format: "
                "+[country code][number] with 1-15 total digits (e.g., +17038590314)"
            )

        return v


# Properties shared by models stored in DB
class StudentInDBBase(StudentBase):
    """Base schema for Student data from database."""

    id: int = Field(..., description="Student ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


# Properties to return to client
class Student(StudentInDBBase):
    """
    Student schema for API responses.
    This is what clients receive when fetching student data.
    """

    pass
