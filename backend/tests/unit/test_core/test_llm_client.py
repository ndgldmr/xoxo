"""
Unit tests for LLM clients (MockLLMClient and OpenAIClient).
"""

import pytest

from app.core.llm_client import LLMClientError, MockLLMClient
from app.schemas.message_generation import MessageGenerationPayload


class TestMockLLMClient:
    """Tests for MockLLMClient."""

    @pytest.mark.asyncio
    async def test_generate_basic(self):
        """Test basic message payload generation."""
        client = MockLLMClient()

        payload = await client.generate_message_payload()

        assert isinstance(payload, MessageGenerationPayload)
        assert payload.subject
        assert payload.definition
        assert payload.example
        assert payload.usage_tips
        # cultural_notes is optional

    @pytest.mark.asyncio
    async def test_generate_with_category(self):
        """Test generation with category context."""
        client = MockLLMClient()

        payload = await client.generate_message_payload(category="everyday_phrases")

        assert isinstance(payload, MessageGenerationPayload)
        assert payload.subject
        assert payload.cultural_notes is not None  # Category triggers cultural_notes

    @pytest.mark.asyncio
    async def test_generate_respects_exclusions(self):
        """Test that excluded subjects are not returned."""
        # Create client with small pool
        subjects_pool = ["Subject A", "Subject B", "Subject C"]
        client = MockLLMClient(subjects_pool=subjects_pool)

        # Exclude all but one subject
        exclude = ["Subject A", "Subject B"]

        payload = await client.generate_message_payload(exclude_subjects=exclude)

        assert payload.subject == "Subject C"

    @pytest.mark.asyncio
    async def test_generate_respects_recent_subjects(self):
        """Test that recent subjects are avoided."""
        subjects_pool = ["Subject A", "Subject B", "Subject C"]
        client = MockLLMClient(subjects_pool=subjects_pool)

        # Mark A and B as recent
        recent = ["Subject A", "Subject B"]

        payload = await client.generate_message_payload(recent_subjects=recent)

        assert payload.subject == "Subject C"

    @pytest.mark.asyncio
    async def test_generate_cycles_through_pool(self):
        """Test that multiple calls cycle through available subjects."""
        subjects_pool = ["Subject A", "Subject B", "Subject C"]
        client = MockLLMClient(subjects_pool=subjects_pool)

        # Generate 3 messages
        payload1 = await client.generate_message_payload()
        payload2 = await client.generate_message_payload()
        payload3 = await client.generate_message_payload()

        # Should cycle through pool
        assert payload1.subject == "Subject A"
        assert payload2.subject == "Subject B"
        assert payload3.subject == "Subject C"

    @pytest.mark.asyncio
    async def test_generate_fails_when_all_excluded(self):
        """Test that generation fails when all subjects are excluded."""
        subjects_pool = ["Subject A", "Subject B"]
        client = MockLLMClient(subjects_pool=subjects_pool)

        # Exclude all subjects
        exclude = ["Subject A", "Subject B"]

        with pytest.raises(LLMClientError) as exc_info:
            await client.generate_message_payload(exclude_subjects=exclude)

        assert exc_info.value.error_type == "AI_SUBJECT_EXHAUSTED"
        assert "No available subjects" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_generate_combines_recent_and_exclude(self):
        """Test that both recent and exclude lists are respected."""
        subjects_pool = ["A", "B", "C", "D"]
        client = MockLLMClient(subjects_pool=subjects_pool)

        recent = ["A", "B"]
        exclude = ["C"]

        payload = await client.generate_message_payload(
            recent_subjects=recent, exclude_subjects=exclude
        )

        assert payload.subject == "D"

    @pytest.mark.asyncio
    async def test_payload_validation(self):
        """Test that generated payload passes Pydantic validation."""
        client = MockLLMClient()

        payload = await client.generate_message_payload()

        # Should not raise validation errors
        assert len(payload.subject) > 0
        assert len(payload.subject) <= 255
        assert len(payload.definition) > 0
        assert len(payload.example) > 0
        assert len(payload.usage_tips) > 0


class TestOpenAIClient:
    """
    Tests for OpenAIClient.

    Note: These tests do NOT make real API calls. We test OpenAIClient behavior
    using mocks or by verifying it raises appropriate errors without API keys.
    """

    def test_openai_client_requires_api_key(self):
        """Test that OpenAIClient requires an API key."""
        from app.core.llm_client import OpenAIClient

        # Should not raise during initialization
        client = OpenAIClient(api_key="test-key")
        assert client.api_key == "test-key"
        assert client.model == "gpt-4o-mini"  # default

    def test_openai_client_custom_config(self):
        """Test OpenAIClient with custom configuration."""
        from app.core.llm_client import OpenAIClient

        client = OpenAIClient(
            api_key="test-key",
            model="gpt-4",
            base_url="https://custom.api.com/v1",
            timeout=60.0,
            max_tokens=1000,
        )

        assert client.api_key == "test-key"
        assert client.model == "gpt-4"
        assert client.base_url == "https://custom.api.com/v1"
        assert client.timeout == 60.0
        assert client.max_tokens == 1000

    # Note: We don't test actual API calls here to keep tests fast and free
    # Real API integration would be tested manually or in separate integration tests
