# ─────────────────────────────────────────────────────────────────────────────
# Stage 1 — builder
# Install all Python dependencies into an isolated virtual environment.
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

# Install build tools needed for C-extension packages (e.g. asyncpg).
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment in a known location.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy only the dependency manifest first (better layer caching).
COPY pyproject.toml ./

# Upgrade pip and install all project dependencies.
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -e .


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2 — runtime
# Minimal image — only the venv and application code.
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Install runtime-only system library for asyncpg.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy the pre-built virtual environment from the builder stage.
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create a non-root user (UID 1000) to run the application.
RUN groupadd --gid 1000 appgroup \
    && useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Set working directory.
WORKDIR /app

# Copy application source code.
COPY --chown=appuser:appgroup . .

# Switch to non-root user.
USER appuser

# Expose the application port.
EXPOSE 8000

# Health check — verifies the process is responding.
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Default command — can be overridden in docker-compose for development.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
