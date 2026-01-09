# ===========================================
# FastAPI Enterprise Boilerplate - Dockerfile
# ===========================================

# Stage 1: Base
FROM python:3.13-slim AS base

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

COPY pyproject.toml ./
COPY . .
RUN pip install -e .[dev]

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Stage 4: Production
FROM deps AS production

COPY pyproject.toml ./
COPY . .
RUN pip install .

# Non-root user for security
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
