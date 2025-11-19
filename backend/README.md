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
- **Testing**: pytest + pytest-asyncio
- **Dependency Management**: Poetry
- **Code Quality**: black, ruff, mypy
- **Containerization**: Docker + Docker Compose

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/      # API endpoints
│   │       │   ├── health.py
│   │       │   └── users.py
│   │       └── router.py       # API router aggregation
│   ├── core/
│   │   ├── config.py          # Settings & configuration
│   │   ├── deps.py            # FastAPI dependencies
│   │   └── exceptions.py      # Custom exceptions
│   ├── db/
│   │   ├── base.py            # Import all models for Alembic
│   │   ├── base_class.py      # Base ORM class
│   │   └── session.py         # Async session management
│   ├── models/                # SQLAlchemy models
│   │   └── user.py
│   ├── repositories/          # Data access layer
│   │   ├── base.py
│   │   └── user.py
│   ├── schemas/               # Pydantic schemas
│   │   └── user.py
│   ├── services/              # Business logic
│   │   └── user.py
│   └── main.py                # FastAPI app entry point
├── alembic/                   # Database migrations
│   ├── versions/
│   └── env.py
├── tests/
│   ├── conftest.py           # Pytest fixtures
│   ├── unit/
│   └── integration/
├── scripts/                   # Utility scripts
├── .env.example              # Environment variables template
├── alembic.ini               # Alembic configuration
├── docker-compose.yml        # Docker Compose setup
├── Dockerfile                # Multi-stage Docker build
└── pyproject.toml            # Poetry dependencies
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

2. **Copy environment variables:**
   ```bash
   cp .env.example .env
   ```

3. **Start services:**
   ```bash
   docker-compose up
   ```

   The API will be available at: http://localhost:8000

   API Documentation: http://localhost:8000/docs

4. **Optional: Start with pgAdmin (database UI):**
   ```bash
   docker-compose --profile tools up
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
   # Edit .env with your settings
   ```

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

### Run all tests

```bash
pytest
```

### Run with coverage

```bash
pytest --cov=app --cov-report=html
```

### Run specific test file

```bash
pytest tests/integration/test_api/test_health.py
```

### Run tests in Docker

```bash
docker-compose exec app pytest
```

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

Once the server is running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/api/v1/openapi.json

## Example API Usage

### Health Check

```bash
curl http://localhost:8000/api/v1/health
```

### Create a User

```bash
curl -X POST http://localhost:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+1234567890",
    "is_active": true
  }'
```

### Get All Users

```bash
curl http://localhost:8000/api/v1/users
```

### Get User by ID

```bash
curl http://localhost:8000/api/v1/users/1
```

### Update User

```bash
curl -X PUT http://localhost:8000/api/v1/users/1 \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Jane"
  }'
```

### Delete User

```bash
curl -X DELETE http://localhost:8000/api/v1/users/1
```

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

See `.env.example` for all available environment variables.

Key variables:

- `DATABASE_URL`: PostgreSQL connection string
- `ENVIRONMENT`: development, staging, or production
- `DEBUG`: Enable debug mode
- `ALLOWED_ORIGINS`: CORS origins (comma-separated)
- `SECRET_KEY`: Secret key for JWT (change in production!)

## Deployment

### Building for Production

```bash
docker build -t xoxo-backend:latest .
```

### Running in Production

1. Update `.env` with production values
2. Set `ENVIRONMENT=production` and `DEBUG=False`
3. Generate a secure `SECRET_KEY`
4. Use managed PostgreSQL (AWS RDS, GCP Cloud SQL, etc.)

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

### Database connection errors

- Ensure PostgreSQL is running: `docker ps`
- Check `DATABASE_URL` in `.env`
- Verify database exists: `docker exec -it xoxo-db psql -U xoxo -l`

### Import errors

- Ensure you're in the Poetry shell: `poetry shell`
- Install dependencies: `poetry install`

### Migration errors

- Check that all models are imported in `app/db/base.py`
- Verify database connection
- Review migration file in `alembic/versions/`

## Contributing

1. Create a feature branch from `main`
2. Make your changes
3. Run tests and code quality checks
4. Submit a pull request

## License

Proprietary - XOXO Education

## Support

For questions or issues, contact the development team or create an issue in the repository.
