# PRMS — Project Resource Management System

Backend REST API built with **FastAPI**, **PostgreSQL**, **SQLAlchemy 2.0**, and **Alembic**.

---

## Prerequisites

| Tool | Minimum Version | Install |
|------|----------------|---------|
| Python | 3.12 | https://www.python.org/downloads/ |
| Docker | 24.x | https://docs.docker.com/get-docker/ |
| Docker Compose | v2.x | Included with Docker Desktop |
| uv *(recommended)* | 0.5.x | `pip install uv` or https://github.com/astral-sh/uv |

---

## Quick Start (Docker)

The fastest way to run the full stack locally.

```bash
# 1. Clone the repository
git clone <repo-url>
cd prms

# 2. Create the backend .env file
cp backend/.env.example backend/.env
# Open backend/.env and set a real SECRET_KEY (min 32 chars)
# All other defaults are pre-configured for Docker

# 3. Build and start all services (PostgreSQL + API)
docker compose up --build

# 4. Run database migrations (in a new terminal)
docker compose exec api alembic upgrade head

# 5. Verify the API is healthy
curl http://localhost:8000/health
# Expected: {"status":"healthy","version":"0.1.0","environment":"development","database":"connected"}

# 6. Open the interactive API docs
# http://localhost:8000/docs
```

---

## Local Development (without Docker)

Use this when you want faster iteration without container overhead.

### 1. Set up PostgreSQL

Start a local PostgreSQL instance, then create a database and user:

```sql
CREATE USER prms_user WITH PASSWORD 'prms_password';
CREATE DATABASE prms_db OWNER prms_user;
```

Or run just the database in Docker while running the API locally:

```bash
docker compose up db
```

### 2. Create a virtual environment and install dependencies

**Using uv (recommended):**
```bash
cd backend
uv venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

uv pip install -e ".[dev]"
```

**Using pip:**
```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -e ".[dev]"
```

### 3. Configure environment variables

```bash
cp .env.example .env
# Edit .env:
#   DATABASE_URL=postgresql+asyncpg://prms_user:prms_password@localhost:5432/prms_db
#   SECRET_KEY=<random-string-min-32-chars>
#   DEBUG=true
```

Generate a secure SECRET_KEY:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 4. Run database migrations

```bash
cd backend
alembic upgrade head
```

### 5. Start the development server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API is now available at `http://localhost:8000`.

---

## Environment Variables

All configuration is loaded from environment variables (or the `backend/.env` file).

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `DATABASE_URL` | `PostgresDsn` | **required** | Full async PostgreSQL DSN (`postgresql+asyncpg://...`) |
| `SECRET_KEY` | `str` | **required** | JWT signing secret — min 32 chars. Never commit this. |
| `ALGORITHM` | `str` | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `int` | `30` | JWT token TTL in minutes (min 1) |
| `ENVIRONMENT` | `str` | `development` | Runtime environment: `development`, `staging`, or `production` |
| `DEBUG` | `bool` | `false` | Enables SQL echo and traceback in 500 responses |
| `PROJECT_NAME` | `str` | `PRMS API` | Application name shown in OpenAPI docs |
| `API_V1_STR` | `str` | `/api/v1` | URL prefix for all v1 API routes |
| `ALLOWED_ORIGINS` | `list[str]` | `["http://localhost:3000","http://localhost:5173"]` | CORS allowed origins (JSON array) |
| `LOG_LEVEL` | `str` | `INFO` | Logging verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |

---

## Project Structure

```
prms/
├── backend/
│   ├── app/
│   │   ├── core/               # Config, security (JWT), logging
│   │   │   ├── config.py       # Pydantic Settings singleton
│   │   │   ├── logging.py      # Structured logging setup
│   │   │   └── security.py     # JWT create / verify helpers + OAuth2 scheme
│   │   ├── database/
│   │   │   ├── base.py         # SQLAlchemy DeclarativeBase
│   │   │   └── session.py      # Async engine + AsyncSessionLocal factory
│   │   ├── models/
│   │   │   ├── __init__.py     # Model registry (import all models here)
│   │   │   └── base.py         # UUIDMixin + TimestampMixin reusable mixins
│   │   ├── schemas/
│   │   │   └── common.py       # Shared Pydantic response models (errors, health)
│   │   ├── routers/
│   │   │   └── health.py       # GET /health endpoint
│   │   ├── services/           # Business logic layer (populated per feature)
│   │   ├── crud/               # Database access layer (populated per feature)
│   │   ├── middleware/
│   │   │   └── exception_handler.py  # Global HTTP / validation / 500 handlers
│   │   ├── dependencies/
│   │   │   ├── database.py     # get_db — per-request AsyncSession injector
│   │   │   └── auth.py         # get_current_user — JWT bearer dependency stub
│   │   ├── utils/              # Shared helpers (populated as needed)
│   │   └── main.py             # App factory + lifespan + router registration
│   ├── alembic/
│   │   ├── env.py              # Async Alembic migration environment
│   │   ├── script.py.mako      # Migration file template
│   │   └── versions/           # Auto-generated migration scripts
│   ├── alembic.ini             # Alembic configuration
│   ├── pyproject.toml          # Python project & dependency manifest
│   ├── Dockerfile              # Multi-stage production Docker image
│   ├── .env.example            # Environment variable template
│   └── .dockerignore
├── docker-compose.yml          # Local dev: PostgreSQL + API services
├── .gitignore
└── README.md
```

---

## API Documentation

Interactive Swagger UI is available at:

```
http://localhost:8000/docs
```

ReDoc alternative documentation:

```
http://localhost:8000/redoc
```

> **Note:** Both `/docs` and `/redoc` are disabled when `ENVIRONMENT=production` to prevent public schema exposure.

Use the **Authorize** button in Swagger UI to supply a Bearer JWT token for testing protected endpoints.

---

## Common Commands

```bash
# Generate a new migration after changing models
alembic revision --autogenerate -m "add users table"

# Apply all pending migrations
alembic upgrade head

# Roll back the last migration
alembic downgrade -1

# Check current migration state
alembic current

# Run linter
ruff check .

# Run type checker
mypy app/

# Run tests
pytest
```

---

## Architecture Decisions

- **Async-first**: `asyncpg` + `create_async_engine` throughout — no synchronous DB calls on the event loop.
- **Settings singleton**: Pydantic `BaseSettings` with `@lru_cache` prevents repeated `.env` file reads.
- **Layered architecture**: `routers → services → crud → models` — each layer has a single responsibility.
- **Mixins over inheritance**: `UUIDMixin` and `TimestampMixin` compose cleanly without deep class hierarchies.
- **Non-root Docker**: The container runs as UID 1000 to minimise the attack surface.
- **Production docs disabled**: Swagger/ReDoc are hidden in production to avoid leaking the API schema.
