"""
Pydantic schemas for User model.
These schemas handle request validation and response serialization.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# Shared properties
class UserBase(BaseModel):
    """Base User schema with shared properties."""

    email: EmailStr = Field(..., description="User's email address")
    first_name: str = Field(..., min_length=1, max_length=100, description="First name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Last name")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    is_active: bool = Field(default=True, description="Whether user is active")
    is_admin: bool = Field(default=False, description="Whether user has admin privileges")


# Properties to receive on creation
class UserCreate(UserBase):
    """Schema for creating a new user (admin-only operation)."""

    password: str = Field(
        ...,
        min_length=12,
        description="User password (min 12 chars, must include uppercase, lowercase, digit, special char)"
    )


# Properties to receive on update
class UserUpdate(BaseModel):
    """Schema for updating an existing user. All fields are optional."""

    email: Optional[EmailStr] = Field(None, description="User's email address")
    first_name: Optional[str] = Field(None, min_length=1, max_length=100, description="First name")
    last_name: Optional[str] = Field(None, min_length=1, max_length=100, description="Last name")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    is_active: Optional[bool] = Field(None, description="Whether user is active")
    is_admin: Optional[bool] = Field(None, description="Whether user has admin privileges")


# Properties shared by models stored in DB
class UserInDBBase(UserBase):
    """Base schema for User data from database."""

    id: int = Field(..., description="User ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


# Properties to return to client
class User(UserInDBBase):
    """
    User schema for API responses.
    This is what clients receive when fetching user data.
    """

    pass


# Properties stored in DB
class UserInDB(UserInDBBase):
    """
    User schema as stored in database.
    Includes sensitive fields like hashed_password.
    NEVER expose this directly to API responses.
    """

    hashed_password: str = Field(..., description="Hashed password")
