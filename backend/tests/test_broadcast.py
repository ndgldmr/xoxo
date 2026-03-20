"""Tests for POST /broadcast — send an announcement to active WhatsApp subscribers.

Covers:
- Sends to all active, opted-in subscribers
- Level filter is passed through to the repository
- Null level queries all levels
- Partial send failures are counted correctly
- No subscribers → zero counts, no sends attempted
- No database configured → 503
- Empty message body → 422
- DB session is always closed (even on success)
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.api.routes import app
from app.api.deps import verify_api_key, verify_jwt


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_mock_student(phone="+5511999999999", english_level="beginner"):
    s = MagicMock()
    s.phone_number = phone
    s.english_level = english_level
    return s


@pytest.fixture
def http_client():
    return TestClient(app)


@pytest.fixture
def mock_settings():
    s = MagicMock()
    s.api_key = None                         # disable API key auth in tests
    s.wasender_api_key = "test_key"
    s.dry_run = True
    s.database_url = "postgresql://test"
    s.send_delay_seconds = 0
    return s


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    """Bypass auth and clean up all overrides after each test."""
    app.dependency_overrides[verify_api_key] = lambda: None
    app.dependency_overrides[verify_jwt] = lambda: "test@xoxo.com"
    yield
    app.dependency_overrides.clear()


# Patch targets — all are imported inside the endpoint function body,
# so we patch them at their source modules.
_SETTINGS = "app.config.get_settings"
_WASENDER = "app.integrations.wasender_client.WaSenderClient"
_REPO = "app.repositories.student.StudentRepository"
_SESSION_FACTORY = "app.db.session._get_session_factory"


def _make_session_patches(mock_settings, students, send_side_effect=None):
    """Build the four mocks needed for a broadcast endpoint call."""
    mock_wasender = MagicMock()
    if send_side_effect is not None:
        mock_wasender.send_message.side_effect = send_side_effect

    mock_repo = MagicMock()
    mock_repo.get_active_subscribers.return_value = students

    mock_session = MagicMock()
    mock_factory = MagicMock(return_value=mock_session)

    return mock_wasender, mock_repo, mock_session, mock_factory


# ── POST /broadcast ───────────────────────────────────────────────────────────

class TestBroadcastEndpoint:
    def test_sends_to_all_active_subscribers(self, http_client, mock_settings):
        students = [
            make_mock_student("+5511111111111"),
            make_mock_student("+5522222222222"),
        ]
        mock_wasender, mock_repo, mock_session, mock_factory = _make_session_patches(
            mock_settings, students
        )

        with patch(_SETTINGS, return_value=mock_settings), \
             patch(_WASENDER, return_value=mock_wasender), \
             patch(_REPO, return_value=mock_repo), \
             patch(_SESSION_FACTORY, return_value=mock_factory):
            response = http_client.post("/broadcast", json={"message": "Hello everyone!"})

        assert response.status_code == 200
        body = response.json()
        assert body["sent_count"] == 2
        assert body["failed_count"] == 0
        assert body["total_recipients"] == 2
        assert mock_wasender.send_message.call_count == 2

    def test_filters_recipients_by_level(self, http_client, mock_settings):
        students = [make_mock_student(english_level="intermediate")]
        mock_wasender, mock_repo, mock_session, mock_factory = _make_session_patches(
            mock_settings, students
        )

        with patch(_SETTINGS, return_value=mock_settings), \
             patch(_WASENDER, return_value=mock_wasender), \
             patch(_REPO, return_value=mock_repo), \
             patch(_SESSION_FACTORY, return_value=mock_factory):
            response = http_client.post(
                "/broadcast", json={"message": "Hi!", "level": "intermediate"}
            )

        assert response.status_code == 200
        mock_repo.get_active_subscribers.assert_called_once_with(level="intermediate")

    def test_null_level_queries_all_levels(self, http_client, mock_settings):
        students = [make_mock_student()]
        mock_wasender, mock_repo, mock_session, mock_factory = _make_session_patches(
            mock_settings, students
        )

        with patch(_SETTINGS, return_value=mock_settings), \
             patch(_WASENDER, return_value=mock_wasender), \
             patch(_REPO, return_value=mock_repo), \
             patch(_SESSION_FACTORY, return_value=mock_factory):
            response = http_client.post("/broadcast", json={"message": "Hi!", "level": None})

        assert response.status_code == 200
        mock_repo.get_active_subscribers.assert_called_once_with(level=None)

    def test_partial_failure_returns_correct_counts(self, http_client, mock_settings):
        students = [
            make_mock_student("+5511111111111"),
            make_mock_student("+5522222222222"),
            make_mock_student("+5533333333333"),
        ]
        mock_wasender, mock_repo, mock_session, mock_factory = _make_session_patches(
            mock_settings,
            students,
            send_side_effect=[
                {"status": "sent"},
                Exception("WaSender timeout"),
                {"status": "sent"},
            ],
        )

        with patch(_SETTINGS, return_value=mock_settings), \
             patch(_WASENDER, return_value=mock_wasender), \
             patch(_REPO, return_value=mock_repo), \
             patch(_SESSION_FACTORY, return_value=mock_factory):
            response = http_client.post("/broadcast", json={"message": "Hello!"})

        assert response.status_code == 200
        body = response.json()
        assert body["sent_count"] == 2
        assert body["failed_count"] == 1
        assert body["total_recipients"] == 3

    def test_no_active_subscribers_returns_zero_counts(self, http_client, mock_settings):
        mock_wasender, mock_repo, mock_session, mock_factory = _make_session_patches(
            mock_settings, students=[]
        )

        with patch(_SETTINGS, return_value=mock_settings), \
             patch(_WASENDER, return_value=mock_wasender), \
             patch(_REPO, return_value=mock_repo), \
             patch(_SESSION_FACTORY, return_value=mock_factory):
            response = http_client.post("/broadcast", json={"message": "Hi!"})

        assert response.status_code == 200
        body = response.json()
        assert body["sent_count"] == 0
        assert body["failed_count"] == 0
        assert body["total_recipients"] == 0
        mock_wasender.send_message.assert_not_called()

    def test_no_database_returns_503(self, http_client, mock_settings):
        mock_settings.database_url = None

        with patch(_SETTINGS, return_value=mock_settings):
            response = http_client.post("/broadcast", json={"message": "Hi!"})

        assert response.status_code == 503

    def test_empty_message_returns_422(self, http_client):
        response = http_client.post("/broadcast", json={"message": ""})
        assert response.status_code == 422

    def test_db_session_is_always_closed(self, http_client, mock_settings):
        mock_wasender, mock_repo, mock_session, mock_factory = _make_session_patches(
            mock_settings, students=[]
        )

        with patch(_SETTINGS, return_value=mock_settings), \
             patch(_WASENDER, return_value=mock_wasender), \
             patch(_REPO, return_value=mock_repo), \
             patch(_SESSION_FACTORY, return_value=mock_factory):
            http_client.post("/broadcast", json={"message": "Hi!"})

        mock_session.close.assert_called_once()
