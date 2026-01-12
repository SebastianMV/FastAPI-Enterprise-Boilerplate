# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Application configuration with environment validation."""

from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field, PostgresDsn
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
    APP_VERSION: str = "1.0.0"
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

    # ===========================================
    # Redis
    # ===========================================
    REDIS_URL_OVERRIDE: Optional[str] = Field(default=None, alias="REDIS_URL")
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379, ge=1, le=65535)
    REDIS_PASSWORD: Optional[str] = Field(default=None)
    REDIS_DB: int = Field(default=0, ge=0, le=15)

    # ===========================================
    # Cache Configuration
    # ===========================================
    CACHE_ENABLED: bool = Field(
        default=True,
        description="Enable/disable Redis caching"
    )
    CACHE_PREFIX: str = Field(
        default="fastapi_cache",
        description="Prefix for all cache keys"
    )
    CACHE_DEFAULT_TTL: int = Field(
        default=300,
        ge=1,
        le=86400,
        description="Default cache TTL in seconds (5 minutes)"
    )
    CACHE_USER_TTL: int = Field(
        default=60,
        ge=1,
        le=3600,
        description="TTL for user cache in seconds (1 minute)"
    )
    CACHE_ROLE_TTL: int = Field(
        default=300,
        ge=1,
        le=3600,
        description="TTL for role cache in seconds (5 minutes)"
    )
    CACHE_TENANT_TTL: int = Field(
        default=600,
        ge=1,
        le=3600,
        description="TTL for tenant cache in seconds (10 minutes)"
    )

    # ===========================================
    # JWT Authentication
    # ===========================================
    JWT_SECRET_KEY: str = Field(
        default="change-this-in-production-with-strong-secret",
        min_length=32,
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15, ge=1, le=60)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, ge=1, le=30)

    # ===========================================
    # Account Security
    # ===========================================
    ACCOUNT_LOCKOUT_ENABLED: bool = Field(
        default=True,
        description="Enable account lockout after failed login attempts"
    )
    ACCOUNT_LOCKOUT_THRESHOLD: int = Field(
        default=5,
        ge=3,
        le=10,
        description="Number of failed attempts before account lockout"
    )
    ACCOUNT_LOCKOUT_DURATION_MINUTES: int = Field(
        default=30,
        ge=5,
        le=1440,
        description="Duration of account lockout in minutes"
    )
    EMAIL_VERIFICATION_REQUIRED: bool = Field(
        default=True,
        description="Require email verification for new users"
    )
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = Field(
        default=24,
        ge=1,
        le=72,
        description="Email verification token expiration in hours"
    )
    
    # ===========================================
    # Rate Limiting
    # ===========================================
    RATE_LIMIT_ENABLED: bool = Field(default=True)
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(default=100, ge=1)

    # ===========================================
    # Internationalization (i18n)
    # ===========================================
    DEFAULT_LOCALE: Literal["en", "es", "pt", "fr", "de"] = Field(
        default="en",
        description="Default locale for the application"
    )
    SUPPORTED_LOCALES: list[str] = Field(
        default=["en", "es", "pt", "fr", "de"],
        description="List of supported locales"
    )

    # ===========================================
    # Observability (OpenTelemetry)
    # ===========================================
    OTEL_ENABLED: bool = Field(default=False)
    OTEL_EXPORTER_OTLP_ENDPOINT: Optional[str] = Field(default=None)
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
        description="Storage backend: auto (fallback to local), local, s3, minio"
    )
    STORAGE_LOCAL_PATH: str = Field(
        default="./storage",
        description="Local storage path (relative or absolute)"
    )
    
    # AWS S3 Configuration (optional)
    S3_BUCKET: Optional[str] = Field(default=None)
    S3_REGION: str = Field(default="us-east-1")
    S3_ENDPOINT_URL: Optional[str] = Field(
        default=None, 
        description="Custom S3 endpoint (for S3-compatible services)"
    )
    AWS_ACCESS_KEY_ID: Optional[str] = Field(default=None)
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(default=None)
    
    # MinIO Configuration (S3-compatible, optional)
    MINIO_ENDPOINT: Optional[str] = Field(default=None)
    MINIO_BUCKET: Optional[str] = Field(default=None)
    MINIO_ACCESS_KEY: Optional[str] = Field(default=None)
    MINIO_SECRET_KEY: Optional[str] = Field(default=None)
    MINIO_SECURE: bool = Field(default=True, description="Use HTTPS for MinIO")

    # ===========================================
    # WebSocket & Real-time Features (Pluggable)
    # ===========================================
    WEBSOCKET_ENABLED: bool = Field(
        default=True,
        description="Enable/disable all WebSocket functionality (required for notifications)"
    )
    WEBSOCKET_BACKEND: Literal["memory", "redis"] = Field(
        default="memory",
        description="WebSocket backend: memory (single instance) or redis (scalable)"
    )
    WEBSOCKET_NOTIFICATIONS: bool = Field(
        default=True,
        description="Enable real-time notifications via WebSocket (recommended)"
    )

    # ===========================================
    # Email Configuration
    # ===========================================
    EMAIL_BACKEND: Literal["console", "smtp", "sendgrid", "aws_ses", "mailgun"] = Field(
        default="console",
        description="Email backend: console (dev), smtp, sendgrid, aws_ses, mailgun"
    )
    EMAIL_FROM: str = Field(
        default="noreply@example.com",
        description="Default from email address"
    )
    EMAIL_FROM_NAME: str = Field(
        default="FastAPI Enterprise",
        description="Default from name for emails"
    )
    EMAIL_SUPPORT: str = Field(
        default="support@example.com",
        description="Support email address shown in email templates"
    )
    
    # SMTP Configuration (when EMAIL_BACKEND=smtp)
    SMTP_HOST: Optional[str] = Field(default=None)
    SMTP_PORT: int = Field(default=587)
    SMTP_USERNAME: Optional[str] = Field(default=None)
    SMTP_PASSWORD: Optional[str] = Field(default=None)
    SMTP_TLS: bool = Field(default=True, description="Use TLS for SMTP connection")
    SMTP_SSL: bool = Field(default=False, description="Use SSL for SMTP connection")
    
    # SendGrid Configuration (when EMAIL_BACKEND=sendgrid)
    SENDGRID_API_KEY: Optional[str] = Field(default=None)
    
    # AWS SES Configuration (when EMAIL_BACKEND=aws_ses)
    SES_REGION: str = Field(default="us-east-1")
    # Uses AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY from Storage section
    
    # Mailgun Configuration (when EMAIL_BACKEND=mailgun)
    MAILGUN_API_KEY: Optional[str] = Field(default=None)
    MAILGUN_DOMAIN: Optional[str] = Field(default=None)

    # ===========================================
    # OAuth2 / SSO Configuration
    # ===========================================
    APP_BASE_URL: str = Field(
        default="http://localhost:8000",
        description="Base URL for OAuth callbacks"
    )
    
    # Google OAuth
    OAUTH_GOOGLE_CLIENT_ID: Optional[str] = Field(default=None)
    OAUTH_GOOGLE_CLIENT_SECRET: Optional[str] = Field(default=None)
    
    # GitHub OAuth
    OAUTH_GITHUB_CLIENT_ID: Optional[str] = Field(default=None)
    OAUTH_GITHUB_CLIENT_SECRET: Optional[str] = Field(default=None)
    
    # Microsoft/Azure AD OAuth
    OAUTH_MICROSOFT_CLIENT_ID: Optional[str] = Field(default=None)
    OAUTH_MICROSOFT_CLIENT_SECRET: Optional[str] = Field(default=None)
    OAUTH_MICROSOFT_TENANT_ID: Optional[str] = Field(
        default="common",
        description="Azure AD tenant ID or 'common' for multi-tenant"
    )

    # ===========================================
    # Full-Text Search Configuration
    # ===========================================
    SEARCH_BACKEND: Literal["postgres", "elasticsearch"] = Field(
        default="postgres",
        description="Search backend: postgres (built-in FTS) or elasticsearch"
    )
    SEARCH_INDEX_PREFIX: str = Field(
        default="app",
        description="Prefix for search indices"
    )
    
    # PostgreSQL FTS Configuration
    SEARCH_PG_LANGUAGE: str = Field(
        default="english",
        description="PostgreSQL text search configuration (english, spanish, etc.)"
    )
    
    # Elasticsearch Configuration (when SEARCH_BACKEND=elasticsearch)
    ELASTICSEARCH_URL: Optional[str] = Field(
        default="http://localhost:9200",
        description="Elasticsearch server URL"
    )
    ELASTICSEARCH_USERNAME: Optional[str] = Field(default=None)
    ELASTICSEARCH_PASSWORD: Optional[str] = Field(default=None)
    ELASTICSEARCH_VERIFY_CERTS: bool = Field(default=True)

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
