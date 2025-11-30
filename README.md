# XOXO Education

Backend and services for XOXO Education (https://www.xoxoeducation.com), a non-profit organization.

## Project Structure

```
xoxo/
├── backend/          # FastAPI backend application
│   ├── README.md     # Complete backend documentation
│   └── CHANGELOG.md  # Version history and migration guides
└── README.md         # This file
```

## Quick Start

```bash
cd backend
docker compose up
```

**API**: http://localhost:8000
**Interactive Docs**: http://localhost:8000/docs

## Features

### 🔐 Authentication & Authorization
- JWT-based authentication (access + refresh tokens)
- Bcrypt password hashing with complexity requirements
- Role-based access control (Admin/User)
- Admin-only user management

### 📊 User Management
- Full CRUD operations (admin-only)
- Email uniqueness validation
- User activation/deactivation

### 👨‍🎓 Student Tracking
- Student CRUD operations (admin-only)
- Students are NOT system users (no login)
- Email and phone number uniqueness
- Soft delete with activation/deactivation
- Advanced filtering (by name, email, country, active status)
- E.164 phone number validation
- Messaging preferences:
  - English proficiency level tracking
  - Native language configuration
  - Daily message opt-in with timezone preferences
  - Preparation for AI-generated WhatsApp messaging

### 🏥 Health Monitoring
- Health check endpoints
- Database connectivity monitoring

## Tech Stack

- **Backend**: FastAPI, Python 3.11+
- **Database**: PostgreSQL (async via asyncpg)
- **ORM**: SQLAlchemy 2.0+ (async)
- **Authentication**: JWT tokens (python-jose), bcrypt (passlib)
- **Migrations**: Alembic
- **Testing**: pytest + pytest-asyncio
- **Containerization**: Docker + Docker Compose

## Architecture

The backend follows a **layered monolithic architecture** with clear separation of concerns:

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

**Key Principles:**
- Dependency injection for testability
- Async-first for scalability
- Type hints throughout for safety
- Comprehensive test coverage

## Getting Started

See [backend/README.md](backend/README.md) for complete setup instructions, including:
- Installation (Docker and local)
- Database migrations
- Creating admin users
- Authentication setup
- Testing
- Deployment

## Documentation

- **[backend/README.md](backend/README.md)** - Complete backend documentation
- **[backend/CHANGELOG.md](backend/CHANGELOG.md)** - Version history and migration guides
- **Interactive API Docs** - http://localhost:8000/docs (when running)

## Development

### Prerequisites
- Python 3.11+
- Poetry (dependency management)
- Docker & Docker Compose

### Local Setup
```bash
cd backend
poetry install
poetry shell
alembic upgrade head
python scripts/create_admin.py
uvicorn app.main:app --reload
```

### Docker Setup (Recommended)
```bash
cd backend
docker compose up
docker compose exec app python scripts/create_admin.py
```

## Testing

```bash
# In Docker
docker compose exec app pytest

# Locally
cd backend
poetry shell
pytest
```

## License

Proprietary - XOXO Education
