# XOXO Education

Backend and services for XOXO Education (https://www.xoxoeducation.com), a non-profit organization.

## Project Structure

```
xoxo/
├── backend/          # FastAPI backend application
│   └── README.md     # Backend-specific documentation and setup
└── README.md         # This file
```

## Getting Started

### Backend

The backend is a FastAPI application with PostgreSQL database, built with clean layered architecture.

For detailed setup instructions, see: [backend/README.md](backend/README.md)

Quick start with Docker:

```bash
cd backend
cp .env.example .env
docker-compose up
```

API will be available at: http://localhost:8000

API Documentation: http://localhost:8000/docs

## Tech Stack

- **Backend**: FastAPI, Python 3.11+
- **Database**: PostgreSQL (async)
- **ORM**: SQLAlchemy 2.0+
- **Migrations**: Alembic
- **Testing**: pytest
- **Containerization**: Docker + Docker Compose

## Architecture

The backend follows a **layered monolithic architecture**:

- **API Layer**: FastAPI routers, request/response handling
- **Service Layer**: Business logic and orchestration
- **Repository Layer**: Data access operations
- **Data Layer**: PostgreSQL database

For detailed architecture documentation, see [backend/README.md](backend/README.md)

## Development

### Prerequisites

- Python 3.11+
- Poetry
- Docker & Docker Compose

### Setup

See [backend/README.md](backend/README.md) for detailed development setup instructions.

## License

Proprietary - XOXO Education
