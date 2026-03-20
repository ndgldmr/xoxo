"""Tests for POST /auth/login and JWT-protected route enforcement."""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.api.routes import app
from app.api.deps import verify_api_key, verify_jwt, get_db
from app.security import hash_password, create_access_token

_TEST_SECRET = "test-secret-key-for-tests"
_TEST_EMAIL = "admin@xoxo.com"
_TEST_PASSWORD = "correct-password"


@pytest.fixture
def http_client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_overrides():
    app.dependency_overrides[verify_api_key] = lambda: None
    yield
    app.dependency_overrides.clear()


def _make_admin(email=_TEST_EMAIL, password=_TEST_PASSWORD):
    admin = MagicMock()
    admin.email = email
    admin.hashed_password = hash_password(password)
    return admin


def _make_mock_settings(jwt_secret=_TEST_SECRET):
    s = MagicMock()
    s.jwt_secret_key = jwt_secret
    s.jwt_algorithm = "HS256"
    s.jwt_expire_hours = 8
    return s


# ── POST /auth/login ──────────────────────────────────────────────────────────

class TestLogin:
    def test_valid_credentials_returns_token(self, http_client):
        mock_db = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_by_email.return_value = _make_admin()
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch("app.api.routers.auth.AdminRepository", return_value=mock_repo), \
             patch("app.api.routers.auth.get_settings", return_value=_make_mock_settings()):
            response = http_client.post("/auth/login", json={
                "email": _TEST_EMAIL,
                "password": _TEST_PASSWORD,
            })

        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    def test_wrong_password_returns_401(self, http_client):
        mock_db = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_by_email.return_value = _make_admin()
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch("app.api.routers.auth.AdminRepository", return_value=mock_repo), \
             patch("app.api.routers.auth.get_settings", return_value=_make_mock_settings()):
            response = http_client.post("/auth/login", json={
                "email": _TEST_EMAIL,
                "password": "wrong-password",
            })

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid email or password"

    def test_unknown_email_returns_401(self, http_client):
        mock_db = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_by_email.return_value = None
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch("app.api.routers.auth.AdminRepository", return_value=mock_repo), \
             patch("app.api.routers.auth.get_settings", return_value=_make_mock_settings()):
            response = http_client.post("/auth/login", json={
                "email": "unknown@xoxo.com",
                "password": _TEST_PASSWORD,
            })

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid email or password"

    def test_error_message_same_for_wrong_password_and_unknown_email(self, http_client):
        """Don't reveal whether email exists or password is wrong."""
        mock_db = MagicMock()
        mock_repo_unknown = MagicMock()
        mock_repo_unknown.get_by_email.return_value = None
        mock_repo_wrong_pw = MagicMock()
        mock_repo_wrong_pw.get_by_email.return_value = _make_admin()
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch("app.api.routers.auth.AdminRepository", return_value=mock_repo_unknown), \
             patch("app.api.routers.auth.get_settings", return_value=_make_mock_settings()):
            r1 = http_client.post("/auth/login", json={"email": "x@x.com", "password": "pw"})

        with patch("app.api.routers.auth.AdminRepository", return_value=mock_repo_wrong_pw), \
             patch("app.api.routers.auth.get_settings", return_value=_make_mock_settings()):
            r2 = http_client.post("/auth/login", json={"email": _TEST_EMAIL, "password": "wrong"})

        assert r1.json()["detail"] == r2.json()["detail"]


# ── JWT-protected route enforcement ───────────────────────────────────────────

class TestJWTProtection:
    def _valid_token(self) -> str:
        return create_access_token(
            email=_TEST_EMAIL,
            secret=_TEST_SECRET,
            algorithm="HS256",
            expire_hours=8,
        )

    def test_valid_token_allows_access(self, http_client):
        """A valid JWT should give access to a JWT-protected route."""
        mock_db = MagicMock()
        mock_repo = MagicMock()
        mock_repo.list_all.return_value = []
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch("app.api.routers.students.StudentRepository", return_value=mock_repo), \
             patch("app.api.deps.get_settings", return_value=_make_mock_settings()):
            response = http_client.get(
                "/students",
                headers={"Authorization": f"Bearer {self._valid_token()}"},
            )

        assert response.status_code == 200

    def test_missing_token_returns_401_when_secret_set(self, http_client):
        """No token + JWT_SECRET_KEY set → 401."""
        with patch("app.api.deps.get_settings", return_value=_make_mock_settings()):
            response = http_client.get("/students")

        assert response.status_code == 401

    def test_invalid_token_returns_401(self, http_client):
        """Tampered/garbage token → 401."""
        with patch("app.api.deps.get_settings", return_value=_make_mock_settings()):
            response = http_client.get(
                "/students",
                headers={"Authorization": "Bearer not.a.real.token"},
            )

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid or expired token"
