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


def test_fallback_used_after_max_retries(service, mock_llm_client, mock_wasender_client):
    """Test that fallback is used after validation fails on all retry attempts."""
    # All attempts return invalid params
    invalid_params = {**VALID_PARAMS, "word_phrase": ""}
    mock_llm_client.generate_message_params.return_value = invalid_params
    mock_llm_client.generate_repair_message_params.return_value = invalid_params

    result = service.run_daily_job()

    # Should use fallback
    assert result["sent_count"] == 1
    assert result["used_fallback"] is True


def test_preview_generates_and_validates_without_sending(
    service,
    mock_llm_client,
    mock_wasender_client,
):
    """Test preview mode generates and validates but does not send."""
    result = service.preview_message(theme="work", level="intermediate")

    # LLM should be called
    mock_llm_client.generate_message_params.assert_called_once_with(
        theme="work",
        level="intermediate",
    )

    # WaSender should NOT be called
    mock_wasender_client.send_template_message.assert_not_called()

    # Result should show validation status
    assert result["valid"] is True
    assert result["content"] == VALID_PARAMS
    assert result["validation_errors"] == []

    # No audit log entries for preview
    events = service.audit_log.get_today_events()
    assert len(events) == 0
