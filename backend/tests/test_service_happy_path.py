"""Tests for service layer happy path scenarios."""
import pytest
from unittest.mock import Mock
from app.services.word_of_day_service import WordOfDayService
from app.logging.audit_log import AuditLog
from datetime import date


# Valid 6-parameter dict for mocking LLM output
VALID_PARAMS = {
    "word_phrase": "Thank you",
    "meaning_pt": "Uma expressão de gratidão usada para agradecer alguém.",
    "pronunciation": "thank YOO",
    "when_to_use": "Use quando alguém faz algo gentil por você ou te dá algo.",
    "example_pt": "Obrigado pela ajuda que você me deu!",
    "example_en": "Thank you for your help!",
}


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    client = Mock()
    client.generate_message_params.return_value = VALID_PARAMS
    client.generate_repair_message_params.return_value = VALID_PARAMS
    return client


@pytest.fixture
def mock_wasender_client():
    """Create a mock WaSender client."""
    client = Mock()
    client.send_template_message.return_value = {
        "sid": "MOCK_MESSAGE_SID_12345",
        "status": "sent",
        "error_code": None,
        "error_message": None,
        "date_created": None,
        "date_updated": None,
        "price": None,
        "price_unit": None,
        "full_response": {},
    }
    return client


@pytest.fixture
def temp_audit_log(tmp_path):
    """Create a temporary audit log."""
    log_path = tmp_path / "test_audit.jsonl"
    return AuditLog(str(log_path))


@pytest.fixture
def service(mock_llm_client, mock_wasender_client, temp_audit_log):
    """Create a WordOfDayService with mocked dependencies."""
    return WordOfDayService(
        llm_client=mock_llm_client,
        whatsapp_client=mock_wasender_client,
        audit_log=temp_audit_log,
        to_number="+5511999999999",
    )


def test_happy_path_generates_validates_and_sends(
    service,
    mock_llm_client,
    mock_wasender_client,
):
    """Test complete happy path: generate -> validate -> send -> log."""
    result = service.run_daily_job(theme="greetings", level="beginner")

    # Check LLM was called correctly
    mock_llm_client.generate_message_params.assert_called_once_with(
        theme="greetings",
        level="beginner",
    )

    # Check WaSender was called
    mock_wasender_client.send_template_message.assert_called_once()

    # Check result
    assert result["status"] == "success"
    assert result["sent_count"] == 1
    assert result["date"] == date.today().isoformat()
    assert result["used_fallback"] is False
    assert result["validation_errors"] == []

    # Check audit log
    events = service.audit_log.get_today_events()
    assert len(events) == 1
    assert events[0]["sent"] is True
    assert events[0]["valid"] is True
    assert events[0]["theme"] == "greetings"
    assert events[0]["level"] == "beginner"


def test_idempotency_does_not_send_twice_without_force(
    service,
    mock_llm_client,
    mock_wasender_client,
):
    """Test that message is not sent twice on same day unless force=True."""
    # First send
    result1 = service.run_daily_job()
    assert result1["sent_count"] == 1

    # Reset mocks
    mock_llm_client.reset_mock()
    mock_wasender_client.reset_mock()

    # Second send without force
    result2 = service.run_daily_job(force=False)
    assert result2["status"] == "skipped"
    assert result2["sent_count"] == 0
    assert "already sent today" in result2["validation_errors"][0].lower()

    # LLM and WaSender should not be called
    mock_llm_client.generate_message_params.assert_not_called()
    mock_wasender_client.send_template_message.assert_not_called()


def test_idempotency_sends_with_force_flag(
    service,
    mock_llm_client,
    mock_wasender_client,
):
    """Test that force=True bypasses idempotency check."""
    # First send
    result1 = service.run_daily_job()
    assert result1["sent_count"] == 1

    # Reset mocks
    mock_llm_client.reset_mock()
    mock_wasender_client.reset_mock()

    # Second send with force=True
    result2 = service.run_daily_job(force=True)
    assert result2["sent_count"] == 1

    # LLM and WaSender should be called again
    mock_llm_client.generate_message_params.assert_called_once()
    mock_wasender_client.send_template_message.assert_called_once()


def test_validation_failure_triggers_retry(service, mock_llm_client, mock_wasender_client):
    """Test that validation failure triggers repair attempt."""
    # First attempt returns params that will fail validation (empty word_phrase)
    invalid_params = {**VALID_PARAMS, "word_phrase": ""}

    mock_llm_client.generate_message_params.return_value = invalid_params
    mock_llm_client.generate_repair_message_params.return_value = VALID_PARAMS

    result = service.run_daily_job()

    # Check repair was called
    assert mock_llm_client.generate_repair_message_params.call_count >= 1

    # Should still succeed with repaired params
    assert result["sent_count"] == 1
    assert result["used_fallback"] is False


def test_no_send_after_max_validation_retries(service, mock_llm_client, mock_wasender_client):
    """Test that nothing is sent when validation keeps failing after all repair attempts."""
    invalid_params = {**VALID_PARAMS, "word_phrase": ""}
    mock_llm_client.generate_message_params.return_value = invalid_params
    mock_llm_client.generate_repair_message_params.return_value = invalid_params

    result = service.run_daily_job()

    assert result["status"] == "error"
    assert result["sent_count"] == 0
    assert result["used_fallback"] is False
    mock_wasender_client.send_template_message.assert_not_called()


def test_multi_recipient_generates_content_per_level(
    mock_llm_client,
    mock_wasender_client,
    temp_audit_log,
):
    """In multi-recipient mode, content is generated separately for each english level."""
    from unittest.mock import MagicMock, patch

    beginner_params = {**VALID_PARAMS, "word_phrase": "Good morning"}
    intermediate_params = {**VALID_PARAMS, "word_phrase": "Nevertheless"}

    def generate_by_level(theme, level):
        return beginner_params if level == "beginner" else intermediate_params

    mock_llm_client.generate_message_params.side_effect = generate_by_level

    # Build mock DB session with two students at different levels
    beginner = MagicMock()
    beginner.phone_number = "+5511111111111"
    beginner.first_name = "Ana"
    beginner.english_level = "beginner"

    intermediate = MagicMock()
    intermediate.phone_number = "+5522222222222"
    intermediate.first_name = "Bruno"
    intermediate.english_level = "intermediate"

    mock_repo = MagicMock()
    mock_repo.get_active_subscribers.return_value = [beginner, intermediate]

    mock_db = MagicMock()

    with patch("app.repositories.student.StudentRepository", return_value=mock_repo), \
         patch.object(WordOfDayService, "_load_stored_messages", return_value={}):
        svc = WordOfDayService(
            llm_client=mock_llm_client,
            whatsapp_client=mock_wasender_client,
            audit_log=temp_audit_log,
            db_session=mock_db,
        )
        result = svc.run_daily_job(theme="travel")

    assert result["status"] == "success"
    assert result["sent_count"] == 2
    assert result["total_recipients"] == 2

    # LLM called once per distinct level
    assert mock_llm_client.generate_message_params.call_count == 2
    levels_called = {
        call.kwargs["level"]
        for call in mock_llm_client.generate_message_params.call_args_list
    }
    assert levels_called == {"beginner", "intermediate"}

    # Both students received a message
    assert mock_wasender_client.send_template_message.call_count == 2

    # Preview contains both level words
    assert "beginner" in result["preview"]
    assert "intermediate" in result["preview"]


def test_send_job_uses_stored_message_skips_llm(
    mock_llm_client,
    mock_wasender_client,
    temp_audit_log,
):
    """When stored messages exist for today, the send job uses them without calling the LLM."""
    from unittest.mock import MagicMock, patch

    stored_beginner = {
        "template_params": VALID_PARAMS,
        "formatted_message": "🇺🇸 *Palavra/Frase do Dia:* Thank you\n\n...",
        "theme": "greetings",
    }

    student = MagicMock()
    student.phone_number = "+5511111111111"
    student.first_name = "Ana"
    student.english_level = "beginner"

    mock_repo = MagicMock()
    mock_repo.get_active_subscribers.return_value = [student]
    mock_db = MagicMock()

    with patch("app.repositories.student.StudentRepository", return_value=mock_repo), \
         patch.object(WordOfDayService, "_load_stored_messages", return_value={"beginner": stored_beginner}):
        svc = WordOfDayService(
            llm_client=mock_llm_client,
            whatsapp_client=mock_wasender_client,
            audit_log=temp_audit_log,
            db_session=mock_db,
        )
        result = svc.run_daily_job(theme="greetings")

    assert result["status"] == "success"
    assert result["sent_count"] == 1
    # LLM must NOT be called when a stored message is available
    mock_llm_client.generate_message_params.assert_not_called()
    mock_wasender_client.send_template_message.assert_called_once()


def test_send_job_falls_back_to_llm_when_no_stored_message(
    mock_llm_client,
    mock_wasender_client,
    temp_audit_log,
):
    """When no stored message exists for a level, the send job generates fresh via LLM."""
    from unittest.mock import MagicMock, patch

    student = MagicMock()
    student.phone_number = "+5511111111111"
    student.first_name = "Ana"
    student.english_level = "beginner"

    mock_repo = MagicMock()
    mock_repo.get_active_subscribers.return_value = [student]
    mock_db = MagicMock()

    # No stored messages — empty dict
    with patch("app.repositories.student.StudentRepository", return_value=mock_repo), \
         patch.object(WordOfDayService, "_load_stored_messages", return_value={}):
        svc = WordOfDayService(
            llm_client=mock_llm_client,
            whatsapp_client=mock_wasender_client,
            audit_log=temp_audit_log,
            db_session=mock_db,
        )
        result = svc.run_daily_job(theme="greetings")

    assert result["status"] == "success"
    assert result["sent_count"] == 1
    # LLM MUST be called as fallback
    mock_llm_client.generate_message_params.assert_called_once_with(
        theme="greetings", level="beginner"
    )



def test_fallback_llm_used_when_primary_fails(
    mock_wasender_client, temp_audit_log
):
    """Test that fallback LLM is tried when primary raises LLMError."""
    from app.integrations.llm_client import LLMError

    primary = Mock()
    primary.generate_message_params.side_effect = LLMError("503 unavailable")

    fallback = Mock()
    fallback.model = "gemini-2.0-flash-lite"
    fallback.generate_message_params.return_value = VALID_PARAMS

    svc = WordOfDayService(
        llm_client=primary,
        fallback_llm_client=fallback,
        whatsapp_client=mock_wasender_client,
        audit_log=temp_audit_log,
        to_number="+5511999999999",
    )
    result = svc.run_daily_job()

    assert result["status"] == "success"
    assert result["sent_count"] == 1
    assert result["used_fallback"] is False  # LLM fallback ≠ hardcoded fallback
    primary.generate_message_params.assert_called_once()
    fallback.generate_message_params.assert_called_once()


def test_no_send_when_both_llms_fail(
    mock_wasender_client, temp_audit_log
):
    """Test that nothing is sent when both primary and fallback LLMs are unavailable."""
    from app.integrations.llm_client import LLMError

    primary = Mock()
    primary.generate_message_params.side_effect = LLMError("503 unavailable")

    fallback = Mock()
    fallback.model = "gemini-2.0-flash-lite"
    fallback.generate_message_params.side_effect = LLMError("503 unavailable")

    svc = WordOfDayService(
        llm_client=primary,
        fallback_llm_client=fallback,
        whatsapp_client=mock_wasender_client,
        audit_log=temp_audit_log,
        to_number="+5511999999999",
    )
    result = svc.run_daily_job()

    assert result["status"] == "error"
    assert result["sent_count"] == 0
    assert result["used_fallback"] is False
    mock_wasender_client.send_template_message.assert_not_called()
    primary.generate_message_params.assert_called_once()
    fallback.generate_message_params.assert_called_once()
