"""
Unit tests for MessageGenerationService.
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AlreadyExistsException
from app.core.llm_client import LLMClientError, MockLLMClient
from app.models.message import Message
from app.schemas.message_generation import MessageGenerationPayload
from app.services.message_generation import MessageGenerationService


class TestMessageGenerationService:
    """Tests for MessageGenerationService."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        mock = AsyncMock()
        mock.add = MagicMock(return_value=None)  # db.add is not async

        # Mock execute to return a result with .all() method
        mock_result = MagicMock()
        mock_result.all.return_value = []  # Default empty list for recent subjects
        mock.execute = AsyncMock(return_value=mock_result)

        return mock

    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client."""
        return MockLLMClient(subjects_pool=["Test Subject", "Another Subject"])

    @pytest.fixture
    def sample_message(self):
        """Create a sample message for testing."""
        return Message(
            id=1,
            message_date=date(2025, 11, 26),
            category="everyday_phrases",
            subject="Test Subject",
            definition="A test definition",
            example="This is a test example.",
            usage_tips="Use this for testing.",
            cultural_notes="Test cultural notes",
            is_active=True,
        )

    @pytest.mark.asyncio
    async def test_generate_success(self, mock_db, mock_llm_client, sample_message):
        """Test successful message generation."""
        service = MessageGenerationService(mock_db, mock_llm_client, max_retries=1)

        # Mock MessageService methods
        service.message_service.get_message_by_date = AsyncMock(return_value=None)
        service.message_service.get_message_by_subject = AsyncMock(return_value=None)
        service.message_service.create_message = AsyncMock(return_value=sample_message)

        result = await service.generate_for_date(
            message_date=date(2025, 11, 26), category="everyday_phrases"
        )

        assert result == sample_message
        # Verify service methods were called
        service.message_service.get_message_by_date.assert_called_once()
        service.message_service.get_message_by_subject.assert_called_once()
        service.message_service.create_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_date_already_exists(
        self, mock_db, mock_llm_client, sample_message
    ):
        """Test generation fails when message_date already has a message."""
        service = MessageGenerationService(mock_db, mock_llm_client)

        # Mock existing message for date
        service.message_service.get_message_by_date = AsyncMock(
            return_value=sample_message
        )

        with pytest.raises(AlreadyExistsException) as exc_info:
            await service.generate_for_date(
                message_date=date(2025, 11, 26), category=None
            )

        assert "Message for date 2025-11-26 already exists" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_subject_conflict_no_retry(
        self, mock_db, mock_llm_client, sample_message
    ):
        """Test generation fails on subject conflict with max_retries=0."""
        service = MessageGenerationService(mock_db, mock_llm_client, max_retries=0)

        # Mock: no message for date, but subject exists
        service.message_service.get_message_by_date = AsyncMock(return_value=None)
        service.message_service.get_message_by_subject = AsyncMock(
            return_value=sample_message
        )

        with pytest.raises(AlreadyExistsException) as exc_info:
            await service.generate_for_date(message_date=date(2025, 11, 27))

        assert "already exists" in str(exc_info.value)
        assert "1 attempts" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_subject_conflict_with_retry_success(
        self, mock_db, mock_llm_client, sample_message
    ):
        """Test generation succeeds on retry after subject conflict."""
        # Use client with 2 different subjects
        llm_client = MockLLMClient(subjects_pool=["Conflict Subject", "Unique Subject"])
        service = MessageGenerationService(mock_db, llm_client, max_retries=1)

        # Mock: no message for date
        service.message_service.get_message_by_date = AsyncMock(return_value=None)

        # First subject conflicts, second is unique
        existing_message = Message(
            id=1,
            message_date=date(2025, 11, 20),
            subject="Conflict Subject",
            definition="...",
            example="...",
            usage_tips="...",
            is_active=True,
        )

        call_count = 0

        async def mock_get_by_subject(subject):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call: conflict
                return existing_message
            else:
                # Second call: no conflict
                return None

        service.message_service.get_message_by_subject = mock_get_by_subject

        # Mock successful creation
        created_message = Message(
            id=2,
            message_date=date(2025, 11, 27),
            subject="Unique Subject",
            definition="...",
            example="...",
            usage_tips="...",
            is_active=True,
        )
        service.message_service.create_message = AsyncMock(return_value=created_message)

        result = await service.generate_for_date(message_date=date(2025, 11, 27))

        assert result.subject == "Unique Subject"
        # Should have called get_by_subject twice (first conflict, second success)
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_generate_subject_conflict_retry_exhausted(
        self, mock_db, mock_llm_client, sample_message
    ):
        """Test generation fails after retry limit on subject conflict."""
        # Use client with 2 subjects that both conflict
        llm_client = MockLLMClient(
            subjects_pool=["Conflict Subject 1", "Conflict Subject 2"]
        )
        service = MessageGenerationService(mock_db, llm_client, max_retries=1)

        service.message_service.get_message_by_date = AsyncMock(return_value=None)
        # Both subjects conflict
        service.message_service.get_message_by_subject = AsyncMock(
            return_value=sample_message
        )

        with pytest.raises(AlreadyExistsException) as exc_info:
            await service.generate_for_date(message_date=date(2025, 11, 27))

        assert "already exists" in str(exc_info.value)
        assert "2 attempts" in str(exc_info.value)  # max_retries=1 means 2 total attempts

    @pytest.mark.asyncio
    async def test_generate_with_category(self, mock_db, mock_llm_client, sample_message):
        """Test generation with category passed to LLM."""
        service = MessageGenerationService(mock_db, mock_llm_client)

        service.message_service.get_message_by_date = AsyncMock(return_value=None)
        service.message_service.get_message_by_subject = AsyncMock(return_value=None)
        service.message_service.create_message = AsyncMock(return_value=sample_message)

        result = await service.generate_for_date(
            message_date=date(2025, 11, 26), category="black_history_month"
        )

        assert result == sample_message
        # Category should be passed through to create_message
        create_call_args = service.message_service.create_message.call_args
        assert create_call_args[0][0].category == "black_history_month"

    @pytest.mark.asyncio
    async def test_generate_llm_error_propagates(self, mock_db):
        """Test that LLM errors are propagated correctly."""
        # Create LLM client that raises an error
        mock_llm = AsyncMock()
        mock_llm.generate_message_payload = AsyncMock(
            side_effect=LLMClientError(
                error_type="AI_TIMEOUT", message="Request timed out"
            )
        )

        service = MessageGenerationService(mock_db, mock_llm)
        service.message_service.get_message_by_date = AsyncMock(return_value=None)

        with pytest.raises(LLMClientError) as exc_info:
            await service.generate_for_date(message_date=date(2025, 11, 26))

        assert exc_info.value.error_type == "AI_TIMEOUT"
        assert "timed out" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_get_recent_subjects(self, mock_db):
        """Test retrieval of recent subjects for context."""
        llm_client = MockLLMClient()
        service = MessageGenerationService(mock_db, llm_client)

        # Mock db.execute to return recent subjects
        mock_result = MagicMock()
        mock_result.all.return_value = [
            ("Subject 1",),
            ("Subject 2",),
            ("Subject 3",),
        ]
        mock_db.execute.return_value = mock_result

        recent = await service._get_recent_subjects(limit=3)

        assert recent == ["Subject 1", "Subject 2", "Subject 3"]
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_uses_recent_subjects_context(
        self, mock_db, sample_message
    ):
        """Test that recent subjects are fetched and passed to LLM."""
        llm_client = MockLLMClient()
        service = MessageGenerationService(mock_db, llm_client)

        # Mock recent subjects
        with patch.object(
            service, "_get_recent_subjects", return_value=["Old Subject 1", "Old Subject 2"]
        ):
            service.message_service.get_message_by_date = AsyncMock(return_value=None)
            service.message_service.get_message_by_subject = AsyncMock(return_value=None)
            service.message_service.create_message = AsyncMock(
                return_value=sample_message
            )

            # Spy on LLM client call
            with patch.object(
                llm_client, "generate_message_payload", wraps=llm_client.generate_message_payload
            ) as spy:
                await service.generate_for_date(message_date=date(2025, 11, 26))

                # Verify recent_subjects were passed
                spy.assert_called_once()
                call_kwargs = spy.call_args[1]
                assert call_kwargs["recent_subjects"] == ["Old Subject 1", "Old Subject 2"]
