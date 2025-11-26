"""
API tests for POST /messages/generate endpoint.
"""

from datetime import date, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status

from app.core.exceptions import AlreadyExistsException
from app.core.llm_client import LLMClientError
from app.models.message import Message


@pytest.fixture
def sample_message():
    """Create a sample message for testing."""
    return Message(
        id=1,
        message_date=date(2025, 11, 26),
        category="everyday_phrases",
        subject="Break the ice",
        definition="To make people feel more comfortable in a social situation",
        example="He told a joke to break the ice at the beginning of the meeting.",
        usage_tips="Use this phrase when you want to reduce tension or start a conversation in an awkward situation.",
        cultural_notes="Common in English-speaking business and social contexts.",
        is_active=True,
        created_at=datetime(2025, 11, 26, 12, 0, 0),
        updated_at=datetime(2025, 11, 26, 12, 0, 0),
    )


@pytest.mark.asyncio
async def test_generate_success(client, admin_headers, sample_message):
    """Test successful message generation."""
    with patch(
        "app.api.v1.endpoints.messages.MessageGenerationService"
    ) as mock_service_class:
        # Mock the service instance and its method
        mock_service = mock_service_class.return_value
        mock_service.generate_for_date = AsyncMock(return_value=sample_message)

        response = await client.post(
            "/api/v1/messages/generate",
            json={"message_date": "2025-11-26", "category": "everyday_phrases"},
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["id"] == 1
        assert data["subject"] == "Break the ice"
        assert data["message_date"] == "2025-11-26"
        assert data["category"] == "everyday_phrases"


@pytest.mark.asyncio
async def test_generate_without_category(client, admin_headers, sample_message):
    """Test generation without category (optional field)."""
    sample_message.category = None

    with patch(
        "app.api.v1.endpoints.messages.MessageGenerationService"
    ) as mock_service_class:
        mock_service = mock_service_class.return_value
        mock_service.generate_for_date = AsyncMock(return_value=sample_message)

        response = await client.post(
            "/api/v1/messages/generate",
            json={"message_date": "2025-11-26"},
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["category"] is None


@pytest.mark.asyncio
async def test_generate_date_conflict(client, admin_headers):
    """Test generation fails when message_date already exists."""
    with patch(
        "app.api.v1.endpoints.messages.MessageGenerationService"
    ) as mock_service_class:
        mock_service = mock_service_class.return_value
        mock_service.generate_for_date = AsyncMock(
            side_effect=AlreadyExistsException(
                "Message for date 2025-11-26 already exists"
            )
        )

        response = await client.post(
            "/api/v1/messages/generate",
            json={"message_date": "2025-11-26"},
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_generate_subject_conflict(client, admin_headers):
    """Test generation fails on subject conflict after retries."""
    with patch(
        "app.api.v1.endpoints.messages.MessageGenerationService"
    ) as mock_service_class:
        mock_service = mock_service_class.return_value
        mock_service.generate_for_date = AsyncMock(
            side_effect=AlreadyExistsException(
                "Message with subject 'Test' already exists. Failed after 2 attempts."
            )
        )

        response = await client.post(
            "/api/v1/messages/generate",
            json={"message_date": "2025-11-26", "category": "everyday_phrases"},
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_generate_ai_timeout(client, admin_headers):
    """Test generation fails on AI timeout."""
    with patch(
        "app.api.v1.endpoints.messages.MessageGenerationService"
    ) as mock_service_class:
        mock_service = mock_service_class.return_value
        mock_service.generate_for_date = AsyncMock(
            side_effect=LLMClientError(
                error_type="AI_TIMEOUT",
                message="OpenAI API request timed out after 30s",
                details={"timeout": 30},
            )
        )

        response = await client.post(
            "/api/v1/messages/generate",
            json={"message_date": "2025-11-26"},
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()["detail"]
        assert data["error_type"] == "AI_TIMEOUT"
        assert "timed out" in data["message"]


@pytest.mark.asyncio
async def test_generate_ai_parse_error(client, admin_headers):
    """Test generation fails on AI JSON parse error."""
    with patch(
        "app.api.v1.endpoints.messages.MessageGenerationService"
    ) as mock_service_class:
        mock_service = mock_service_class.return_value
        mock_service.generate_for_date = AsyncMock(
            side_effect=LLMClientError(
                error_type="AI_JSON_PARSE_ERROR",
                message="Failed to parse LLM response as JSON",
            )
        )

        response = await client.post(
            "/api/v1/messages/generate",
            json={"message_date": "2025-11-26"},
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()["detail"]
        assert data["error_type"] == "AI_JSON_PARSE_ERROR"


@pytest.mark.asyncio
async def test_generate_requires_admin(client, user_headers):
    """Test generation requires admin authentication."""
    response = await client.post(
        "/api/v1/messages/generate",
        json={"message_date": "2025-11-26"},
        headers=user_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "Admin privileges required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_generate_requires_auth(client):
    """Test generation requires authentication."""
    response = await client.post(
        "/api/v1/messages/generate",
        json={"message_date": "2025-11-26"},
    )

    # require_admin dependency returns 403 when no auth header provided
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_generate_invalid_date_format(client, admin_headers):
    """Test generation with invalid date format."""
    response = await client.post(
        "/api/v1/messages/generate",
        json={"message_date": "invalid-date"},
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_generate_missing_date(client, admin_headers):
    """Test generation without required message_date field."""
    response = await client.post(
        "/api/v1/messages/generate",
        json={"category": "everyday_phrases"},
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_generate_empty_category(client, admin_headers):
    """Test generation with empty category string."""
    response = await client.post(
        "/api/v1/messages/generate",
        json={"message_date": "2025-11-26", "category": ""},
        headers=admin_headers,
    )

    # Empty category should fail validation
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
