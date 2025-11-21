# Changelog

All notable changes to the XOXO Education Backend will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## \[0.4.0\] - 2025-11-21

### Added - Student Messaging Preferences

#### 📊 Data Modeling for Future AI Messaging

This release focuses exclusively on extending the Student domain with data fields needed to support future daily AI-generated WhatsApp message delivery. **NO messaging logic, NO AI integration, NO scheduling** - only data modeling and validation.

#### 🎯 New Student Fields (Messaging Preferences)

**Proficiency Level**

* `proficiency_level` (VARCHAR, required on creation)
  * Allowed values: `beginner`, `intermediate`, `advanced`
  * Python-side validation (no Postgres ENUM)
  * Case-insensitive validation, normalized to lowercase
  * Used for future AI content targeting

**Native Language**

* `native_language` (VARCHAR, default: `"pt-BR"`)
  * Free-form string for flexibility
  * Will be used for bilingual explanations in future messaging
  * Default reflects primary student demographic (Brazilian Portuguese speakers)

**Daily Message Opt-In**

* `wants_daily_message` (BOOLEAN, default: `false`)
  * Opt-in model for daily messaging
  * When `true`, requires `timezone` and `daily_message_time_local`

**Scheduling Preferences**

* `daily_message_time_local` (TIME, nullable)
  * Preferred time for daily message in student's local timezone
  * Accepts any valid time (00:00 - 23:59)
  * Required when `wants_daily_message=true`
* `timezone` (VARCHAR, nullable)
  * IANA timezone identifier (e.g., `America/Sao_Paulo`, `America/New_York`)
  * Strict validation using Python's `zoneinfo`
  * Required when `wants_daily_message=true`

#### ✅ Validation & Business Rules

**Schema-Level Validation** (`app/schemas/student.py`)

* Proficiency level must be one of: `beginner`, `intermediate`, `advanced`
* Timezone must be valid IANA timezone (strict `zoneinfo` validation)
* Cross-field validation: If `wants_daily_message=true` → `timezone` and `daily_message_time_local` required
* All validation in `StudentCreate` and `StudentUpdate` schemas

**Service-Level Validation** (`app/services/student.py`)

* When updating `wants_daily_message` to `true`, validates that timezone/time are set
* Checks both update data and existing student record to ensure completeness
* Raises `ValueError` with clear error messages for validation failures

#### 🏗️ Architecture Changes

**Models** (`app/models/student.py`)

* Added 5 new columns to Student model
* All fields use appropriate SQLAlchemy types (String, Boolean, Time)
* Includes database-level comments for documentation

**Schemas** (`app/schemas/student.py`)

* `StudentBase`: Added all 5 new fields with descriptions
* `StudentCreate`:
  * `proficiency_level` is required
  * `native_language` defaults to `"pt-BR"`
  * `wants_daily_message` defaults to `false`
  * Cross-field validation via `model_post_init`
* `StudentUpdate`: All fields optional (PATCH-style updates)
* Field validators for proficiency_level and timezone

**Services** (`app/services/student.py`)

* Enhanced `update_student()` with messaging preference validation
* Validates cross-field dependencies during updates
* Clear error messages for validation failures

**Database**

* Alembic migration: `2025_11_21_1701-336052308553_add_student_messaging_prefs.py`
* Adds 5 columns with safe defaults for existing records
* Migration uses temporary server defaults, then removes them
* Clean upgrade and downgrade paths

#### 🧪 Testing

**Unit Tests** (`tests/unit/test_services/test_student.py`)

* 25+ new test cases for Phase 0 functionality:
  * Proficiency level validation (valid/invalid values, case-insensitivity)
  * Native language defaults and overrides
  * Timezone validation (valid IANA timezones, invalid formats)
  * Cross-field validation for `wants_daily_message`
  * Time acceptance (all valid times 00:00 - 23:59)
  * StudentUpdate schema validation
  * Service-level business rules for updates
  * Edge cases for updating wants_daily_message

**Test Coverage:**

* ✅ Valid proficiency levels accepted (beginner, intermediate, advanced)
* ✅ Invalid proficiency levels rejected (expert, novice, etc.)
* ✅ Proficiency level validation is case-insensitive
* ✅ proficiency_level required on creation
* ✅ native_language defaults to "pt-BR"
* ✅ native_language can be overridden
* ✅ wants_daily_message defaults to false
* ✅ Valid IANA timezones accepted
* ✅ Invalid timezones rejected
* ✅ wants_daily_message=true requires timezone and time
* ✅ wants_daily_message=false allows missing fields
* ✅ Any valid time accepted (00:00 - 23:59)
* ✅ Update validation with existing student data
* ✅ Update validation with provided fields in request

#### 📚 Documentation

**README Updates**

* `xoxo/README.md`: Added Phase 0 messaging preferences to Student Tracking section
* `backend/README.md`: Comprehensive documentation of new fields
  * Updated Student API examples with messaging preferences
  * Added required vs optional field documentation
  * Added validation error examples
  * Documented timezone format requirements
  * Included examples with and without messaging preferences

**CHANGELOG**

* Detailed Phase 0 entry (this section!)

#### 🔍 Technical Details

**Migration Strategy**

* Safe defaults used during migration to avoid breaking existing rows
* `proficiency_level`: server default `"beginner"` during migration
* `native_language`: server default `"pt-BR"`
* `wants_daily_message`: server default `false`
* Server defaults removed after column addition (app-level defaults for future inserts)

**Validation Approach**

* VARCHAR for proficiency_level (not ENUM) for flexibility
* Strict IANA timezone validation using `zoneinfo`
* Pydantic v2 validators with `model_post_init` for cross-field checks
* Service-level validation for update operations
* Clear, actionable error messages

**Data Integrity**

* Cross-field validation ensures data consistency
* PATCH-style updates allow partial modifications
* Timezone validation prevents invalid data at creation time
* Service layer validates updates against existing state

#### 🚀 Future Phases (Not in This Release)

Phase 0 is **data modeling only**. Future phases will add:

* **Phase 1**: AI content generation logic
* **Phase 2**: WhatsApp integration
* **Phase 3**: Scheduling and delivery system
* **Phase 4**: Analytics and tracking

### Changed

* Student model extended with 5 new fields for messaging preferences
* Student schemas updated to include messaging fields with validation
* Student service enhanced with cross-field validation logic

### Technical Notes

* Uses `zoneinfo` (Python 3.9+) for timezone validation
* All new fields are non-nullable except `daily_message_time_local` and `timezone`
* Migration is backward-compatible with existing student records
* No API endpoint changes required (automatic schema updates)


---

## \[0.3.0\] - 2025-11-21

### Added - Student Tracking System

#### 👨‍🎓 Student Management

* **Student Model** (`app/models/student.py`)
  * Students are NOT system users (no authentication/login)
  * Fields: `id`, `email`, `first_name`, `last_name`, `phone_number`, `country`, `is_active`
  * Automatic timestamp tracking (`created_at`, `updated_at`)
  * Email uniqueness constraint with indexing
  * Phone number uniqueness constraint with indexing
  * Soft delete support via `is_active` flag
* **Admin-Only Access**
  * All student operations require admin authentication
  * Full CRUD operations managed by administrators
  * Students cannot access the system directly

#### 🔌 API Endpoints

**Student Management** (`/api/v1/students`) - All endpoints require admin authentication

* `POST /` - Create student with E.164 phone validation
* `GET /` - List students with pagination and filtering
  * Filter by: `active_only`, `email`, `name` (first/last), `country`
  * Pagination: `skip`, `limit` (max 1000)
* `GET /{student_id}` - Get student by ID
* `PUT /{student_id}` - Update student (all fields optional)
* `DELETE /{student_id}` - Soft delete student (sets `is_active=False`)
* `POST /{student_id}/activate` - Reactivate deactivated student

#### 🏗️ Architecture Components

**Models** (`app/models/`)

* `student.py` - Student ORM model with `Base` + `TimestampMixin`
  * Unique email and phone number constraints
  * Indexed fields for query performance
  * `full_name` property for convenience

**Repositories** (`app/repositories/`)

* `student.py` - StudentRepository extending BaseRepository
  * `get_by_email()` - Find student by email
  * `get_by_phone()` - Find student by phone number
  * `get_active_students()` - Filter active students
  * `get_with_filters()` - Advanced filtering with pagination
  * `email_exists()` - Check email uniqueness (with exclusion for updates)
  * `phone_exists()` - Check phone uniqueness (with exclusion for updates)

**Services** (`app/services/`)

* `student.py` - StudentService business logic
  * Email normalization (lowercase, trim)
  * Phone number normalization (trim)
  * Uniqueness validation for email and phone
  * Soft delete implementation
  * Filter orchestration

**Schemas** (`app/schemas/`)

* `student.py` - Pydantic validation schemas
  * `StudentBase` - Shared properties
  * `StudentCreate` - Creation with E.164 phone validation
  * `StudentUpdate` - Optional update fields with E.164 validation
  * `Student` - Response schema with timestamps
  * E.164 regex validation: `^\+[1-9]\d{1,14}$`

**API** (`app/api/v1/endpoints/`)

* `students.py` - Student endpoints with comprehensive documentation
  * Query parameter validation
  * Admin authentication enforcement
  * Detailed error responses

**Database**

* Alembic migration: `2025_11_21_1749-f7cef4dac3fa_add_students_table.py`
* Creates `students` table with indexes on `id`, `email`, `phone_number`
* Unique constraints on `email` and `phone_number`

#### ✅ Validation

* **Email Validation**
  * EmailStr type with Pydantic validation
  * Automatic lowercase normalization
  * Uniqueness enforcement at database and service layers
* **Phone Number Validation**
  * Strict E.164 format: `+[country code][number]`
  * Regex pattern: `^\+[1-9]\d{1,14}$`
  * Examples: `+17038590314` (US), `+447911123456` (UK)
  * Uniqueness enforcement
  * Clear error messages for invalid formats
* **Country Field**
  * Optional string field (max 100 chars)
  * No format enforcement (future enhancement opportunity)

#### 🧪 Testing

* **Unit Tests** (`tests/unit/test_services/test_student.py`)
  * 15+ test cases covering StudentService
  * Tests for CRUD operations
  * Tests for email normalization (uppercase → lowercase)
  * Tests for phone number validation (valid/invalid E.164 formats)
  * Tests for uniqueness constraints (email and phone)
  * Tests for soft delete behavior
  * Tests for filtering functionality
  * Mocked dependencies for isolated testing

#### 📚 Documentation

* **README.md Updates**
  * `xoxo/README.md` - Added Student Tracking to features list
  * `backend/README.md` - Complete Student API documentation
    * API endpoint examples with curl commands
    * Request/response samples
    * Error code documentation
    * Filtering examples
    * E.164 phone format explanation
  * Project structure updated with student files
* **CHANGELOG.md** - This entry!

#### 🔍 Features

* **Advanced Filtering**
  * Filter by active status
  * Search by email (exact match, case-insensitive)
  * Search by name (substring match in first or last name)
  * Filter by country (exact match, case-insensitive)
  * Combine multiple filters
  * Pagination support (skip/limit)
* **Data Integrity**
  * Email and phone uniqueness enforced
  * Automatic timestamp management
  * Soft delete preserves data
  * Update validations prevent conflicts
* **User Experience**
  * Clear validation error messages
  * E.164 format guidance
  * Comprehensive API documentation
  * Filtering flexibility

### Changed

* `app/db/base.py` - Added Student model import for Alembic
* `app/api/v1/router.py` - Registered students router

### Technical Details

* Students use `int` autoincrement ID (consistent with Users)
* Email stored in lowercase for consistency
* Phone numbers stored as provided (after E.164 validation)
* Soft delete via `is_active` boolean (default `True`)
* All database operations are async
* Repository pattern for data access abstraction
* Service layer handles business logic and normalization


---

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


## Support

For questions or issues:

* Review complete documentation in [README.md](README.md)
* Check code comments in `app/core/security.py` and `app/services/auth.py`
* Run tests: `pytest` or `docker compose exec app pytest`
* Visit interactive API docs: http://localhost:8000/docs
* See root project documentation: [../README.md](../README.md)


