# ===========================================
# FastAPI Enterprise Boilerplate - Dockerfile
# ===========================================

# Stage 1: Base
# Pin to minor; update patch periodically: docker pull python:3.13-slim
FROM python:3.14-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore

WORKDIR /app

# Stage 2: Dependencies
FROM base AS deps

COPY requirements.txt ./
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Stage 3: Development
FROM deps AS development
# NOTE: Runs as root for hot-reload file watching in mounted volumes.
# Production stage below uses a non-root 'appuser'.

COPY pyproject.toml ./
COPY . .
RUN pip install -e .[dev]

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# NOTE: For production builds, use Dockerfile.prod (multi-stage with venv,
# non-root user, uvloop, stripped dev artifacts, proper healthcheck).
