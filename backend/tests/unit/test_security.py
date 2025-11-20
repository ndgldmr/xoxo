"""
Unit tests for core security utilities.
"""

import pytest
from datetime import datetime, timedelta

from app.core.security import (
    hash_password,
    verify_password,
    validate_password_strength,
    create_access_token,
    create_refresh_token,
    verify_token,
    decode_token,
)
from jose import jwt, JWTError


class TestPasswordHashing:
    """Tests for password hashing and verification."""

    def test_hash_password(self):
        """Test that password hashing works."""
        password = "TestPassword123!"
        hashed = hash_password(password)

        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "TestPassword123!"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "TestPassword123!"
        wrong_password = "WrongPassword123!"
        hashed = hash_password(password)

        assert verify_password(wrong_password, hashed) is False

    def test_different_hashes_for_same_password(self):
        """Test that same password produces different hashes (salt)."""
        password = "TestPassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestPasswordValidation:
    """Tests for password strength validation."""

    def test_valid_password(self):
        """Test that valid password passes validation."""
        password = "ValidPass123!"
        is_valid, error = validate_password_strength(password)

        assert is_valid is True
        assert error is None

    def test_password_too_short(self):
        """Test that short password fails validation."""
        password = "Short1!"
        is_valid, error = validate_password_strength(password)

        assert is_valid is False
        assert "12 characters" in error

    def test_password_no_lowercase(self):
        """Test that password without lowercase fails."""
        password = "NOLOWERCASE123!"
        is_valid, error = validate_password_strength(password)

        assert is_valid is False
        assert "lowercase" in error

    def test_password_no_uppercase(self):
        """Test that password without uppercase fails."""
        password = "nouppercase123!"
        is_valid, error = validate_password_strength(password)

        assert is_valid is False
        assert "uppercase" in error

    def test_password_no_digit(self):
        """Test that password without digit fails."""
        password = "NoDigitPassword!"
        is_valid, error = validate_password_strength(password)

        assert is_valid is False
        assert "digit" in error

    def test_password_no_special_char(self):
        """Test that password without special character fails."""
        password = "NoSpecialChar123"
        is_valid, error = validate_password_strength(password)

        assert is_valid is False
        assert "special character" in error


class TestJWTTokens:
    """Tests for JWT token creation and verification."""

    def test_create_access_token(self):
        """Test access token creation."""
        user_id = 1
        is_admin = True

        token = create_access_token(subject=user_id, is_admin=is_admin)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self):
        """Test refresh token creation."""
        user_id = 1

        token = create_refresh_token(subject=user_id)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_access_token(self):
        """Test decoding access token."""
        user_id = 1
        is_admin = True

        token = create_access_token(subject=user_id, is_admin=is_admin)
        payload = decode_token(token)

        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"
        assert payload["is_admin"] is True
        assert "exp" in payload

    def test_decode_refresh_token(self):
        """Test decoding refresh token."""
        user_id = 2

        token = create_refresh_token(subject=user_id)
        payload = decode_token(token)

        assert payload["sub"] == str(user_id)
        assert payload["type"] == "refresh"
        assert "exp" in payload

    def test_verify_valid_access_token(self):
        """Test verifying valid access token."""
        user_id = 1
        is_admin = False

        token = create_access_token(subject=user_id, is_admin=is_admin)
        payload = verify_token(token, token_type="access")

        assert payload is not None
        assert payload["sub"] == str(user_id)
        assert payload["is_admin"] is False

    def test_verify_valid_refresh_token(self):
        """Test verifying valid refresh token."""
        user_id = 3

        token = create_refresh_token(subject=user_id)
        payload = verify_token(token, token_type="refresh")

        assert payload is not None
        assert payload["sub"] == str(user_id)

    def test_verify_wrong_token_type(self):
        """Test that token type mismatch returns None."""
        user_id = 1

        access_token = create_access_token(subject=user_id, is_admin=False)
        payload = verify_token(access_token, token_type="refresh")

        assert payload is None

    def test_verify_expired_token(self):
        """Test that expired token returns None."""
        user_id = 1

        # Create token that expires immediately
        token = create_access_token(
            subject=user_id,
            is_admin=False,
            expires_delta=timedelta(seconds=-1)  # Already expired
        )

        payload = verify_token(token, token_type="access")
        assert payload is None

    def test_verify_invalid_token(self):
        """Test that invalid token returns None."""
        invalid_token = "invalid.token.here"

        payload = verify_token(invalid_token, token_type="access")
        assert payload is None

    def test_custom_expiration(self):
        """Test creating token with custom expiration."""
        user_id = 1
        custom_delta = timedelta(hours=1)

        token = create_access_token(
            subject=user_id,
            is_admin=False,
            expires_delta=custom_delta
        )

        payload = decode_token(token)
        exp_time = datetime.fromtimestamp(payload["exp"])
        expected_time = datetime.utcnow() + custom_delta

        # Allow 5 second margin for test execution time
        time_diff = abs((exp_time - expected_time).total_seconds())
        assert time_diff < 5
