# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Application configuration with environment validation."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ===========================================
    # Application
    # ===========================================
    APP_NAME: str = "FastAPI Enterprise Boilerplate"
    APP_VERSION: str = "0.9.0"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = Field(default=False)

    # ===========================================
    # Database
    # ===========================================
    DATABASE_URL: PostgresDsn = Field(
        default="postgresql+asyncpg://boilerplate:boilerplate@localhost:5432/boilerplate"
    )
    DB_POOL_SIZE: int = Field(default=10, ge=1, le=100)
    DB_MAX_OVERFLOW: int = Field(default=20, ge=0, le=100)
    DB_POOL_TIMEOUT: int = Field(default=30, ge=1)
    DB_POOL_RECYCLE: int = Field(default=3600, ge=60, description="Recycle connections after N seconds")
    DB_ECHO: bool = Field(default=False, description="Log SQL queries")

    # ===========================================
    # Redis
    # ===========================================
    REDIS_URL_OVERRIDE: str | None = Field(default=None, alias="REDIS_URL")
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379, ge=1, le=65535)
    REDIS_PASSWORD: str | None = Field(default=None)
    REDIS_DB: int = Field(default=0, ge=0, le=15)

    # ===========================================
    # Cache Configuration
    # ===========================================
    CACHE_ENABLED: bool = Field(
        default=True, description="Enable/disable Redis caching"
    )
    CACHE_PREFIX: str = Field(
        default="fastapi_cache", description="Prefix for all cache keys"
    )
    CACHE_DEFAULT_TTL: int = Field(
        default=300,
        ge=1,
        le=86400,
        description="Default cache TTL in seconds (5 minutes)",
    )
    CACHE_USER_TTL: int = Field(
        default=60,
        ge=1,
        le=3600,
        description="TTL for user cache in seconds (1 minute)",
    )
    CACHE_ROLE_TTL: int = Field(
        default=300,
        ge=1,
        le=3600,
        description="TTL for role cache in seconds (5 minutes)",
    )
    CACHE_TENANT_TTL: int = Field(
        default=600,
        ge=1,
        le=3600,
        description="TTL for tenant cache in seconds (10 minutes)",
    )

    # ===========================================
    # Frontend URL (used for email links, password reset, etc.)
    # ===========================================
    FRONTEND_URL: str = Field(
        default="http://localhost:3000",
        description="Frontend application URL for email links and OAuth callbacks",
    )

    # ===========================================
    # JWT Authentication
    # ===========================================
    JWT_SECRET_KEY: str = Field(
        default="change-this-in-production-with-strong-secret-key-min-32-chars",
        min_length=32,
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15, ge=1, le=60)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, ge=1, le=30)

    # ===========================================
    # Encryption (at-rest secrets: MFA, OAuth tokens)
    # ===========================================
    ENCRYPTION_KEY: str = Field(
        default="",
        description=(
            "Separate Fernet-compatible key for encrypting secrets at rest. "
            "If empty, a key is derived from JWT_SECRET_KEY (acceptable for dev, "
            "not recommended for production)."
        ),
    )

    # ===========================================
    # Cookie-based Authentication
    # ===========================================
    AUTH_COOKIE_SECURE: bool = Field(
        default=False,
        description="Set Secure flag on auth cookies (True in production with HTTPS)",
    )
    AUTH_COOKIE_DOMAIN: str | None = Field(
        default=None, description="Domain for auth cookies (None = current domain only)"
    )
    AUTH_COOKIE_SAMESITE: Literal["lax", "strict", "none"] = Field(
        default="lax", description="SameSite policy for auth cookies"
    )

    # ===========================================
    # Account Security
    # ===========================================
    ACCOUNT_LOCKOUT_ENABLED: bool = Field(
        default=True, description="Enable account lockout after failed login attempts"
    )
    ACCOUNT_LOCKOUT_THRESHOLD: int = Field(
        default=5,
        ge=3,
        le=10,
        description="Number of failed attempts before account lockout",
    )
    ACCOUNT_LOCKOUT_DURATION_MINUTES: int = Field(
        default=30, ge=5, le=1440, description="Duration of account lockout in minutes"
    )
    EMAIL_VERIFICATION_REQUIRED: bool = Field(
        default=True, description="Require email verification for new users"
    )
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = Field(
        default=24,
        ge=1,
        le=72,
        description="Email verification token expiration in hours",
    )

    # ===========================================
    # Rate Limiting
    # ===========================================
    RATE_LIMIT_ENABLED: bool = Field(default=True)
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(default=100, ge=1)

    # ===========================================
    # Internationalization (i18n)
    # ===========================================
    DEFAULT_LOCALE: Literal["en", "es", "pt"] = Field(
        default="en", description="Default locale for the application"
    )
    SUPPORTED_LOCALES: list[str] = Field(
        default=["en", "es", "pt"], description="List of supported locales"
    )

    # ===========================================
    # Observability (OpenTelemetry)
    # ===========================================
    OTEL_ENABLED: bool = Field(default=False)
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = Field(default=None)
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    LOG_FORMAT: Literal["json", "console"] = Field(default="console")

    # ===========================================
    # CORS
    # ===========================================
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"]
    )

    # ===========================================
    # Storage (Pluggable: auto, local, s3, minio)
    # ===========================================
    STORAGE_BACKEND: Literal["auto", "local", "s3", "minio"] = Field(
        default="auto",
        description="Storage backend: auto (fallback to local), local, s3, minio",
    )
    STORAGE_LOCAL_PATH: str = Field(
        default="./storage", description="Local storage path (relative or absolute)"
    )

    # AWS S3 Configuration (optional)
    S3_BUCKET: str | None = Field(default=None)
    S3_REGION: str = Field(default="us-east-1")
    S3_ENDPOINT_URL: str | None = Field(
        default=None, description="Custom S3 endpoint (for S3-compatible services)"
    )
    AWS_ACCESS_KEY_ID: str | None = Field(default=None)
    AWS_SECRET_ACCESS_KEY: str | None = Field(default=None)

    # MinIO Configuration (S3-compatible, optional)
    MINIO_ENDPOINT: str | None = Field(default=None)
    MINIO_BUCKET: str | None = Field(default=None)
    MINIO_ACCESS_KEY: str | None = Field(default=None)
    MINIO_SECRET_KEY: str | None = Field(default=None)
    MINIO_SECURE: bool = Field(default=True, description="Use HTTPS for MinIO")

    # ===========================================
    # WebSocket & Real-time Features
    # ===========================================
    WEBSOCKET_ENABLED: bool = Field(
        default=True,
        description="Enable/disable WebSocket functionality for notifications",
    )
    WEBSOCKET_NOTIFICATIONS: bool = Field(
        default=True, description="Enable real-time notifications via WebSocket"
    )

    # ===========================================
    # Email Configuration
    # ===========================================
    EMAIL_BACKEND: Literal["console", "smtp", "sendgrid", "aws_ses", "mailgun"] = Field(
        default="console",
        description="Email backend: console (dev), smtp, sendgrid, aws_ses, mailgun",
    )
    EMAIL_FROM: str = Field(
        default="noreply@example.com", description="Default from email address"
    )
    EMAIL_FROM_NAME: str = Field(
        default="FastAPI Enterprise", description="Default from name for emails"
    )
    EMAIL_SUPPORT: str = Field(
        default="support@example.com",
        description="Support email address shown in email templates",
    )

    # SMTP Configuration (when EMAIL_BACKEND=smtp)
    SMTP_HOST: str | None = Field(default=None)
    SMTP_PORT: int = Field(default=587)
    SMTP_USERNAME: str | None = Field(default=None)
    SMTP_PASSWORD: str | None = Field(default=None)
    SMTP_TLS: bool = Field(default=True, description="Use TLS for SMTP connection")
    SMTP_SSL: bool = Field(default=False, description="Use SSL for SMTP connection")

    # SendGrid Configuration (when EMAIL_BACKEND=sendgrid)
    SENDGRID_API_KEY: str | None = Field(default=None)

    # AWS SES Configuration (when EMAIL_BACKEND=aws_ses)
    SES_REGION: str = Field(default="us-east-1")
    # Uses AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY from Storage section

    # Mailgun Configuration (when EMAIL_BACKEND=mailgun)
    MAILGUN_API_KEY: str | None = Field(default=None)
    MAILGUN_DOMAIN: str | None = Field(default=None)

    # ===========================================
    # OAuth2 / SSO Configuration
    # ===========================================
    APP_BASE_URL: str = Field(
        default="http://localhost:8000", description="Base URL for OAuth callbacks"
    )

    # Google OAuth
    OAUTH_GOOGLE_CLIENT_ID: str | None = Field(default=None)
    OAUTH_GOOGLE_CLIENT_SECRET: str | None = Field(default=None)

    # GitHub OAuth
    OAUTH_GITHUB_CLIENT_ID: str | None = Field(default=None)
    OAUTH_GITHUB_CLIENT_SECRET: str | None = Field(default=None)

    # Microsoft/Azure AD OAuth
    OAUTH_MICROSOFT_CLIENT_ID: str | None = Field(default=None)
    OAUTH_MICROSOFT_CLIENT_SECRET: str | None = Field(default=None)
    OAUTH_MICROSOFT_TENANT_ID: str | None = Field(
        default="common", description="Azure AD tenant ID or 'common' for multi-tenant"
    )

    # ===========================================
    # Full-Text Search Configuration
    # ===========================================
    SEARCH_BACKEND: Literal["postgres"] = Field(
        default="postgres", description="Search backend: PostgreSQL built-in FTS"
    )
    SEARCH_INDEX_PREFIX: str = Field(
        default="app", description="Prefix for search indices"
    )

    # PostgreSQL FTS Configuration
    SEARCH_PG_LANGUAGE: str = Field(
        default="english",
        description="PostgreSQL text search configuration (english, spanish, etc.)",
    )

    @model_validator(mode="after")
    def _validate_security(self) -> "Settings":
        """Fail-fast: reject insecure defaults in production/staging."""
        if self.ENVIRONMENT in ("production", "staging"):
            _INSECURE_DEFAULTS = {
                "change-this-in-production-with-strong-secret",
                "change-this-in-production-with-strong-secret-key-min-32-chars",
            }
            if self.JWT_SECRET_KEY in _INSECURE_DEFAULTS:
                raise ValueError(
                    "FATAL: JWT_SECRET_KEY must be set to a unique, strong secret "
                    f"in {self.ENVIRONMENT} environment. "
                    "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(64))'"
                )
            if not self.AUTH_COOKIE_SECURE:
                raise ValueError(
                    f"FATAL: AUTH_COOKIE_SECURE must be True in {self.ENVIRONMENT} "
                    "environment. Set AUTH_COOKIE_SECURE=true in your .env file."
                )
            _INSECURE_ENCRYPTION_DEFAULTS = {
                "dev-only-encryption-key-change-in-production-min-32-chars",
                "",
            }
            if (
                not self.ENCRYPTION_KEY
                or self.ENCRYPTION_KEY in _INSECURE_ENCRYPTION_DEFAULTS
            ):
                raise ValueError(
                    f"FATAL: ENCRYPTION_KEY must be set to a unique, strong secret in {self.ENVIRONMENT} "
                    "environment. Sharing JWT_SECRET_KEY for encryption is insecure. "
                    "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
                )
            # Validate Redis password is not a well-known default
            _INSECURE_REDIS_PASSWORDS = {
                "changeme-in-production",
                "staging-redis-pass",
                "devpassword",
                "",
            }
            redis_pass = self.REDIS_PASSWORD or ""
            if redis_pass in _INSECURE_REDIS_PASSWORDS:
                raise ValueError(
                    f"FATAL: REDIS_PASSWORD must be set to a strong password "
                    f"in {self.ENVIRONMENT} environment."
                )
            # Validate DATABASE_URL doesn't use default dev credentials
            db_url = str(self.DATABASE_URL)
            if "boilerplate:boilerplate@" in db_url:
                raise ValueError(
                    f"FATAL: DATABASE_URL contains default credentials "
                    f"in {self.ENVIRONMENT} environment. "
                    "Use a strong password for the database connection."
                )
        return self

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.ENVIRONMENT == "production"

    @property
    def redis_url(self) -> str:
        """Build Redis URL from components or use override."""
        # Prioritize REDIS_URL environment variable if set
        if self.REDIS_URL_OVERRIDE:
            return self.REDIS_URL_OVERRIDE
        # Otherwise build from components
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def REDIS_URL(self) -> str:
        """Alias for redis_url (for consistency)."""
        return self.redis_url


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
