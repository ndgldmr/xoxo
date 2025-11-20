"""
Authentication-related Pydantic schemas.
"""

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """
    Login request schema.
    """

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="User password")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "admin@xoxoeducation.com",
                    "password": "SecurePass123!",
                }
            ]
        }
    }


class TokenResponse(BaseModel):
    """
    Token response schema returned after successful login.
    """

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                }
            ]
        }
    }


class RefreshRequest(BaseModel):
    """
    Refresh token request schema.
    """

    refresh_token: str = Field(..., description="JWT refresh token")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                }
            ]
        }
    }


class TokenPayload(BaseModel):
    """
    JWT token payload schema for internal use.
    """

    sub: str = Field(..., description="Subject (user ID)")
    exp: int = Field(..., description="Expiration timestamp")
    type: str = Field(..., description="Token type (access or refresh)")
    is_admin: bool = Field(default=False, description="Whether user is admin")
