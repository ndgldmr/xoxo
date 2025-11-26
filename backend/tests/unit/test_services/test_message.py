"""
Unit tests for MessageService.
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AlreadyExistsException, NotFoundException
from app.models.message import Message
from app.schemas.message import MessageCreate, MessageUpdate
from app.services.message import MessageService


class TestMessageService:
    """Tests for MessageService methods."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        mock = AsyncMock()
        # db.add() is NOT async in SQLAlchemy, so use MagicMock for it
        mock.add = MagicMock(return_value=None)
        return mock

    @pytest.fixture
    def mock_repository(self):
        """Create mock message repository with async methods."""
        mock = AsyncMock()
        # Set default return values for common async methods
        mock.get.return_value = None
        mock.subject_exists.return_value = False
        mock.date_exists.return_value = False
        mock.get_with_filters.return_value = []
        mock.update.return_value = None
        # .model is the SQLAlchemy class, NOT an async method
        mock.model = MagicMock()
        return mock

    @pytest.fixture
    def service(self, mock_db, mock_repository):
        """Create MessageService with mocked dependencies."""
        service = MessageService(mock_db)
        service.repository = mock_repository
        return service

    @pytest.fixture
    def sample_message(self):
        """Create a sample message for testing."""
        message = Message(
            id=1,
            message_date=date(2025, 11, 25),
            category="everyday_phrases",
            subject="Hello",
            definition="A greeting",
            example="Hello, how are you?",
            usage_tips="Use when meeting someone",
            cultural_notes="Common in English-speaking countries",
            is_active=True,
        )
        return message

    @pytest.fixture
    def sample_message_create(self):
        """Create sample message creation data."""
        return MessageCreate(
            message_date=date(2025, 11, 25),
            category="Everyday Phrases",  # Will be normalized to "everyday_phrases"
            subject="Hello",
            definition="A greeting",
            example="Hello, how are you?",
            usage_tips="Use when meeting someone",
            cultural_notes="Common in English-speaking countries",
        )

    # Test get_message
    @pytest.mark.asyncio
    async def test_get_message_success(self, service, mock_repository, sample_message):
        """Test successful retrieval of message by ID."""
        mock_repository.get.return_value = sample_message

        result = await service.get_message(1)

        assert result == sample_message
        mock_repository.get.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_message_not_found(self, service, mock_repository):
        """Test get_message raises NotFoundException when message doesn't exist."""
        mock_repository.get.return_value = None

        with pytest.raises(NotFoundException, match="Message with id 999 not found"):
            await service.get_message(999)

    # Test create_message
    @pytest.mark.asyncio
    async def test_create_message_success(
        self, service, mock_db, mock_repository, sample_message_create, sample_message
    ):
        """Test successful message creation."""
        # Setup mocks
        mock_repository.subject_exists.return_value = False
        mock_repository.date_exists.return_value = False
        mock_repository.model.return_value = sample_message

        result = await service.create_message(sample_message_create)

        # Verify subject uniqueness check
        mock_repository.subject_exists.assert_called_once_with("Hello")

        # Verify date uniqueness check
        mock_repository.date_exists.assert_called_once_with(date(2025, 11, 25))

        # Verify db operations
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_message_duplicate_subject(
        self, service, mock_repository, sample_message_create
    ):
        """Test create_message raises AlreadyExistsException for duplicate subject."""
        mock_repository.subject_exists.return_value = True
        mock_repository.date_exists.return_value = False

        with pytest.raises(
            AlreadyExistsException, match="Message with subject 'Hello' already exists"
        ):
            await service.create_message(sample_message_create)

    @pytest.mark.asyncio
    async def test_create_message_duplicate_date(
        self, service, mock_repository, sample_message_create
    ):
        """Test create_message raises AlreadyExistsException for duplicate date."""
        mock_repository.subject_exists.return_value = False
        mock_repository.date_exists.return_value = True

        with pytest.raises(
            AlreadyExistsException,
            match="Message for date 2025-11-25 already exists",
        ):
            await service.create_message(sample_message_create)

    @pytest.mark.asyncio
    async def test_create_message_normalizes_subject(
        self, service, mock_db, mock_repository, sample_message
    ):
        """Test that create_message normalizes subject by stripping whitespace."""
        message_data = MessageCreate(
            message_date=date(2025, 11, 25),
            subject="  Hello  ",  # Extra whitespace
            definition="A greeting",
            example="Hello, how are you?",
            usage_tips="Use when meeting someone",
        )

        mock_repository.subject_exists.return_value = False
        mock_repository.date_exists.return_value = False
        mock_repository.model.return_value = sample_message

        await service.create_message(message_data)

        # Verify subject was normalized before uniqueness check
        mock_repository.subject_exists.assert_called_once_with("Hello")

    # Test update_message
    @pytest.mark.asyncio
    async def test_update_message_success(
        self, service, mock_repository, sample_message
    ):
        """Test successful message update."""
        mock_repository.get.return_value = sample_message
        mock_repository.subject_exists.return_value = False
        mock_repository.date_exists.return_value = False
        updated_message = Message(**{**sample_message.__dict__, "subject": "Hi"})
        mock_repository.update.return_value = updated_message

        update_data = MessageUpdate(subject="Hi")
        result = await service.update_message(1, update_data)

        # Verify uniqueness checks with exclude_id
        mock_repository.subject_exists.assert_called_once_with("Hi", exclude_id=1)

        # Verify update was called
        mock_repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_message_not_found(self, service, mock_repository):
        """Test update_message raises NotFoundException when message doesn't exist."""
        mock_repository.get.return_value = None

        with pytest.raises(NotFoundException, match="Message with id 999 not found"):
            await service.update_message(999, MessageUpdate(subject="Hi"))

    @pytest.mark.asyncio
    async def test_update_message_duplicate_subject(
        self, service, mock_repository, sample_message
    ):
        """Test update_message raises AlreadyExistsException for duplicate subject."""
        mock_repository.get.return_value = sample_message
        mock_repository.subject_exists.return_value = True

        update_data = MessageUpdate(subject="Goodbye")

        with pytest.raises(
            AlreadyExistsException,
            match="Message with subject 'Goodbye' already exists",
        ):
            await service.update_message(1, update_data)

    @pytest.mark.asyncio
    async def test_update_message_duplicate_date(
        self, service, mock_repository, sample_message
    ):
        """Test update_message raises AlreadyExistsException for duplicate date."""
        mock_repository.get.return_value = sample_message
        mock_repository.subject_exists.return_value = False
        mock_repository.date_exists.return_value = True

        update_data = MessageUpdate(message_date=date(2025, 11, 26))

        with pytest.raises(
            AlreadyExistsException,
            match="Message for date 2025-11-26 already exists",
        ):
            await service.update_message(1, update_data)

    @pytest.mark.asyncio
    async def test_update_message_same_subject_no_conflict(
        self, service, mock_repository, sample_message
    ):
        """Test updating message with same subject doesn't trigger uniqueness check."""
        mock_repository.get.return_value = sample_message
        mock_repository.update.return_value = sample_message

        # Update with same subject (no change)
        update_data = MessageUpdate(definition="Updated definition")
        await service.update_message(1, update_data)

        # Verify subject_exists was NOT called (subject unchanged)
        mock_repository.subject_exists.assert_not_called()

    # Test delete_message (soft delete)
    @pytest.mark.asyncio
    async def test_delete_message_success(self, service, mock_repository, sample_message):
        """Test successful soft delete of message."""
        mock_repository.get.return_value = sample_message
        deactivated_message = Message(**{**sample_message.__dict__, "is_active": False})
        mock_repository.update.return_value = deactivated_message

        result = await service.delete_message(1)

        # Verify update was called with is_active=False
        mock_repository.update.assert_called_once()
        call_args = mock_repository.update.call_args
        assert call_args[1]["db_obj"] == sample_message
        assert call_args[1]["obj_in"].is_active is False

    @pytest.mark.asyncio
    async def test_delete_message_not_found(self, service, mock_repository):
        """Test delete_message raises NotFoundException when message doesn't exist."""
        mock_repository.get.return_value = None

        with pytest.raises(NotFoundException, match="Message with id 999 not found"):
            await service.delete_message(999)

    # Test activate_message
    @pytest.mark.asyncio
    async def test_activate_message_success(
        self, service, mock_repository, sample_message
    ):
        """Test successful activation of message."""
        deactivated = Message(**{**sample_message.__dict__, "is_active": False})
        mock_repository.get.return_value = deactivated
        mock_repository.update.return_value = sample_message

        result = await service.activate_message(1)

        # Verify update was called with is_active=True
        mock_repository.update.assert_called_once()
        call_args = mock_repository.update.call_args
        assert call_args[1]["db_obj"] == deactivated
        assert call_args[1]["obj_in"].is_active is True

    # Test get_messages with filters
    @pytest.mark.asyncio
    async def test_get_messages_with_filters(self, service, mock_repository):
        """Test get_messages passes filters correctly to repository."""
        mock_repository.get_with_filters.return_value = []

        await service.get_messages(
            skip=10,
            limit=50,
            active_only=True,
            category="everyday_phrases",
            message_date=date(2025, 11, 25),
        )

        mock_repository.get_with_filters.assert_called_once_with(
            skip=10,
            limit=50,
            active_only=True,
            category="everyday_phrases",
            message_date=date(2025, 11, 25),
        )

    # Test get_message_by_date
    @pytest.mark.asyncio
    async def test_get_message_by_date(
        self, service, mock_repository, sample_message
    ):
        """Test get_message_by_date retrieves message correctly."""
        mock_repository.get_by_date.return_value = sample_message

        result = await service.get_message_by_date(date(2025, 11, 25))

        assert result == sample_message
        mock_repository.get_by_date.assert_called_once_with(date(2025, 11, 25))

    # Test get_message_by_subject
    @pytest.mark.asyncio
    async def test_get_message_by_subject(
        self, service, mock_repository, sample_message
    ):
        """Test get_message_by_subject retrieves message correctly."""
        mock_repository.get_by_subject.return_value = sample_message

        result = await service.get_message_by_subject("Hello")

        assert result == sample_message
        # Verify subject was normalized
        mock_repository.get_by_subject.assert_called_once_with("Hello")
