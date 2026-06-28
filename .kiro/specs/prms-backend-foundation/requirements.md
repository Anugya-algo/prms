# Requirements Document

## Introduction

The PRMS Backend Foundation establishes the technical scaffolding for an enterprise-grade Project Resource Management System. This spec covers the complete backend infrastructure layer using FastAPI (Python 3.12), PostgreSQL, SQLAlchemy 2.0, and Alembic — with no business logic. The foundation includes project structure, database connectivity, authentication framework, logging, error handling, CORS, health monitoring, API documentation, and container support. All subsequent business features will be built on top of this foundation.

## Glossary

- **PRMS**: Project Resource Management System — the target application being built.
- **API**: Application Programming Interface — the HTTP interface exposed by the FastAPI backend.
- **Application**: The FastAPI backend service defined in `backend/app/main.py`.
- **Router**: A FastAPI `APIRouter` instance that groups related endpoints.
- **Database**: The PostgreSQL relational database used for persistent storage.
- **ORM**: Object-Relational Mapper — SQLAlchemy 2.0 used to map Python classes to database tables.
- **Session**: A SQLAlchemy `AsyncSession` instance representing a single database transaction scope.
- **Base_Model**: The declarative SQLAlchemy base class from which all ORM models inherit.
- **Migration**: An Alembic script that applies or reverts a schema change to the Database.
- **JWT**: JSON Web Token — the signed token format used for stateless authentication.
- **JWT_Framework**: The authentication infrastructure (secret loading, token creation, token verification) without any user-facing business logic.
- **Settings**: The Pydantic `BaseSettings` class that loads and validates all configuration from environment variables and `.env` files.
- **CORS**: Cross-Origin Resource Sharing — the HTTP mechanism that controls which origins may call the API.
- **Logger**: The Python `logging` module instance configured for structured, level-based output.
- **Exception_Handler**: A FastAPI exception handler registered globally to convert unhandled exceptions into structured JSON error responses.
- **Health_Check**: The `/health` endpoint that reports the operational status of the Application and its dependencies.
- **Swagger_UI**: The interactive OpenAPI documentation interface served by FastAPI at `/docs`.
- **Dockerfile**: The container image build definition for the Application.
- **Compose_File**: The `docker-compose.yml` file that defines and runs the PostgreSQL service alongside the Application.
- **README**: The `README.md` file at the repository root that documents setup, configuration, and execution instructions.
- **Dependency_Injector**: A FastAPI `Depends`-based provider that supplies a Session to route handlers.

---

## Requirements

### Requirement 1: Project Structure

**User Story:** As a backend developer, I want a clean, layered directory structure, so that I can locate and extend any part of the system predictably.

#### Acceptance Criteria

1. THE Application SHALL be organised under `backend/app/` with the sub-packages: `core/`, `database/`, `models/`, `schemas/`, `routers/`, `services/`, `crud/`, `middleware/`, `utils/`, `dependencies/`, and an `__init__.py` in each package.
2. THE Application SHALL expose `backend/app/main.py` as the single entry point that assembles the FastAPI instance and registers all routers and middleware.
3. THE Application SHALL include a `backend/pyproject.toml` (or `requirements.txt`) that pins all direct and transitive dependencies to exact versions.

---

### Requirement 2: Environment Variable Configuration

**User Story:** As a DevOps engineer, I want all runtime configuration loaded from environment variables with a `.env` fallback, so that the Application runs identically in development and production without code changes.

#### Acceptance Criteria

1. THE Settings SHALL load every configuration value from environment variables using Pydantic `BaseSettings`.
2. THE Settings SHALL read a `.env` file as a fallback when an environment variable is absent, using `model_config = SettingsConfigDict(env_file=".env")`.
3. THE Settings SHALL define and validate the following fields with the specified types and constraints:
   - `DATABASE_URL`: `PostgresDsn` — required, no default.
   - `SECRET_KEY`: `str` — required, minimum length 32 characters.
   - `ALGORITHM`: `str` — default `"HS256"`.
   - `ACCESS_TOKEN_EXPIRE_MINUTES`: `int` — default `30`, minimum value `1`.
   - `ENVIRONMENT`: `Literal["development", "staging", "production"]` — default `"development"`.
   - `DEBUG`: `bool` — default `False`.
   - `ALLOWED_ORIGINS`: `list[str]` — default `["http://localhost:3000", "http://localhost:5173"]`.
   - `LOG_LEVEL`: `Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]` — default `"INFO"`.
   - `PROJECT_NAME`: `str` — default `"PRMS API"`.
   - `API_V1_STR`: `str` — default `"/api/v1"`.
4. IF a required field (`DATABASE_URL`, `SECRET_KEY`) is absent from both environment variables and the `.env` file, THEN THE Settings SHALL raise a `ValidationError` at application startup before any request is served.
5. THE Application SHALL instantiate Settings once and expose the singleton via `backend/app/core/config.py`.

---

### Requirement 3: Database Connection

**User Story:** As a backend developer, I want an async SQLAlchemy 2.0 connection pool to PostgreSQL, so that the Application handles concurrent requests efficiently without blocking threads.

#### Acceptance Criteria

1. THE Application SHALL create an async SQLAlchemy engine using `create_async_engine` with the `DATABASE_URL` from Settings.
2. THE Application SHALL configure the engine with a connection pool of minimum `5` and maximum `20` connections, and a `pool_recycle` of `3600` seconds.
3. THE Application SHALL create an `AsyncSessionLocal` factory using `async_sessionmaker` bound to the async engine.
4. THE Dependency_Injector SHALL yield one `AsyncSession` per request and commit on success or roll back on exception before closing the session.
5. IF the Database is unreachable at startup, THEN THE Application SHALL log an error at `ERROR` level and raise a `RuntimeError` to prevent startup from completing.
6. THE Base_Model SHALL be a SQLAlchemy `DeclarativeBase` subclass defined in `backend/app/database/base.py` that all ORM models inherit from.

---

### Requirement 4: Alembic Migration Configuration

**User Story:** As a backend developer, I want Alembic configured for async migrations, so that I can evolve the database schema safely across environments.

#### Acceptance Criteria

1. THE Application SHALL include an `alembic.ini` file at `backend/alembic.ini` with `script_location = alembic` and `sqlalchemy.url` left as a placeholder to be overridden at runtime.
2. THE Application SHALL include an `env.py` at `backend/alembic/env.py` that reads `DATABASE_URL` from Settings and passes it to the Alembic migration context using `run_async_migrations`.
3. THE Application SHALL import `Base_Model.metadata` in `backend/alembic/env.py` and pass it as `target_metadata` so Alembic can auto-generate migration scripts.
4. WHEN the command `alembic revision --autogenerate -m "<message>"` is executed, THE Migration script SHALL be created in `backend/alembic/versions/` reflecting the current model diff.
5. WHEN the command `alembic upgrade head` is executed, THE Migration SHALL apply all pending scripts to the Database without data loss for additive changes.

---

### Requirement 5: Base SQLAlchemy Model

**User Story:** As a backend developer, I want a reusable base ORM model with common audit columns, so that every database table has consistent metadata without repetitive code.

#### Acceptance Criteria

1. THE Base_Model SHALL define a mixin class `TimestampMixin` in `backend/app/models/base.py` that adds `created_at` and `updated_at` columns of type `DateTime(timezone=True)`.
2. THE `created_at` column SHALL default to the database server's current timestamp via `server_default=func.now()`.
3. THE `updated_at` column SHALL update automatically to the current timestamp on every row update via `onupdate=func.now()`.
4. THE Base_Model SHALL define an `id` column of type `UUID` with `default=uuid4` and `primary_key=True` in a mixin class `UUIDMixin`.
5. WHEN a new ORM model class inherits from both `UUIDMixin` and `TimestampMixin`, THE model SHALL automatically include `id`, `created_at`, and `updated_at` without additional column declarations.

---

### Requirement 6: JWT Authentication Framework

**User Story:** As a security engineer, I want the JWT infrastructure wired up without business logic, so that future authentication endpoints can be added without altering the core token mechanism.

#### Acceptance Criteria

1. THE JWT_Framework SHALL be defined in `backend/app/core/security.py` and expose the functions `create_access_token` and `verify_token`.
2. THE `create_access_token` function SHALL accept a `data: dict` and an optional `expires_delta: timedelta` parameter, sign the token with `SECRET_KEY` using `ALGORITHM` from Settings, and return a `str`.
3. WHEN `expires_delta` is omitted, THE `create_access_token` function SHALL use `ACCESS_TOKEN_EXPIRE_MINUTES` from Settings as the expiry duration.
4. THE `verify_token` function SHALL accept a `token: str`, verify its signature and expiry against Settings, and return the decoded payload `dict`.
5. IF the token signature is invalid or the token is expired, THEN THE `verify_token` function SHALL raise an `HTTPException` with status code `401` and a detail of `"Could not validate credentials"`.
6. THE JWT_Framework SHALL define an `oauth2_scheme` using `OAuth2PasswordBearer(tokenUrl=f"{API_V1_STR}/auth/token")` for use in route dependencies.
7. THE JWT_Framework SHALL define a `get_current_user` dependency stub in `backend/app/dependencies/auth.py` that extracts and verifies the bearer token but returns a placeholder dict until the User model is implemented.

---

### Requirement 7: Logging Configuration

**User Story:** As an operations engineer, I want structured, configurable logging, so that I can diagnose production issues without modifying code.

#### Acceptance Criteria

1. THE Logger SHALL be configured in `backend/app/core/logging.py` using Python's standard `logging` module with a format that includes timestamp, level, logger name, and message.
2. THE Logger SHALL read its log level from `LOG_LEVEL` in Settings.
3. THE Application SHALL configure logging once at startup inside the `lifespan` context manager in `main.py` before the first request is processed.
4. WHEN `ENVIRONMENT` is `"production"`, THE Logger SHALL emit log records in JSON format to support log aggregation pipelines.
5. THE Application SHALL suppress `uvicorn.access` log records at `WARNING` level or below when `ENVIRONMENT` is `"production"` to reduce noise.
6. WHEN a request results in a `5xx` response, THE Logger SHALL emit a log record at `ERROR` level that includes the request method, path, and exception message.

---

### Requirement 8: Global Exception Handling

**User Story:** As an API consumer, I want all errors to return a consistent JSON structure, so that client applications can handle errors uniformly without parsing varied response shapes.

#### Acceptance Criteria

1. THE Exception_Handler SHALL be registered in `backend/app/middleware/exception_handler.py` and added to the Application via `app.add_exception_handler`.
2. THE Exception_Handler SHALL catch `HTTPException` and return a JSON response with the shape `{"detail": "<message>", "status_code": <code>}` and the corresponding HTTP status code.
3. THE Exception_Handler SHALL catch `RequestValidationError` and return a JSON response with status code `422` and the shape `{"detail": <pydantic_errors_list>, "status_code": 422}`.
4. THE Exception_Handler SHALL catch all unhandled `Exception` instances and return a JSON response with status code `500` and the shape `{"detail": "Internal server error", "status_code": 500}`.
5. WHEN `DEBUG` is `True` in Settings, THE Exception_Handler SHALL include the exception traceback as a `"traceback"` field in `500` responses to aid local debugging.
6. WHEN `DEBUG` is `False`, THE Exception_Handler SHALL omit the traceback from `500` responses to avoid leaking implementation details.

---

### Requirement 9: CORS Configuration

**User Story:** As a frontend developer, I want the API to accept requests from the configured frontend origins, so that the browser does not block cross-origin API calls.

#### Acceptance Criteria

1. THE Application SHALL add `CORSMiddleware` from `fastapi.middleware.cors` with `allow_origins` set to `ALLOWED_ORIGINS` from Settings.
2. THE Application SHALL configure `CORSMiddleware` with `allow_credentials=True`, `allow_methods=["*"]`, and `allow_headers=["*"]`.
3. WHEN a preflight `OPTIONS` request is received from an origin in `ALLOWED_ORIGINS`, THE Application SHALL respond with status code `200` and the appropriate CORS headers.
4. WHEN a request is received from an origin not in `ALLOWED_ORIGINS`, THE Application SHALL respond without CORS headers, causing the browser to block the response.

---

### Requirement 10: Health Check Endpoint

**User Story:** As a DevOps engineer, I want a health check endpoint that verifies both application and database connectivity, so that container orchestrators and load balancers can route traffic only to healthy instances.

#### Acceptance Criteria

1. THE Health_Check SHALL be available at `GET /health` and return a JSON response with status code `200`.
2. THE Health_Check response SHALL include at minimum: `{"status": "healthy", "version": "<app_version>", "environment": "<ENVIRONMENT>", "database": "connected"}`.
3. WHEN the Database is reachable, THE Health_Check SHALL include `"database": "connected"` in the response.
4. IF the Database is unreachable, THEN THE Health_Check SHALL include `"database": "disconnected"` and return status code `503`.
5. THE Health_Check SHALL execute a lightweight query (`SELECT 1`) to verify the database connection rather than relying on pool state alone.
6. THE Health_Check endpoint SHALL NOT require authentication.

---

### Requirement 11: Swagger / OpenAPI Documentation

**User Story:** As a backend developer, I want interactive API documentation auto-generated from route definitions, so that I can explore and test endpoints without an external tool.

#### Acceptance Criteria

1. THE Application SHALL serve Swagger UI at `/docs` and ReDoc at `/redoc` when `ENVIRONMENT` is not `"production"`.
2. WHEN `ENVIRONMENT` is `"production"`, THE Application SHALL disable `/docs` and `/redoc` by setting `docs_url=None` and `redoc_url=None` to prevent exposing the schema publicly.
3. THE Application SHALL configure the OpenAPI schema with `title` from `PROJECT_NAME`, `version` from the application version string, and a `description` summarising the PRMS API.
4. THE Application SHALL define a bearer token security scheme in the OpenAPI schema so that Swagger UI displays an "Authorize" button for JWT-protected endpoints.

---

### Requirement 12: Docker Support

**User Story:** As a DevOps engineer, I want a production-ready Dockerfile and a docker-compose file for local development, so that the Application runs consistently across machines without manual environment setup.

#### Acceptance Criteria

1. THE Dockerfile SHALL use a multi-stage build: a `builder` stage that installs dependencies into a virtual environment, and a `runtime` stage based on `python:3.12-slim` that copies only the virtual environment and application code.
2. THE Dockerfile SHALL run the Application as a non-root user with UID `1000` to reduce the attack surface.
3. THE Dockerfile SHALL expose port `8000` and set `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]` as the default command.
4. THE Compose_File SHALL define a `db` service using the official `postgres:16-alpine` image with a named volume for data persistence.
5. THE Compose_File SHALL define an `api` service that builds from the Dockerfile, depends on `db`, mounts the `backend/` directory for hot-reload in development, and passes required environment variables via an `env_file` directive.
6. THE Compose_File SHALL define a `healthcheck` on the `db` service using `pg_isready` so that the `api` service starts only after PostgreSQL is accepting connections.

---

### Requirement 13: README Documentation

**User Story:** As a new team member, I want a comprehensive README, so that I can set up and run the backend from scratch without asking for help.

#### Acceptance Criteria

1. THE README SHALL include a "Prerequisites" section listing required tools with minimum versions: Python 3.12, Docker, Docker Compose, and `uv` or `pip`.
2. THE README SHALL include a "Quick Start" section with step-by-step commands to clone the repository, configure `.env`, start services with Docker Compose, run migrations, and verify the health check endpoint.
3. THE README SHALL include a "Local Development (without Docker)" section with commands to create a virtual environment, install dependencies, start a local PostgreSQL instance, run migrations, and start the development server with `uvicorn --reload`.
4. THE README SHALL include an "Environment Variables" reference table listing every Settings field, its type, default value, and a one-line description.
5. THE README SHALL include a "Project Structure" section with an annotated directory tree explaining the purpose of each package.
6. THE README SHALL include an "API Documentation" section explaining that Swagger UI is available at `http://localhost:8000/docs` in non-production environments.
