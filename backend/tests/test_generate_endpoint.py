"""Tests for POST /messages/generate and GET /messages/today endpoints."""
import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.routes import app
from app.api.deps import verify_api_key, get_db
from app.db.models.message import LEVELS

TODAY = datetime.date.today()

VALID_PARAMS = {
    "word_phrase": "Thank you",
    "meaning_pt": "Expressão de gratidão.",
    "pronunciation": "thank YOO",
    "when_to_use": "Quando alguém te ajuda.",
    "example_pt": "Obrigado pela ajuda!",
    "example_en": "Thank you for your help!",
}

FORMATTED = (
    "🇺🇸  *Palavra/Frase do Dia:* Thank you\n\n"
    "📝 *Significado:* Expressão de gratidão.\n\n"
    "🔊 *Pronúncia:* thank YOO\n\n"
    "💡 *Quando usar:* Quando alguém te ajuda.\n\n"
    "🇧🇷  *Exemplo:* Obrigado pela ajuda!\n\n"
    "🇺🇸  *Exemplo:* Thank you for your help!\n\n"
    "Envie *STOP* para cancelar o recebimento de mensagens da Palavra/Frase do Dia."
)


@pytest.fixture
def http_client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_overrides():
    app.dependency_overrides[verify_api_key] = lambda: None
    yield
    app.dependency_overrides.clear()


def make_mock_service(valid=True):
    """Return a mock preview service that returns a valid or invalid generation result."""
    svc = MagicMock()
    if valid:
        svc.generate_message.return_value = {
            "valid": True,
            "template_params": VALID_PARAMS,
            "formatted_message": FORMATTED,
            "validation_errors": [],
        }
    else:
        svc.generate_message.return_value = {
            "valid": False,
            "template_params": None,
            "formatted_message": None,
            "validation_errors": ["LLM unavailable — message not sent"],
        }
    return svc


def make_mock_db_and_repo(stored_messages=None):
    """Return a mock DB session and MessageRepository with optional stored messages."""
    stored_messages = stored_messages or []
    mock_db = MagicMock()
    mock_repo = MagicMock()
    mock_repo.get_by_date.return_value = stored_messages
    return mock_db, mock_repo


# ── POST /messages/generate ───────────────────────────────────────────────────

class TestGenerateEndpoint:
    def test_generates_all_levels_by_default(self, http_client):
        mock_db, mock_repo = make_mock_db_and_repo()
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch("app.api.routers.messages.get_preview_service", return_value=make_mock_service()), \
             patch("app.api.routers.messages.MessageRepository", return_value=mock_repo), \
             patch("app.api.routers.messages.get_gcp_scheduler_client", side_effect=Exception("no gcp")), \
             patch("app.config.get_settings", return_value=MagicMock(gcp_project_id="")):
            response = http_client.post("/messages/generate", json={"theme": "travel"})

        assert response.status_code == 200
        body = response.json()
        assert body["date"] == TODAY.isoformat()
        assert len(body["results"]) == len(LEVELS)
        assert all(r["valid"] for r in body["results"])
        assert all(r["formatted_message"] == FORMATTED for r in body["results"])

    def test_generates_single_level_when_specified(self, http_client):
        mock_db, mock_repo = make_mock_db_and_repo()
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch("app.api.routers.messages.get_preview_service", return_value=make_mock_service()), \
             patch("app.api.routers.messages.MessageRepository", return_value=mock_repo), \
             patch("app.api.routers.messages.get_gcp_scheduler_client", side_effect=Exception("no gcp")), \
             patch("app.config.get_settings", return_value=MagicMock(gcp_project_id="")):
            response = http_client.post("/messages/generate", json={"theme": "travel", "level": "beginner"})

        assert response.status_code == 200
        body = response.json()
        assert len(body["results"]) == 1
        assert body["results"][0]["level"] == "beginner"

    def test_upserts_to_repository_on_valid_generation(self, http_client):
        mock_db, mock_repo = make_mock_db_and_repo()
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch("app.api.routers.messages.get_preview_service", return_value=make_mock_service()), \
             patch("app.api.routers.messages.MessageRepository", return_value=mock_repo), \
             patch("app.api.routers.messages.get_gcp_scheduler_client", side_effect=Exception("no gcp")), \
             patch("app.config.get_settings", return_value=MagicMock(gcp_project_id="")):
            http_client.post("/messages/generate", json={"theme": "travel"})

        assert mock_repo.upsert.call_count == len(LEVELS)

    def test_does_not_upsert_on_failed_generation(self, http_client):
        mock_db, mock_repo = make_mock_db_and_repo()
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch("app.api.routers.messages.get_preview_service", return_value=make_mock_service(valid=False)), \
             patch("app.api.routers.messages.MessageRepository", return_value=mock_repo), \
             patch("app.api.routers.messages.get_gcp_scheduler_client", side_effect=Exception("no gcp")), \
             patch("app.config.get_settings", return_value=MagicMock(gcp_project_id="")):
            response = http_client.post("/messages/generate", json={"theme": "travel"})

        assert response.status_code == 200
        body = response.json()
        assert all(not r["valid"] for r in body["results"])
        mock_repo.upsert.assert_not_called()


# ── GET /messages/today ───────────────────────────────────────────────────────

class TestTodayMessagesEndpoint:
    def _make_stored_message(self, level="beginner"):
        msg = MagicMock()
        msg.level = level
        msg.theme = "travel"
        msg.formatted_message = FORMATTED
        msg.updated_at = datetime.datetime(2026, 3, 4, 0, 0, 0)
        return msg

    def test_returns_stored_messages_for_today(self, http_client):
        stored = [self._make_stored_message("beginner"), self._make_stored_message("intermediate")]
        mock_db, mock_repo = make_mock_db_and_repo(stored_messages=stored)
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch("app.api.routers.messages.MessageRepository", return_value=mock_repo):
            response = http_client.get("/messages/today")

        assert response.status_code == 200
        body = response.json()
        assert body["date"] == TODAY.isoformat()
        assert len(body["messages"]) == 2
        assert body["messages"][0]["level"] == "beginner"
        assert body["messages"][0]["formatted_message"] == FORMATTED

    def test_returns_empty_when_no_messages_generated(self, http_client):
        mock_db, mock_repo = make_mock_db_and_repo(stored_messages=[])
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch("app.api.routers.messages.MessageRepository", return_value=mock_repo):
            response = http_client.get("/messages/today")

        assert response.status_code == 200
        body = response.json()
        assert body["messages"] == []
