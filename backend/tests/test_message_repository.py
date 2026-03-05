"""Tests for MessageRepository — upsert and retrieval operations."""
import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models.message import Message
from app.repositories.message import MessageRepository


PARAMS = {
    "word_phrase": "Thank you",
    "meaning_pt": "Expressão de gratidão.",
    "pronunciation": "thank YOO",
    "when_to_use": "Quando alguém te ajuda.",
    "example_pt": "Obrigado pela ajuda!",
    "example_en": "Thank you for your help!",
}
FORMATTED = "🇺🇸 *Palavra/Frase do Dia:* Thank you\n\n..."
TODAY = datetime.date.today()
YESTERDAY = TODAY - datetime.timedelta(days=1)


@pytest.fixture
def session():
    """In-memory SQLite session with the messages table created fresh per test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def repo(session):
    return MessageRepository(session)


class TestMessageRepositoryUpsert:
    def test_insert_new_row(self, repo, session):
        msg = repo.upsert(TODAY, "beginner", "travel", PARAMS, FORMATTED)
        assert msg.id is not None
        assert msg.date == TODAY
        assert msg.level == "beginner"
        assert msg.theme == "travel"
        assert msg.template_params == PARAMS
        assert msg.formatted_message == FORMATTED

    def test_update_existing_row(self, repo, session):
        repo.upsert(TODAY, "beginner", "travel", PARAMS, FORMATTED)
        updated_params = {**PARAMS, "word_phrase": "Excuse me"}
        updated_msg = "🇺🇸 *Palavra/Frase do Dia:* Excuse me\n\n..."

        msg = repo.upsert(TODAY, "beginner", "travel", updated_params, updated_msg)

        assert msg.template_params["word_phrase"] == "Excuse me"
        assert msg.formatted_message == updated_msg
        assert session.query(Message).count() == 1  # no duplicate rows

    def test_different_levels_create_separate_rows(self, repo, session):
        repo.upsert(TODAY, "beginner", "travel", PARAMS, FORMATTED)
        repo.upsert(TODAY, "intermediate", "travel", PARAMS, FORMATTED)
        repo.upsert(TODAY, "advanced", "travel", PARAMS, FORMATTED)
        assert session.query(Message).count() == 3

    def test_different_dates_create_separate_rows(self, repo, session):
        repo.upsert(TODAY, "beginner", "travel", PARAMS, FORMATTED)
        repo.upsert(YESTERDAY, "beginner", "travel", PARAMS, FORMATTED)
        assert session.query(Message).count() == 2


class TestMessageRepositoryGetByDate:
    def test_returns_messages_for_date(self, repo):
        repo.upsert(TODAY, "beginner", "travel", PARAMS, FORMATTED)
        repo.upsert(TODAY, "intermediate", "travel", PARAMS, FORMATTED)
        results = repo.get_by_date(TODAY)
        assert len(results) == 2

    def test_excludes_other_dates(self, repo):
        repo.upsert(YESTERDAY, "beginner", "travel", PARAMS, FORMATTED)
        results = repo.get_by_date(TODAY)
        assert results == []

    def test_returns_empty_when_none(self, repo):
        assert repo.get_by_date(TODAY) == []

    def test_ordered_by_level(self, repo):
        repo.upsert(TODAY, "intermediate", "travel", PARAMS, FORMATTED)
        repo.upsert(TODAY, "advanced", "travel", PARAMS, FORMATTED)
        repo.upsert(TODAY, "beginner", "travel", PARAMS, FORMATTED)
        results = repo.get_by_date(TODAY)
        levels = [m.level for m in results]
        assert levels == sorted(levels)


class TestMessageRepositoryGetByDateAndLevel:
    def test_returns_correct_message(self, repo):
        repo.upsert(TODAY, "beginner", "travel", PARAMS, FORMATTED)
        msg = repo.get_by_date_and_level(TODAY, "beginner")
        assert msg is not None
        assert msg.level == "beginner"

    def test_returns_none_for_missing_level(self, repo):
        repo.upsert(TODAY, "beginner", "travel", PARAMS, FORMATTED)
        assert repo.get_by_date_and_level(TODAY, "intermediate") is None

    def test_returns_none_for_missing_date(self, repo):
        repo.upsert(TODAY, "beginner", "travel", PARAMS, FORMATTED)
        assert repo.get_by_date_and_level(YESTERDAY, "beginner") is None
