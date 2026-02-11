# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Tests for application configuration module."""




class TestSettingsDefaults:
    """Tests for Settings default values."""

    def test_app_name_default(self) -> None:
        """Test default app name."""
        from app.config import Settings

        settings = Settings()
        assert "FastAPI" in settings.APP_NAME

    def test_app_version_default(self) -> None:
        """Test default app version."""
        from app.config import Settings

        settings = Settings()
        assert settings.APP_VERSION is not None
        assert "." in settings.APP_VERSION  # Should be semver

    def test_environment_default(self) -> None:
        """Test default environment."""
        from app.config import Settings

        settings = Settings()
        assert settings.ENVIRONMENT in ["development", "staging", "production"]

    def test_debug_default(self) -> None:
        """Test default debug mode."""
        from app.config import Settings

        settings = Settings()
        assert isinstance(settings.DEBUG, bool)

    def test_database_pool_defaults(self) -> None:
        """Test database pool defaults."""
        from app.config import Settings

        settings = Settings()
        assert settings.DB_POOL_SIZE >= 1
        assert settings.DB_MAX_OVERFLOW >= 0
        assert settings.DB_POOL_TIMEOUT >= 1


class TestCacheSettings:
    """Tests for cache configuration settings."""

    def test_cache_enabled_default(self) -> None:
        """Test cache enabled by default."""
        from app.config import Settings

        settings = Settings()
        assert settings.CACHE_ENABLED is True

    def test_cache_prefix_default(self) -> None:
        """Test cache prefix has default."""
        from app.config import Settings

        settings = Settings()
        assert settings.CACHE_PREFIX is not None
        assert len(settings.CACHE_PREFIX) > 0

    def test_cache_ttl_defaults(self) -> None:
        """Test cache TTL defaults."""
        from app.config import Settings

        settings = Settings()
        assert settings.CACHE_DEFAULT_TTL > 0
        assert settings.CACHE_USER_TTL > 0
        assert settings.CACHE_ROLE_TTL > 0


class TestRedisSettings:
    """Tests for Redis configuration settings."""

    def test_redis_host_default(self) -> None:
        """Test Redis host default."""
        from app.config import Settings

        settings = Settings()
        assert settings.REDIS_HOST is not None

    def test_redis_port_default(self) -> None:
        """Test Redis port default."""
        from app.config import Settings

        settings = Settings()
        assert 1 <= settings.REDIS_PORT <= 65535

    def test_redis_db_default(self) -> None:
        """Test Redis DB default."""
        from app.config import Settings

        settings = Settings()
        assert 0 <= settings.REDIS_DB <= 15


class TestSecuritySettings:
    """Tests for security configuration settings."""

    def test_jwt_secret_key_exists(self) -> None:
        """Test JWT secret key setting exists."""
        from app.config import Settings

        settings = Settings()
        assert hasattr(settings, "JWT_SECRET_KEY")

    def test_jwt_algorithm_exists(self) -> None:
        """Test JWT algorithm setting exists."""
        from app.config import Settings

        settings = Settings()
        assert hasattr(settings, "JWT_ALGORITHM")

    def test_access_token_expire_exists(self) -> None:
        """Test access token expiration exists."""
        from app.config import Settings

        settings = Settings()
        assert hasattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES")


class TestSettingsValidation:
    """Tests for settings validation."""

    def test_settings_model_config(self) -> None:
        """Test settings model configuration."""
        from app.config import Settings

        config = Settings.model_config
        assert config.get("env_file") is not None
        assert config.get("case_sensitive") is False


class TestGetSettings:
    """Tests for get_settings function."""

    def test_get_settings_returns_settings(self) -> None:
        """Test get_settings returns Settings instance."""
        from app.config import get_settings

        settings = get_settings()
        assert settings is not None

    def test_get_settings_cached(self) -> None:
        """Test get_settings is cached."""
        from app.config import get_settings

        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2


class TestSettingsInstance:
    """Tests for the settings singleton."""

    def test_settings_singleton_exists(self) -> None:
        """Test settings singleton exists."""
        from app.config import settings

        assert settings is not None

    def test_settings_has_database_url(self) -> None:
        """Test settings has database URL."""
        from app.config import settings

        assert settings.DATABASE_URL is not None


class TestEnvironmentLiteral:
    """Tests for environment literal type."""

    def test_environment_is_valid_literal(self) -> None:
        """Test environment is a valid literal value."""
        from app.config import settings

        valid_environments = ["development", "staging", "production"]
        assert settings.ENVIRONMENT in valid_environments


class TestCorsSettings:
    """Tests for CORS configuration."""

    def test_cors_origins_exists(self) -> None:
        """Test CORS origins setting exists."""
        from app.config import Settings

        settings = Settings()
        assert hasattr(settings, "CORS_ORIGINS")


class TestEmailSettings:
    """Tests for email configuration."""

    def test_email_settings_exist(self) -> None:
        """Test email settings exist."""
        from app.config import Settings

        settings = Settings()
        # Check common email settings exist
        assert hasattr(settings, "SMTP_HOST") or hasattr(settings, "EMAIL_ENABLED")


class TestSettingsEnvironmentVariables:
    """Tests for environment variable loading."""

    def test_settings_env_file_encoding(self) -> None:
        """Test settings uses UTF-8 encoding."""
        from app.config import Settings

        assert Settings.model_config.get("env_file_encoding") == "utf-8"

    def test_settings_extra_ignore(self) -> None:
        """Test settings ignores extra env vars."""
        from app.config import Settings

        assert Settings.model_config.get("extra") == "ignore"
