"""
Unit tests for StudentService.
"""

from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from app.core.exceptions import AlreadyExistsException, NotFoundException
from app.models.student import Student
from app.schemas.student import StudentCreate, StudentUpdate
from app.services.student import StudentService


class TestStudentService:
    """Tests for StudentService methods."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        from unittest.mock import MagicMock

        mock = AsyncMock()
        # db.add() is NOT async in SQLAlchemy, so use MagicMock for it
        mock.add = MagicMock(return_value=None)
        return mock

    @pytest.fixture
    def mock_repository(self):
        """Create mock student repository with async methods."""
        from unittest.mock import MagicMock

        mock = AsyncMock()
        # Set default return values for common async methods
        mock.get.return_value = None
        mock.email_exists.return_value = False
        mock.phone_exists.return_value = False
        mock.get_with_filters.return_value = []
        mock.update.return_value = None
        # .model is the SQLAlchemy class, NOT an async method
        mock.model = MagicMock()
        return mock

    @pytest.fixture
    def service(self, mock_db, mock_repository):
        """Create StudentService with mocked dependencies."""
        service = StudentService(mock_db)
        service.repository = mock_repository
        return service

    @pytest.fixture
    def sample_student(self):
        """Create a sample student for testing."""
        student = Student(
            id=1,
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            phone_number="+17038590314",
            country="USA",
            is_active=True,
            proficiency_level="beginner",
            native_language="pt-BR",
            wants_daily_message=False,
        )
        return student

    @pytest.fixture
    def sample_student_create(self):
        """Create sample student creation data."""
        return StudentCreate(
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            phone_number="+17038590314",
            proficiency_level="beginner",
            country="USA",
        )

    # Test get_student
    @pytest.mark.asyncio
    async def test_get_student_success(self, service, mock_repository, sample_student):
        """Test successful retrieval of student by ID."""
        mock_repository.get.return_value = sample_student

        result = await service.get_student(1)

        assert result == sample_student
        mock_repository.get.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_student_not_found(self, service, mock_repository):
        """Test get_student raises NotFoundException when student doesn't exist."""
        mock_repository.get.return_value = None

        with pytest.raises(NotFoundException, match="Student with id 999 not found"):
            await service.get_student(999)

    # Test create_student
    @pytest.mark.asyncio
    async def test_create_student_success(
        self, service, mock_repository, mock_db, sample_student_create, sample_student
    ):
        """Test successful student creation."""
        mock_repository.email_exists.return_value = False
        mock_repository.phone_exists.return_value = False
        mock_repository.model.return_value = sample_student

        result = await service.create_student(sample_student_create)

        assert result == sample_student
        mock_repository.email_exists.assert_called_once_with("test@example.com")
        mock_repository.phone_exists.assert_called_once_with("+17038590314")
        mock_db.add.assert_called_once()
        assert mock_db.commit.call_count == 1
        assert mock_db.refresh.call_count == 1

    @pytest.mark.asyncio
    async def test_create_student_email_exists(
        self, service, mock_repository, sample_student_create
    ):
        """Test create_student raises AlreadyExistsException for duplicate email."""
        mock_repository.email_exists.return_value = True

        with pytest.raises(
            AlreadyExistsException, match="Student with email .* already exists"
        ):
            await service.create_student(sample_student_create)

    @pytest.mark.asyncio
    async def test_create_student_phone_exists(
        self, service, mock_repository, sample_student_create
    ):
        """Test create_student raises AlreadyExistsException for duplicate phone."""
        mock_repository.email_exists.return_value = False
        mock_repository.phone_exists.return_value = True

        with pytest.raises(
            AlreadyExistsException, match="Student with phone number .* already exists"
        ):
            await service.create_student(sample_student_create)

    @pytest.mark.asyncio
    async def test_create_student_normalizes_email(
        self, service, mock_repository, mock_db, sample_student
    ):
        """Test that email is normalized to lowercase."""
        student_data = StudentCreate(
            email="TEST@EXAMPLE.COM",
            first_name="John",
            last_name="Doe",
            phone_number="+17038590314",
            proficiency_level="beginner",
            country="USA",
        )

        mock_repository.email_exists.return_value = False
        mock_repository.phone_exists.return_value = False
        mock_repository.model.return_value = sample_student

        await service.create_student(student_data)

        # Check that email was normalized to lowercase
        mock_repository.email_exists.assert_called_once_with("test@example.com")

    # Test update_student
    @pytest.mark.asyncio
    async def test_update_student_success(
        self, service, mock_repository, sample_student
    ):
        """Test successful student update."""
        mock_repository.get.return_value = sample_student
        mock_repository.email_exists.return_value = False
        mock_repository.update.return_value = sample_student

        update_data = StudentUpdate(first_name="Jane")
        result = await service.update_student(1, update_data)

        assert result == sample_student
        mock_repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_student_not_found(self, service, mock_repository):
        """Test update_student raises NotFoundException when student doesn't exist."""
        mock_repository.get.return_value = None

        update_data = StudentUpdate(first_name="Jane")

        with pytest.raises(NotFoundException):
            await service.update_student(999, update_data)

    @pytest.mark.asyncio
    async def test_update_student_email_conflict(
        self, service, mock_repository, sample_student
    ):
        """Test update_student raises AlreadyExistsException for email conflict."""
        mock_repository.get.return_value = sample_student
        mock_repository.email_exists.return_value = True

        update_data = StudentUpdate(email="other@example.com")

        with pytest.raises(AlreadyExistsException, match="email .* already exists"):
            await service.update_student(1, update_data)

    @pytest.mark.asyncio
    async def test_update_student_phone_conflict(
        self, service, mock_repository, sample_student
    ):
        """Test update_student raises AlreadyExistsException for phone conflict."""
        mock_repository.get.return_value = sample_student
        mock_repository.email_exists.return_value = False
        mock_repository.phone_exists.return_value = True

        update_data = StudentUpdate(phone_number="+19876543210")

        with pytest.raises(
            AlreadyExistsException, match="phone number .* already exists"
        ):
            await service.update_student(1, update_data)

    # Test delete_student (soft delete)
    @pytest.mark.asyncio
    async def test_delete_student_soft_delete(
        self, service, mock_repository, sample_student
    ):
        """Test that delete_student performs soft delete."""
        mock_repository.get.return_value = sample_student
        mock_repository.update.return_value = sample_student

        result = await service.delete_student(1)

        assert result == sample_student
        mock_repository.update.assert_called_once()
        # Verify that update was called with is_active=False
        call_args = mock_repository.update.call_args
        assert call_args[1]["obj_in"].is_active is False

    @pytest.mark.asyncio
    async def test_delete_student_not_found(self, service, mock_repository):
        """Test delete_student raises NotFoundException when student doesn't exist."""
        mock_repository.get.return_value = None

        with pytest.raises(NotFoundException):
            await service.delete_student(999)

    # Test activate_student
    @pytest.mark.asyncio
    async def test_activate_student_success(
        self, service, mock_repository, sample_student
    ):
        """Test successful student activation."""
        mock_repository.get.return_value = sample_student
        mock_repository.update.return_value = sample_student

        result = await service.activate_student(1)

        assert result == sample_student
        mock_repository.update.assert_called_once()
        # Verify that update was called with is_active=True
        call_args = mock_repository.update.call_args
        assert call_args[1]["obj_in"].is_active is True

    # Test get_students with filters
    @pytest.mark.asyncio
    async def test_get_students_no_filters(self, service, mock_repository, sample_student):
        """Test get_students without filters."""
        mock_students = [sample_student for _ in range(3)]
        mock_repository.get_with_filters.return_value = mock_students

        result = await service.get_students()

        assert len(result) == 3
        mock_repository.get_with_filters.assert_called_once_with(
            skip=0,
            limit=100,
            active_only=False,
            email=None,
            name=None,
            country=None,
        )

    @pytest.mark.asyncio
    async def test_get_students_with_filters(self, service, mock_repository):
        """Test get_students with various filters."""
        mock_repository.get_with_filters.return_value = []

        await service.get_students(
            skip=10,
            limit=50,
            active_only=True,
            email="test@example.com",
            name="John",
            country="USA",
        )

        mock_repository.get_with_filters.assert_called_once_with(
            skip=10,
            limit=50,
            active_only=True,
            email="test@example.com",
            name="John",
            country="USA",
        )

    # Test phone validation
    def test_phone_validation_valid_formats(self):
        """Test that valid E.164 phone numbers are accepted."""
        valid_phones = [
            "+17038590314",  # US
            "+447911123456",  # UK
            "+33612345678",  # France
            "+862012345678",  # China
            "+5511987654321",  # Brazil
        ]

        for phone in valid_phones:
            student_data = StudentCreate(
                email="test@example.com",
                first_name="John",
                last_name="Doe",
                phone_number=phone,
                proficiency_level="beginner",
            )
            assert student_data.phone_number == phone

    def test_phone_validation_invalid_formats(self):
        """Test that invalid E.164 phone numbers are rejected."""
        invalid_phones = [
            "17038590314",  # Missing +
            "+0038590314",  # Starts with 0
            "+1703859031499999",  # Too long (>15 digits)
            "+1",  # Too short
            "+1-703-859-0314",  # Contains dashes
            "+1 (703) 859-0314",  # Contains spaces and parens
            "1234567890",  # No country code
        ]

        for phone in invalid_phones:
            with pytest.raises(ValidationError):
                StudentCreate(
                    email="test@example.com",
                    first_name="John",
                    last_name="Doe",
                    phone_number=phone,
                    proficiency_level="beginner",
                )

    # Test email normalization
    def test_email_normalization(self, service):
        """Test that email normalization works correctly."""
        test_cases = [
            ("TEST@EXAMPLE.COM", "test@example.com"),
            ("  test@example.com  ", "test@example.com"),
            ("Test@Example.COM", "test@example.com"),
        ]

        for input_email, expected in test_cases:
            result = service._normalize_email(input_email)
            assert result == expected

    # ========================================================================
    # PHASE 0: MESSAGING PREFERENCES TESTS
    # ========================================================================

    # Test proficiency_level validation
    def test_proficiency_level_valid_values(self):
        """Test that valid proficiency levels are accepted."""
        valid_levels = ["beginner", "intermediate", "advanced"]

        for level in valid_levels:
            student_data = StudentCreate(
                email="test@example.com",
                first_name="John",
                last_name="Doe",
                phone_number="+17038590314",
                proficiency_level=level,
            )
            # Validator normalizes to lowercase
            assert student_data.proficiency_level == level.lower()

    def test_proficiency_level_case_insensitive(self):
        """Test that proficiency level validation is case-insensitive."""
        test_cases = ["Beginner", "INTERMEDIATE", "AdVaNcEd"]

        for level in test_cases:
            student_data = StudentCreate(
                email="test@example.com",
                first_name="John",
                last_name="Doe",
                phone_number="+17038590314",
                proficiency_level=level,
            )
            assert student_data.proficiency_level == level.lower()

    def test_proficiency_level_invalid_value(self):
        """Test that invalid proficiency levels are rejected."""
        invalid_levels = ["expert", "novice", "fluent", ""]

        for level in invalid_levels:
            with pytest.raises(ValidationError, match="Proficiency level must be one of"):
                StudentCreate(
                    email="test@example.com",
                    first_name="John",
                    last_name="Doe",
                    phone_number="+17038590314",
                    proficiency_level=level,
                )

    def test_proficiency_level_required_on_create(self):
        """Test that proficiency_level is required when creating a student."""
        with pytest.raises(ValidationError):
            StudentCreate(
                email="test@example.com",
                first_name="John",
                last_name="Doe",
                phone_number="+17038590314",
            )

    # Test native_language default
    def test_native_language_default_value(self):
        """Test that native_language defaults to pt-BR."""
        student_data = StudentCreate(
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            phone_number="+17038590314",
            proficiency_level="beginner",
        )
        assert student_data.native_language == "pt-BR"

    def test_native_language_can_be_overridden(self):
        """Test that native_language can be set to a custom value."""
        student_data = StudentCreate(
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            phone_number="+17038590314",
            proficiency_level="beginner",
            native_language="es",
        )
        assert student_data.native_language == "es"

    # Test wants_daily_message defaults
    def test_wants_daily_message_default_false(self):
        """Test that wants_daily_message defaults to False."""
        student_data = StudentCreate(
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            phone_number="+17038590314",
            proficiency_level="beginner",
        )
        assert student_data.wants_daily_message is False

    # Test timezone validation
    def test_timezone_valid_iana_timezones(self):
        """Test that valid IANA timezones are accepted."""
        from datetime import time as dt_time

        valid_timezones = [
            "America/Sao_Paulo",
            "America/New_York",
            "Europe/London",
            "Asia/Tokyo",
            "UTC",
        ]

        for tz in valid_timezones:
            student_data = StudentCreate(
                email="test@example.com",
                first_name="John",
                last_name="Doe",
                phone_number="+17038590314",
                proficiency_level="beginner",
                wants_daily_message=True,
                timezone=tz,
                daily_message_time_local=dt_time(9, 0),
            )
            assert student_data.timezone == tz

    def test_timezone_invalid_value(self):
        """Test that invalid timezones are rejected."""
        from datetime import time as dt_time

        invalid_timezones = [
            "Invalid/Timezone",
            "EST",  # Abbreviations not allowed
            "US/Eastern",  # Deprecated format (though some might still work)
            "Not_A_Timezone",
        ]

        for tz in invalid_timezones:
            with pytest.raises(ValidationError, match="Invalid timezone"):
                StudentCreate(
                    email="test@example.com",
                    first_name="John",
                    last_name="Doe",
                    phone_number="+17038590314",
                    proficiency_level="beginner",
                    wants_daily_message=True,
                    timezone=tz,
                    daily_message_time_local=dt_time(9, 0),
                )

    # Test wants_daily_message cross-field validation
    def test_wants_daily_message_requires_timezone(self):
        """Test that wants_daily_message=True requires timezone."""
        from datetime import time as dt_time

        with pytest.raises(ValidationError, match="timezone is required"):
            StudentCreate(
                email="test@example.com",
                first_name="John",
                last_name="Doe",
                phone_number="+17038590314",
                proficiency_level="beginner",
                wants_daily_message=True,
                daily_message_time_local=dt_time(9, 0),
                # timezone missing
            )

    def test_wants_daily_message_requires_time(self):
        """Test that wants_daily_message=True requires daily_message_time_local."""
        with pytest.raises(ValidationError, match="daily_message_time_local is required"):
            StudentCreate(
                email="test@example.com",
                first_name="John",
                last_name="Doe",
                phone_number="+17038590314",
                proficiency_level="beginner",
                wants_daily_message=True,
                timezone="America/Sao_Paulo",
                # daily_message_time_local missing
            )

    def test_wants_daily_message_false_allows_missing_fields(self):
        """Test that wants_daily_message=False allows missing timezone and time."""
        student_data = StudentCreate(
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            phone_number="+17038590314",
            proficiency_level="beginner",
            wants_daily_message=False,
            # timezone and daily_message_time_local not provided
        )
        assert student_data.wants_daily_message is False
        assert student_data.timezone is None
        assert student_data.daily_message_time_local is None

    def test_daily_message_time_accepts_any_valid_time(self):
        """Test that daily_message_time_local accepts any valid time."""
        from datetime import time as dt_time

        test_times = [
            dt_time(0, 0),      # Midnight
            dt_time(6, 30),     # Morning
            dt_time(12, 0),     # Noon
            dt_time(18, 45),    # Evening
            dt_time(23, 59),    # Late night
        ]

        for test_time in test_times:
            student_data = StudentCreate(
                email="test@example.com",
                first_name="John",
                last_name="Doe",
                phone_number="+17038590314",
                proficiency_level="beginner",
                wants_daily_message=True,
                timezone="America/Sao_Paulo",
                daily_message_time_local=test_time,
            )
            assert student_data.daily_message_time_local == test_time

    # Test StudentUpdate with messaging preferences
    def test_update_proficiency_level(self):
        """Test updating proficiency_level in StudentUpdate."""
        update_data = StudentUpdate(proficiency_level="intermediate")
        assert update_data.proficiency_level == "intermediate"

    def test_update_proficiency_level_invalid(self):
        """Test that invalid proficiency_level is rejected in StudentUpdate."""
        with pytest.raises(ValidationError, match="Proficiency level must be one of"):
            StudentUpdate(proficiency_level="expert")

    def test_update_timezone_valid(self):
        """Test updating timezone with valid IANA timezone."""
        update_data = StudentUpdate(timezone="Europe/Paris")
        assert update_data.timezone == "Europe/Paris"

    def test_update_timezone_invalid(self):
        """Test that invalid timezone is rejected in StudentUpdate."""
        with pytest.raises(ValidationError, match="Invalid timezone"):
            StudentUpdate(timezone="Invalid/Zone")

    # Test service-level validation for updates
    @pytest.mark.asyncio
    async def test_update_wants_daily_message_requires_fields(
        self, service, mock_repository, sample_student
    ):
        """Test that updating wants_daily_message=True validates required fields."""
        from datetime import time as dt_time

        # Student exists but doesn't have timezone/time set
        sample_student.wants_daily_message = False
        sample_student.timezone = None
        sample_student.daily_message_time_local = None
        mock_repository.get.return_value = sample_student

        # Try to update wants_daily_message=True without providing timezone/time
        update_data = StudentUpdate(wants_daily_message=True)

        with pytest.raises(ValueError, match="timezone is required"):
            await service.update_student(1, update_data)

    @pytest.mark.asyncio
    async def test_update_wants_daily_message_with_existing_fields(
        self, service, mock_repository, sample_student
    ):
        """Test updating wants_daily_message=True when fields already exist."""
        from datetime import time as dt_time

        # Student already has timezone and time configured
        sample_student.timezone = "America/Sao_Paulo"
        sample_student.daily_message_time_local = dt_time(9, 0)
        sample_student.wants_daily_message = False
        mock_repository.get.return_value = sample_student
        mock_repository.update.return_value = sample_student

        # Update wants_daily_message=True (should succeed because fields exist)
        update_data = StudentUpdate(wants_daily_message=True)
        result = await service.update_student(1, update_data)

        assert result == sample_student
        mock_repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_wants_daily_message_with_provided_fields(
        self, service, mock_repository, sample_student
    ):
        """Test updating wants_daily_message=True with timezone and time in same request."""
        from datetime import time as dt_time

        # Student doesn't have timezone/time
        sample_student.timezone = None
        sample_student.daily_message_time_local = None
        mock_repository.get.return_value = sample_student
        mock_repository.update.return_value = sample_student

        # Update wants_daily_message=True and provide required fields
        update_data = StudentUpdate(
            wants_daily_message=True,
            timezone="America/New_York",
            daily_message_time_local=dt_time(10, 30),
        )
        result = await service.update_student(1, update_data)

        assert result == sample_student
        mock_repository.update.assert_called_once()
