# Changelog

All notable changes to the XOXO Education Backend will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## \[0.2.0\] - 2025-11-20

### Added - Authentication & Authorization System

#### 🔐 Security Infrastructure

* **Password Security**
  * Bcrypt password hashing with unique salts per password
  * Password strength validation (12+ chars, uppercase, lowercase, digit, special char)
  * Secure password storage (never store plain text)
* **JWT Token System**
  * Access tokens (30 minute expiration)
  * Refresh tokens (7 day expiration)
  * Token type verification (access vs refresh)
  * Token payload includes user ID and admin status
* **Production Safety**
  * SECRET_KEY validation (fails on default in production)
  * Environment-based configuration
  * Token expiration enforcement

#### 👥 User Management

* **User Model Extensions**
  * `hashed_password` field for credential storage
  * `is_admin` boolean field for role-based access control
  * All existing fields preserved (email, first_name, last_name, phone, is_active)
* **Admin-Only Provisioning**
  * No public user registration (security-first approach)
  * All user CRUD operations require admin privileges
  * Admins can create users with passwords
  * Password validation on user creation

#### 🔌 API Endpoints

**Authentication** (`/api/v1/auth`)

* `POST /login` - Email/password authentication → JWT tokens
* `POST /refresh` - Refresh token → new access/refresh tokens
* `GET /me` - Get current authenticated user profile

**User Management** (`/api/v1/users`) - All endpoints now require admin authentication

* `POST /` - Create user (with password hashing)
* `GET /` - List users with pagination
* `GET /{user_id}` - Get user by ID
* `PUT /{user_id}` - Update user
* `DELETE /{user_id}` - Delete user
* `POST /{user_id}/deactivate` - Soft delete user

#### 🏗️ Architecture Components

**Core Modules** (`app/core/`)

* `security.py` - Password hashing, JWT creation/verification, password validation
* `config.py` - Extended with refresh token settings and SECRET_KEY validation
* `deps.py` - Auth dependencies: `get_current_user`, `get_current_active_user`, `require_admin`

**Services** (`app/services/`)

* `auth.py` - Authentication business logic (login, refresh, user verification)
* `user.py` - Updated to hash passwords on creation with strength validation

**Schemas** (`app/schemas/`)

* `auth.py` - `LoginRequest`, `TokenResponse`, `RefreshRequest`, `TokenPayload`
* `user.py` - Added `password` field to `UserCreate`, `is_admin` to all schemas

**Database**

* Alembic migration: `2025_11_19_1600-001_initial_user_table_with_auth.py`
* Adds `hashed_password` and `is_admin` columns to users table

#### 🧪 Testing

* **Unit Tests** (`tests/unit/test_security.py`)
  * 20 test cases covering password hashing, JWT tokens, validation
  * Tests for password strength validation (all requirements)
  * Tests for token creation, verification, expiration
  * Tests for custom expiration times
* **Test Fixtures** (`tests/conftest.py`)
  * `test_user` - Regular user with hashed password
  * `test_admin` - Admin user with privileges
  * `user_token` - Valid access token for regular user
  * `admin_token` - Valid access token for admin
* **Future Testing**
  * Functional/integration tests to be added in future releases

#### 📚 Documentation

* `README.md` - Complete backend documentation with authentication guide
  * API endpoint documentation with examples
  * Getting started guide
  * Testing instructions
  * Security considerations
  * Troubleshooting guide
* `CHANGELOG.md` - Project changelog (this file)

#### 🛠️ Tooling

* `scripts/create_admin.py` - Interactive admin user creation script
  * Password validation
  * Email uniqueness checking
  * User-friendly prompts

#### 📦 Dependencies Added

* `bcrypt = "^4.1.2"` - Password hashing
* `passlib = "^1.7.4"` - Password hashing framework
* `python-jose[cryptography] = "^3.3.0"` - JWT token handling
* `python-multipart = "^0.0.6"` - Form data parsing

### Changed

* **User Endpoints**: All user management endpoints now require admin authentication
* **User Creation**: Now requires password field and validates strength
* **User Schemas**: Extended with `is_admin` field across all schemas
* **Dockerfile**: Added `scripts/` directory to container image

### Security

* ✅ Passwords hashed with bcrypt (never stored in plain text)
* ✅ JWT tokens with expiration
* ✅ Admin-only user management (no public registration)
* ✅ Password complexity requirements enforced
* ✅ Production SECRET_KEY validation
* ✅ Token type verification (prevents access token used as refresh)
* ✅ Inactive user account protection


---

## \[0.1.0\] - 2025-11-19

### Added - Initial Release

#### Base Infrastructure

* FastAPI application with async support
* PostgreSQL database with async SQLAlchemy 2.0
* Alembic database migrations
* Docker Compose development environment
* Layered architecture (API → Services → Repositories → Models)

#### User Management (No Auth)

* User CRUD endpoints (create, read, update, delete)
* User soft delete (deactivation)
* Email uniqueness validation
* Pagination support

#### API Features

* Health check endpoints (`/health`, `/health/db`)
* OpenAPI/Swagger documentation (`/docs`)
* ReDoc documentation (`/redoc`)
* CORS configuration
* Exception handling

#### Testing

* Pytest setup with async support
* Test fixtures for database and HTTP client
* Basic health endpoint tests

#### Development Tools

* Black code formatting
* Ruff linting
* Mypy type checking
* Pre-commit hooks support


---

## Future Considerations

### Potential Enhancements (Not Implemented)

* Token blacklist/revocation for logout
* Rate limiting on authentication endpoints
* Multi-factor authentication (MFA)
* OAuth2/OIDC integration
* Email verification for new users
* Password reset flow
* Audit logging for admin actions
* IP-based access controls
* Session management

### Deferred Features

* Public user registration (currently admin-only)
* Role-based permissions beyond admin/user
* User profile pictures
* Email notifications
* Account lockout after failed attempts


---

## Migration Guide

### From 0.1.0 to 0.2.0

**Prerequisites:**


1. Backup your database
2. Update dependencies: `poetry install`
3. Generate secure SECRET_KEY for production

**Migration Steps:**


1. Run database migration: `alembic upgrade head`
2. Create first admin user: `python scripts/create_admin.py`
3. Update environment variables (add SECRET_KEY for production)
4. Test authentication flow
5. Update frontend to use new auth endpoints

**Breaking Changes:**

* All user management endpoints now require admin authentication
* User creation now requires `password` field in request body
* User responses now include `is_admin` field

**Deprecations:**

* None


---

## Support

For questions or issues:

* Review complete documentation in [README.md](README.md)
* Check code comments in `app/core/security.py` and `app/services/auth.py`
* Run tests: `pytest` or `docker compose exec app pytest`
* Visit interactive API docs: http://localhost:8000/docs
* See root project documentation: [../README.md](../README.md)


