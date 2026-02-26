"""Tests for the student enrollment feature.

Covers:
- normalize_phone() utility
- WaSenderClient.send_welcome_message()
- POST /students endpoint (phone normalization, welcome message, edge cases)
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.api.routes import app, normalize_phone
from app.integrations.wasender_client import WaSenderClient


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_mock_student(
    phone="+5511999999999",
    first_name="Ana",
    last_name="Silva",
    english_level="beginner",
    whatsapp_messages=True,
    is_active=True,
):
    student = MagicMock()
    student.phone_number = phone
    student.first_name = first_name
    student.last_name = last_name
    student.english_level = english_level
    student.whatsapp_messages = whatsapp_messages
    student.is_active = is_active
    return student


@pytest.fixture
def http_client():
    return TestClient(app)


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.api_key = None          # disable API key auth in tests
    settings.wasender_api_key = "test_wasender_key"
    settings.dry_run = True
    settings.database_url = "postgresql://test"
    return settings


# ── normalize_phone ───────────────────────────────────────────────────────────

class TestNormalizePhone:
    def test_valid_e164_unchanged(self):
        assert normalize_phone("+5511999999999") == "+5511999999999"

    def test_strips_spaces(self):
        assert normalize_phone("+1 555 123 4567") == "+15551234567"

    def test_strips_dashes(self):
        assert normalize_phone("+1-555-123-4567") == "+15551234567"

    def test_strips_parens_and_spaces(self):
        assert normalize_phone("+1 (555) 123-4567") == "+15551234567"

    def test_strips_dots(self):
        assert normalize_phone("+1.555.123.4567") == "+15551234567"

    def test_strips_surrounding_whitespace(self):
        assert normalize_phone("  +5511999999999  ") == "+5511999999999"

    def test_adds_plus_if_missing(self):
        assert normalize_phone("5511999999999") == "+5511999999999"

    def test_too_short_raises(self):
        with pytest.raises(ValueError, match="E.164"):
            normalize_phone("+12345")  # only 5 digits

    def test_too_long_raises(self):
        with pytest.raises(ValueError, match="E.164"):
            normalize_phone("+1234567890123456")  # 16 digits

    def test_letters_in_number_raises(self):
        with pytest.raises(ValueError, match="E.164"):
            normalize_phone("+123abc456")

    def test_minimum_valid_length(self):
        assert normalize_phone("+1234567") == "+1234567"  # 7 digits

    def test_maximum_valid_length(self):
        assert normalize_phone("+123456789012345") == "+123456789012345"  # 15 digits


# ── WaSenderClient.send_welcome_message ──────────────────────────────────────

class TestSendWelcomeMessage:
    def setup_method(self):
        self.client = WaSenderClient(api_key="test_key", dry_run=True)

    def test_includes_first_name_in_greeting(self):
        with patch.object(self.client, "send_message", return_value={"status": "dry_run"}) as mock_send:
            self.client.send_welcome_message("+5511999999999", first_name="Ana")
            message = mock_send.call_args.kwargs["message"]
            assert "Ana" in message

    def test_generic_greeting_without_name(self):
        with patch.object(self.client, "send_message", return_value={"status": "dry_run"}) as mock_send:
            self.client.send_welcome_message("+5511999999999")
            message = mock_send.call_args.kwargs["message"]
            assert "Olá!" in message

    def test_message_has_two_paragraphs(self):
        with patch.object(self.client, "send_message", return_value={"status": "dry_run"}) as mock_send:
            self.client.send_welcome_message("+5511999999999", first_name="João")
            message = mock_send.call_args.kwargs["message"]
            assert "\n\n" in message

    def test_message_mentions_stop(self):
        with patch.object(self.client, "send_message", return_value={"status": "dry_run"}) as mock_send:
            self.client.send_welcome_message("+5511999999999")
            message = mock_send.call_args.kwargs["message"]
            assert "STOP" in message

    def test_sends_to_correct_number(self):
        with patch.object(self.client, "send_message", return_value={"status": "dry_run"}) as mock_send:
            self.client.send_welcome_message("+5511999999999", first_name="Ana")
            assert mock_send.call_args.kwargs["to_number"] == "+5511999999999"


# ── POST /students endpoint ───────────────────────────────────────────────────

class TestAddStudentEndpoint:
    def test_creates_student_and_sends_welcome(self, http_client, mock_settings):
        student = make_mock_student()
        mock_repo = MagicMock()
        mock_repo.get_by_phone.return_value = None
        mock_repo.create.return_value = student
        mock_wasender = MagicMock()

        with patch("app.api.routes.get_db_session"), \
             patch("app.api.routes.StudentRepository", return_value=mock_repo), \
             patch("app.api.routes.get_settings", return_value=mock_settings), \
             patch("app.api.routes.WaSenderClient", return_value=mock_wasender):

            response = http_client.post("/students", json={
                "phone_number": "+5511999999999",
                "first_name": "Ana",
                "last_name": "Silva",
                "english_level": "beginner",
            })

        assert response.status_code == 201
        assert response.json()["phone_number"] == "+5511999999999"
        mock_wasender.send_welcome_message.assert_called_once_with(
            to_number="+5511999999999",
            first_name="Ana",
        )

    def test_normalizes_formatted_phone_before_saving(self, http_client, mock_settings):
        student = make_mock_student(phone="+15551234567")
        mock_repo = MagicMock()
        mock_repo.get_by_phone.return_value = None
        mock_repo.create.return_value = student
        mock_wasender = MagicMock()

        with patch("app.api.routes.get_db_session"), \
             patch("app.api.routes.StudentRepository", return_value=mock_repo), \
             patch("app.api.routes.get_settings", return_value=mock_settings), \
             patch("app.api.routes.WaSenderClient", return_value=mock_wasender):

            response = http_client.post("/students", json={
                "phone_number": "+1 (555) 123-4567",
                "english_level": "beginner",
            })

        assert response.status_code == 201
        mock_repo.get_by_phone.assert_called_once_with("+15551234567")

    def test_duplicate_phone_returns_409(self, http_client, mock_settings):
        mock_repo = MagicMock()
        mock_repo.get_by_phone.return_value = make_mock_student()

        with patch("app.api.routes.get_db_session"), \
             patch("app.api.routes.StudentRepository", return_value=mock_repo), \
             patch("app.api.routes.get_settings", return_value=mock_settings):

            response = http_client.post("/students", json={
                "phone_number": "+5511999999999",
                "english_level": "beginner",
            })

        assert response.status_code == 409

    def test_invalid_phone_returns_422(self, http_client, mock_settings):
        with patch("app.api.routes.get_settings", return_value=mock_settings):
            response = http_client.post("/students", json={
                "phone_number": "not-a-phone",
                "english_level": "beginner",
            })

        assert response.status_code == 422
        assert "E.164" in response.json()["detail"][0]["msg"]

    def test_welcome_message_failure_does_not_block_enrollment(self, http_client, mock_settings):
        student = make_mock_student()
        mock_repo = MagicMock()
        mock_repo.get_by_phone.return_value = None
        mock_repo.create.return_value = student
        mock_wasender = MagicMock()
        mock_wasender.send_welcome_message.side_effect = Exception("WaSender timeout")

        with patch("app.api.routes.get_db_session"), \
             patch("app.api.routes.StudentRepository", return_value=mock_repo), \
             patch("app.api.routes.get_settings", return_value=mock_settings), \
             patch("app.api.routes.WaSenderClient", return_value=mock_wasender):

            response = http_client.post("/students", json={
                "phone_number": "+5511999999999",
                "english_level": "beginner",
            })

        assert response.status_code == 201

    def test_no_welcome_message_when_whatsapp_disabled(self, http_client, mock_settings):
        student = make_mock_student(whatsapp_messages=False)
        mock_repo = MagicMock()
        mock_repo.get_by_phone.return_value = None
        mock_repo.create.return_value = student
        mock_wasender = MagicMock()

        with patch("app.api.routes.get_db_session"), \
             patch("app.api.routes.StudentRepository", return_value=mock_repo), \
             patch("app.api.routes.get_settings", return_value=mock_settings), \
             patch("app.api.routes.WaSenderClient", return_value=mock_wasender):

            response = http_client.post("/students", json={
                "phone_number": "+5511999999999",
                "english_level": "beginner",
                "whatsapp_messages": False,
            })

        assert response.status_code == 201
        mock_wasender.send_welcome_message.assert_not_called()
