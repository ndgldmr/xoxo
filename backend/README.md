# XOXO Education Backend API

A robust, scalable FastAPI backend for XOXO Education built with clean architecture principles.

## Architecture

This project follows a **layered monolithic architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────┐
│          API Layer (FastAPI)            │  ← HTTP, validation, routing
├─────────────────────────────────────────┤
│         Service Layer                   │  ← Business logic
├─────────────────────────────────────────┤
│        Repository Layer                 │  ← Data access
├─────────────────────────────────────────┤
│      Data Layer (PostgreSQL)            │  ← Persistence
└─────────────────────────────────────────┘
```

### Layers

- **API Layer** (`app/api/`): FastAPI routers, request/response models, HTTP handling
- **Service Layer** (`app/services/`): Business logic, orchestration, validation
- **Repository Layer** (`app/repositories/`): Data access, CRUD operations
- **Data Layer** (`app/models/`): SQLAlchemy ORM models

## Tech Stack

- **Framework**: FastAPI 0.109+
- **Language**: Python 3.11+
- **Database**: PostgreSQL (async via asyncpg)
- **ORM**: SQLAlchemy 2.0+ (async)
- **Migrations**: Alembic
- **Validation**: Pydantic v2
- **Authentication**: JWT tokens (access + refresh)
- **Password Hashing**: bcrypt via passlib
- **Testing**: pytest + pytest-asyncio
- **Dependency Management**: Poetry
- **Code Quality**: black, ruff, mypy
- **Containerization**: Docker + Docker Compose

## Features

### 🔐 Authentication & Authorization

#### Authentication System
- **Password Security**: Bcrypt-based password hashing with unique salts per password
- **JWT Tokens**: Access tokens (30 min) and Refresh tokens (7 day) strategy
- **Login Flow**: Email/password authentication with token issuance
- **Token Refresh**: Secure token refresh endpoint for extended sessions

#### Authorization System
- **Role-Based Access Control (RBAC)**: Admin and regular user roles
- **Admin-Only User Management**: All user CRUD operations require admin privileges
- **Protected Routes**: FastAPI dependency injection for route protection

#### Password Policy
- Minimum 12 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character (@$!%\*?&)

#### Security Features
- ✅ Password hashing with bcrypt (never store plain text)
- ✅ JWT tokens with expiration
- ✅ Password complexity requirements enforced
- ✅ Token type verification (prevents access token used as refresh)
- ✅ Admin role enforcement
- ✅ Production SECRET_KEY validation (fails if default in production)
- ✅ Inactive user account protection

### 📊 User Management
- Full CRUD operations for users (admin-only)
- Email uniqueness validation
- User activation/deactivation (soft delete)
- Pagination support
- Password strength validation on user creation

### 👨‍🎓 Student Tracking
- Full CRUD operations for students (admin-only)
- Students are NOT system users (no authentication)
- Email and phone number uniqueness enforcement
- Soft delete with activation/deactivation support
- Advanced filtering (name, email, country, active status)
- Strict E.164 phone number validation
- Automatic email normalization (lowercase)
- Pagination support

### 🏥 Health & Monitoring
- Health check endpoints (`/health`, `/health/db`)
- Database connectivity monitoring

### 🔮 Future Security Enhancements (Optional)

These features are not currently implemented but may be considered for future releases:

- **Token Blacklist/Revocation**: Enable explicit logout by blacklisting tokens
- **Rate Limiting**: Protect auth endpoints from brute force attacks
- **Multi-Factor Authentication (MFA)**: Add TOTP/SMS verification
- **OAuth2/OIDC Integration**: Support third-party authentication (Google, Microsoft, etc.)
- **Email Verification**: Require email verification for new users
- **Password Reset Flow**: Allow users to reset forgotten passwords
- **Audit Logging**: Track all admin actions for compliance
- **IP-Based Access Controls**: Restrict access by IP address or geolocation
- **Session Management**: Track active sessions and allow users to revoke them
- **Account Lockout**: Temporarily lock accounts after failed login attempts

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/      # API endpoints
│   │       │   ├── auth.py     # 🔐 Authentication endpoints
│   │       │   ├── health.py
│   │       │   ├── students.py # 👨‍🎓 Student management
│   │       │   └── users.py    # 🔒 Protected user management
│   │       └── router.py       # API router aggregation
│   ├── core/
│   │   ├── config.py          # Settings & configuration
│   │   ├── deps.py            # 🔐 Auth dependencies
│   │   ├── exceptions.py      # Custom exceptions
│   │   └── security.py        # 🔐 Password & JWT utilities
│   ├── db/
│   │   ├── base.py            # Import all models for Alembic
│   │   ├── base_class.py      # Base ORM class
│   │   └── session.py         # Async session management
│   ├── models/                # SQLAlchemy models
│   │   ├── student.py         # 👨‍🎓 Student model
│   │   └── user.py            # User with auth fields
│   ├── repositories/          # Data access layer
│   │   ├── base.py
│   │   ├── student.py         # 👨‍🎓 Student repository
│   │   └── user.py
│   ├── schemas/               # Pydantic schemas
│   │   ├── auth.py            # 🔐 Auth schemas
│   │   ├── student.py         # 👨‍🎓 Student schemas
│   │   └── user.py            # User schemas with password
│   ├── services/              # Business logic
│   │   ├── auth.py            # 🔐 Auth service
│   │   ├── student.py         # 👨‍🎓 Student service
│   │   └── user.py            # User service with password hashing
│   └── main.py                # FastAPI app entry point
├── alembic/                   # Database migrations
│   ├── versions/              # Migration files
│   │   ├── 2025_11_19_*_auth.py
│   │   └── 2025_11_21_*_add_students_table.py
│   └── env.py
├── tests/
│   ├── conftest.py           # Pytest fixtures (with auth fixtures)
│   └── unit/
│       ├── test_security.py  # 🔐 Auth unit tests (20 tests)
│       └── test_services/
│           └── test_student.py  # 👨‍🎓 Student service tests
├── scripts/                   # Utility scripts
│   └── create_admin.py       # 🔐 Admin user creation
├── .env.example              # Environment variables template
├── alembic.ini               # Alembic configuration
├── docker-compose.yml        # Docker Compose setup
├── Dockerfile                # Multi-stage Docker build
├── pyproject.toml            # Poetry dependencies
├── CHANGELOG.md              # Project changelog
├── .github/                  # GitHub templates
│   └── PULL_REQUEST_TEMPLATE.md
└── docs/                     # 📚 Documentation
    ├── README.md             # Documentation index
    ├── authentication.md     # Auth implementation guide
    ├── quick-start.md        # Quick reference
    └── development/          # Development guides
```

## Getting Started

### Prerequisites

- Python 3.11+
- Poetry
- Docker & Docker Compose (for local development)

### Option 1: Docker Compose (Recommended)

This is the easiest way to get started. It will set up PostgreSQL and the API automatically.

1. **Clone the repository and navigate to backend:**
   ```bash
   cd backend
   ```

2. **Start services:**
   ```bash
   docker compose up
   ```

   **Note:** No need to create a `.env` file! All environment variables are configured in `docker-compose.yml`.

   The API will be available at: http://localhost:8000

   API Documentation: http://localhost:8000/docs

3. **Optional: Start with pgAdmin (database UI):**
   ```bash
   docker compose --profile tools up
   ```

   pgAdmin: http://localhost:5050 (admin@xoxo.com / admin)

### Option 2: Local Development (Without Docker)

1. **Install Poetry:**
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. **Install dependencies:**
   ```bash
   poetry install
   ```

3. **Activate virtual environment:**
   ```bash
   poetry shell
   ```

4. **Set up PostgreSQL** (via Docker):
   ```bash
   docker run --name xoxo-postgres \
     -e POSTGRES_USER=xoxo \
     -e POSTGRES_PASSWORD=xoxo \
     -e POSTGRES_DB=xoxo_dev \
     -p 5432:5432 \
     -d postgres:16-alpine
   ```

5. **Copy and configure environment variables:**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` to update the database connection if needed. The defaults should work with the PostgreSQL container above.

6. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

7. **Start the development server:**
   ```bash
   uvicorn app.main:app --reload
   ```

   API: http://localhost:8000
   Docs: http://localhost:8000/docs

## 🔐 Authentication Setup

After starting the application, you need to create your first admin user:

### Create Admin User

**With Docker:**
```bash
docker compose exec app python scripts/create_admin.py
```

**Locally:**
```bash
python scripts/create_admin.py
```

The script will interactively prompt you for:
- Email
- First name, last name, phone (optional)
- Password (must meet complexity requirements: 12+ chars, uppercase, lowercase, digit, special char)

### Authentication API Endpoints

#### **POST /api/v1/auth/login**

Authenticate with email and password to receive JWT tokens.

**Request:**
```json
{
  "email": "admin@xoxoeducation.com",
  "password": "AdminPassword123!"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Errors:**
- `401`: Invalid credentials or inactive account

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@xoxoeducation.com",
    "password": "YourPassword123!"
  }'
```

---

#### **POST /api/v1/auth/refresh**

Refresh access token using refresh token.

**Request:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Errors:**
- `401`: Invalid or expired refresh token

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "YOUR_REFRESH_TOKEN"
  }'
```

---

#### **GET /api/v1/auth/me**

Get current authenticated user's profile.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200):**
```json
{
  "id": 1,
  "email": "admin@xoxoeducation.com",
  "first_name": "Admin",
  "last_name": "User",
  "phone": "+1234567890",
  "is_active": true,
  "is_admin": true,
  "created_at": "2025-11-19T16:00:00Z",
  "updated_at": "2025-11-19T16:00:00Z"
}
```

**Errors:**
- `401`: Invalid or missing token
- `403`: Inactive user account

**Example:**
```bash
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### Protected User Management Endpoints

All user management endpoints (`/api/v1/users/*`) now require admin authentication. Include the `Authorization: Bearer <access_token>` header with an admin user's token.

**Example - Create User (Admin Only):**
```bash
curl -X POST http://localhost:8000/api/v1/users/ \
  -H "Authorization: Bearer YOUR_ADMIN_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "first_name": "New",
    "last_name": "User",
    "password": "SecurePass123!",
    "phone": "+1234567890",
    "is_active": true,
    "is_admin": false
  }'
```

**Response (201):**
```json
{
  "id": 2,
  "email": "newuser@example.com",
  "first_name": "New",
  "last_name": "User",
  "phone": "+1234567890",
  "is_active": true,
  "is_admin": false,
  "created_at": "2025-11-19T16:00:00Z",
  "updated_at": "2025-11-19T16:00:00Z"
}
```

**Errors:**
- `401`: Not authenticated
- `403`: Not admin (Admin privileges required)
- `409`: Email already exists
- `422`: Password doesn't meet requirements

## Database Migrations

### Create a new migration

After modifying models in `app/models/`:

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Description of changes"

# Review the generated migration in alembic/versions/
# Then apply it:
alembic upgrade head
```

### Common migration commands

```bash
# Apply all migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current migration
alembic current

# Show migration history
alembic history
```

## Testing

### Run All Tests

```bash
# Locally (if dependencies installed)
pytest

# In Docker (recommended)
docker compose exec app pytest
```

### Test Coverage

**Current Test Suite:**
- **20 unit tests** covering core authentication functionality
- **Unit Tests** (`tests/unit/test_security.py`): 20 tests covering password hashing, validation, and JWT operations
- **Functional tests**: To be added in future releases

**Run with Coverage Report:**
```bash
# Generate HTML coverage report
pytest --cov=app --cov-report=html

# View coverage in terminal
pytest --cov=app --cov-report=term-missing

# In Docker
docker compose exec app pytest --cov=app --cov-report=term-missing
```

### Run Specific Test Suites

```bash
# All tests (unit tests only)
pytest -v

# Authentication unit tests (password hashing, JWT)
pytest tests/unit/test_security.py -v

# In Docker
docker compose exec app pytest -v
docker compose exec app pytest tests/unit/test_security.py -v
```

### Test Scenarios Covered

**Authentication Unit Tests (20 tests):**
- ✅ Password hashing (bcrypt with unique salts)
- ✅ Password verification (valid/invalid)
- ✅ Password strength validation (all complexity rules)
- ✅ JWT access token creation and decoding
- ✅ JWT refresh token creation and decoding
- ✅ Token expiration handling
- ✅ Token type verification (access vs refresh)
- ✅ Custom expiration times

**Future Testing:**
- Functional/integration tests for API endpoints
- End-to-end authentication flows
- Protected route access control testing

## Code Quality

### Format code with black

```bash
black .
```

### Lint with ruff

```bash
ruff check .
```

### Type check with mypy

```bash
mypy app/
```

### Run all quality checks

```bash
black . && ruff check . && mypy app/ && pytest
```

### Install pre-commit hooks (Optional)

```bash
pre-commit install
```

Now code quality checks will run automatically on git commit.

## API Documentation

Once the server is running, visit the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
  - Try the authentication flow: Login → Copy access token → Click "Authorize" → Test protected endpoints
  - Includes all endpoints: Authentication, User Management, Health
- **ReDoc**: http://localhost:8000/redoc (Alternative documentation viewer)
- **OpenAPI JSON**: http://localhost:8000/api/v1/openapi.json (Raw OpenAPI specification)

## Example API Usage

### Health Check (No Auth Required)

```bash
curl http://localhost:8000/api/v1/health
```

### Authentication Flow

#### 1. Login to Get Tokens

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@xoxoeducation.com",
    "password": "YourPassword123!"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbG...",
  "refresh_token": "eyJhbG...",
  "token_type": "bearer"
}
```

#### 2. Get Current User Profile

```bash
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### 3. Refresh Tokens (When Access Token Expires)

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "YOUR_REFRESH_TOKEN"
  }'
```

### User Management (Admin Only)

**Note:** All user management endpoints require admin authentication. Include `Authorization: Bearer <admin_access_token>` header.

#### Create a User

```bash
curl -X POST http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer YOUR_ADMIN_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "password": "SecurePass123!",
    "phone": "+1234567890",
    "is_active": true,
    "is_admin": false
  }'
```

#### Get All Users

```bash
curl http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer YOUR_ADMIN_ACCESS_TOKEN"
```

#### Get User by ID

```bash
curl http://localhost:8000/api/v1/users/1 \
  -H "Authorization: Bearer YOUR_ADMIN_ACCESS_TOKEN"
```

#### Update User

```bash
curl -X PUT http://localhost:8000/api/v1/users/1 \
  -H "Authorization: Bearer YOUR_ADMIN_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Jane"
  }'
```

#### Deactivate User (Soft Delete)

```bash
curl -X POST http://localhost:8000/api/v1/users/1/deactivate \
  -H "Authorization: Bearer YOUR_ADMIN_ACCESS_TOKEN"
```

#### Delete User (Hard Delete)

```bash
curl -X DELETE http://localhost:8000/api/v1/users/1 \
  -H "Authorization: Bearer YOUR_ADMIN_ACCESS_TOKEN"
```

### Student Management (Admin Only)

**Note:** All student management endpoints require admin authentication. Students are NOT system users and have no login credentials.

#### Create a Student

```bash
curl -X POST http://localhost:8000/api/v1/students \
  -H "Authorization: Bearer YOUR_ADMIN_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "student@example.com",
    "first_name": "Jane",
    "last_name": "Smith",
    "phone_number": "+17038590314",
    "country": "USA",
    "is_active": true
  }'
```

**Response (201):**
```json
{
  "id": 1,
  "email": "student@example.com",
  "first_name": "Jane",
  "last_name": "Smith",
  "phone_number": "+17038590314",
  "country": "USA",
  "is_active": true,
  "created_at": "2025-11-21T17:00:00Z",
  "updated_at": "2025-11-21T17:00:00Z"
}
```

**Errors:**
- `401`: Not authenticated
- `403`: Not admin
- `409`: Email or phone number already exists
- `422`: Validation error (invalid email or phone format)

**Phone Number Format:** Must be E.164 format: `+[country code][number]` (e.g., `+17038590314`)

#### Get All Students (with Filters)

```bash
# Get all students with pagination
curl http://localhost:8000/api/v1/students?skip=0&limit=100 \
  -H "Authorization: Bearer YOUR_ADMIN_ACCESS_TOKEN"

# Get only active students
curl http://localhost:8000/api/v1/students?active_only=true \
  -H "Authorization: Bearer YOUR_ADMIN_ACCESS_TOKEN"

# Filter by name (searches first and last name)
curl http://localhost:8000/api/v1/students?name=Jane \
  -H "Authorization: Bearer YOUR_ADMIN_ACCESS_TOKEN"

# Filter by email
curl http://localhost:8000/api/v1/students?email=student@example.com \
  -H "Authorization: Bearer YOUR_ADMIN_ACCESS_TOKEN"

# Filter by country
curl http://localhost:8000/api/v1/students?country=USA \
  -H "Authorization: Bearer YOUR_ADMIN_ACCESS_TOKEN"

# Combine multiple filters
curl "http://localhost:8000/api/v1/students?active_only=true&country=USA&limit=50" \
  -H "Authorization: Bearer YOUR_ADMIN_ACCESS_TOKEN"
```

#### Get Student by ID

```bash
curl http://localhost:8000/api/v1/students/1 \
  -H "Authorization: Bearer YOUR_ADMIN_ACCESS_TOKEN"
```

#### Update Student

```bash
curl -X PUT http://localhost:8000/api/v1/students/1 \
  -H "Authorization: Bearer YOUR_ADMIN_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Janet",
    "country": "Canada"
  }'
```

**Note:** All fields are optional. Only provided fields will be updated.

#### Deactivate Student (Soft Delete)

```bash
curl -X DELETE http://localhost:8000/api/v1/students/1 \
  -H "Authorization: Bearer YOUR_ADMIN_ACCESS_TOKEN"
```

**Note:** This performs a soft delete by setting `is_active=False`. The student record remains in the database.

#### Activate Student

```bash
curl -X POST http://localhost:8000/api/v1/students/1/activate \
  -H "Authorization: Bearer YOUR_ADMIN_ACCESS_TOKEN"
```

**Note:** Reactivates a previously deactivated student.

## Adding New Features

To add a new domain (e.g., "Volunteers"):

1. **Create ORM model** (`app/models/volunteer.py`)
2. **Create Pydantic schemas** (`app/schemas/volunteer.py`)
3. **Create repository** (`app/repositories/volunteer.py`)
4. **Create service** (`app/services/volunteer.py`)
5. **Create API endpoints** (`app/api/v1/endpoints/volunteers.py`)
6. **Register router** in `app/api/v1/router.py`
7. **Import model** in `app/db/base.py` for Alembic
8. **Generate migration**: `alembic revision --autogenerate -m "Add volunteers table"`
9. **Apply migration**: `alembic upgrade head`

## Environment Variables

### Configuration Methods

- **Docker Compose** (recommended for local dev): Environment variables are defined in `docker-compose.yml`. No `.env` file needed.
- **Local development** (without Docker): Copy `.env.example` to `.env` and customize as needed.
- **Production**: Use platform-native environment variables or secrets management (never commit `.env` to git).

See `.env.example` for all available environment variables.

### Key Variables

**Database & Application:**
- `DATABASE_URL`: PostgreSQL connection string
- `ENVIRONMENT`: development, staging, or production
- `DEBUG`: Enable debug mode (true/false)
- `ALLOWED_ORIGINS`: CORS origins (comma-separated)

**Authentication & Security (Required for Production):**
- `SECRET_KEY`: Secret key for JWT tokens (MUST be changed in production!)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Access token expiration in minutes (default: 30)
- `REFRESH_TOKEN_EXPIRE_MINUTES`: Refresh token expiration in minutes (default: 10080 = 7 days)
- `ALGORITHM`: JWT signing algorithm (default: HS256)

### Generate Secure SECRET_KEY

**CRITICAL for Production:** Never use the default SECRET_KEY in production. Generate a secure random key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Example output: `qJ7xK3mP9nR2sT5vW8yZ0aB1cD4eF6gH9jK2lM5nP8qR`

Set this as your `SECRET_KEY` environment variable in production. The application will fail to start if using the default key with `ENVIRONMENT=production`.

## Deployment

### Pre-Deployment Checklist

Before deploying to production, ensure:

1. ✅ **Generate Secure SECRET_KEY** - Never use default
2. ✅ **Run Database Migrations** - Apply all migrations including auth
3. ✅ **Create First Admin User** - Use `scripts/create_admin.py`
4. ✅ **Test Authentication Flow** - Verify login, token refresh, protected endpoints
5. ✅ **Run Test Suite** - All 20 unit tests should pass
6. ✅ **Configure Environment Variables** - Set production values
7. ✅ **Use Managed PostgreSQL** - AWS RDS, GCP Cloud SQL, etc.

### Building for Production

```bash
docker build -t xoxo-backend:latest .
```

### Running in Production

1. **Set Environment Variables** (via your platform, not `.env` file):
   ```bash
   ENVIRONMENT=production
   DEBUG=False
   SECRET_KEY=<your-secure-random-key>
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   REFRESH_TOKEN_EXPIRE_MINUTES=10080
   DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
   ALLOWED_ORIGINS=https://yourdomain.com
   ```

2. **Generate Secure SECRET_KEY**:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

3. **Use Managed PostgreSQL** (AWS RDS, GCP Cloud SQL, etc.)

4. **Run Database Migrations**:
   ```bash
   alembic upgrade head
   ```

5. **Create First Admin User**:
   ```bash
   python scripts/create_admin.py
   ```

6. **Verify Production SECRET_KEY** - Application will fail to start if using default key with `ENVIRONMENT=production`

### Cloud Deployment

This application is cloud-agnostic and can be deployed to:

- **AWS**: ECS, Fargate, or EKS
- **GCP**: Cloud Run, GKE, or Compute Engine
- **Azure**: Container Instances or AKS
- **Any platform supporting Docker**

Example for GCP Cloud Run:

```bash
# Build and push to GCP
gcloud builds submit --tag gcr.io/PROJECT_ID/xoxo-backend

# Deploy to Cloud Run
gcloud run deploy xoxo-backend \
  --image gcr.io/PROJECT_ID/xoxo-backend \
  --platform managed \
  --region us-central1 \
  --set-env-vars DATABASE_URL=... \
  --allow-unauthenticated
```

## Troubleshooting

### Authentication Issues

#### "SECRET_KEY must be changed in production"
**Cause:** Using the default SECRET_KEY with `ENVIRONMENT=production`
**Solution:** Generate and set a secure SECRET_KEY:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```
Set the output as your `SECRET_KEY` environment variable.

#### "Incorrect email or password"
**Cause:** Invalid credentials
**Solution:** Verify email and password are correct. Check that user exists in database and password was hashed correctly during creation.

#### "User account is inactive"
**Cause:** User has `is_active=false` in database
**Solution:** Reactivate user by setting `is_active=true` in database or via API if you have admin access.

#### "Could not validate credentials" or "Invalid token"
**Cause:** Token expired, malformed, or invalid
**Solution:** Login again to get new tokens. Access tokens expire after 30 minutes by default.

#### "Admin privileges required"
**Cause:** Endpoint requires admin role but user is not admin
**Solution:** Ensure user has `is_admin=true` in database. Create admin user with `scripts/create_admin.py`.

#### "Invalid or expired refresh token"
**Cause:** Refresh token expired (7 days default) or is invalid
**Solution:** Login again to get new tokens. Cannot refresh an expired refresh token.

#### "Password does not meet security requirements"
**Cause:** Password doesn't meet complexity requirements
**Solution:** Ensure password has:
- At least 12 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character (@$!%\*?&)

#### Bcrypt version warning (non-critical)
**Warning:** `(trapped) error reading bcrypt version`
**Impact:** None - admin user created successfully
**Cause:** bcrypt 4.x removed `__about__.__version__` that passlib tries to read
**Solution:** Ignore - this is cosmetic only and doesn't affect functionality

### Database Connection Errors

- Ensure PostgreSQL is running: `docker ps`
- Check `DATABASE_URL` in `.env` (local dev) or `docker-compose.yml` (Docker)
- Verify database exists: `docker exec -it xoxo-db psql -U xoxo -l`

### Import Errors

- Ensure you're in the Poetry shell: `poetry shell`
- Install dependencies: `poetry install`
- If testing locally without Docker, install `httpx`: `poetry add --group dev httpx`

### Migration Errors

- Check that all models are imported in `app/db/base.py`
- Verify database connection
- Review migration file in `alembic/versions/`

### Test Errors

#### "ModuleNotFoundError: No module named 'httpx'"
**Cause:** Running tests locally without installing dependencies
**Solution (Recommended):** Run tests in Docker:
```bash
docker compose exec app pytest
```
**Solution (Alternative):** Install dependencies locally:
```bash
poetry install
poetry shell
pytest
```

## Contributing

1. Create a feature branch from `main`
2. Make your changes
3. Run tests and code quality checks
4. Submit a pull request

## License

Proprietary - XOXO Education

## Support

For questions or issues:

- **Documentation**: All information is in this README.md and [CHANGELOG.md](CHANGELOG.md)
- **Interactive API Docs**: http://localhost:8000/docs (when running)
- **Code Comments**: Review `app/core/security.py` and `app/services/auth.py` for implementation details
- **Issues**: Create a GitHub issue with detailed information
- **Root README**: See [../README.md](../README.md) for project overview

## Version History

See [CHANGELOG.md](CHANGELOG.md) for detailed version history, migration guides, and breaking changes.
