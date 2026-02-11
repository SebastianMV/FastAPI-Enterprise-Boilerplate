# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Extended tests for application configuration."""

from __future__ import annotations


class TestSettingsStructure:
    """Tests for Settings class structure."""

    def test_settings_import(self) -> None:
        """Test Settings can be imported."""
        from app.config import Settings

        assert Settings is not None

    def test_settings_instance_import(self) -> None:
        """Test settings instance can be imported."""
        from app.config import settings

        assert settings is not None

    def test_get_settings_function(self) -> None:
        """Test get_settings function can be imported."""
        from app.config import get_settings

        assert get_settings is not None
        assert callable(get_settings)


class TestSettingsAppConfig:
    """Tests for application configuration settings."""

    def test_app_name_default(self) -> None:
        """Test APP_NAME has default value."""
        from app.config import settings

        assert settings.APP_NAME == "FastAPI Enterprise Boilerplate"

    def test_app_version_default(self) -> None:
        """Test APP_VERSION has default value."""
        from app.config import settings

        assert settings.APP_VERSION == "1.0.0"

    def test_environment_default(self) -> None:
        """Test ENVIRONMENT has default value."""
        from app.config import settings

        assert settings.ENVIRONMENT in ["development", "staging", "production"]

    def test_debug_is_bool(self) -> None:
        """Test DEBUG is a boolean."""
        from app.config import settings

        assert isinstance(settings.DEBUG, bool)


class TestSettingsDatabaseConfig:
    """Tests for database configuration settings."""

    def test_database_url_exists(self) -> None:
        """Test DATABASE_URL exists."""
        from app.config import settings

        assert settings.DATABASE_URL is not None

    def test_db_pool_size_valid(self) -> None:
        """Test DB_POOL_SIZE is valid."""
        from app.config import settings

        assert settings.DB_POOL_SIZE >= 1
        assert settings.DB_POOL_SIZE <= 100

    def test_db_max_overflow_valid(self) -> None:
        """Test DB_MAX_OVERFLOW is valid."""
        from app.config import settings

        assert settings.DB_MAX_OVERFLOW >= 0
        assert settings.DB_MAX_OVERFLOW <= 100

    def test_db_pool_timeout_valid(self) -> None:
        """Test DB_POOL_TIMEOUT is valid."""
        from app.config import settings

        assert settings.DB_POOL_TIMEOUT >= 1


class TestSettingsRedisConfig:
    """Tests for Redis configuration settings."""

    def test_redis_host_exists(self) -> None:
        """Test REDIS_HOST exists."""
        from app.config import settings

        assert settings.REDIS_HOST is not None

    def test_redis_port_valid(self) -> None:
        """Test REDIS_PORT is valid."""
        from app.config import settings

        assert settings.REDIS_PORT >= 1
        assert settings.REDIS_PORT <= 65535

    def test_redis_db_valid(self) -> None:
        """Test REDIS_DB is valid."""
        from app.config import settings

        assert settings.REDIS_DB >= 0
        assert settings.REDIS_DB <= 15


class TestSettingsCacheConfig:
    """Tests for cache configuration settings."""

    def test_cache_enabled_is_bool(self) -> None:
        """Test CACHE_ENABLED is boolean."""
        from app.config import settings

        assert isinstance(settings.CACHE_ENABLED, bool)

    def test_cache_prefix_exists(self) -> None:
        """Test CACHE_PREFIX exists."""
        from app.config import settings

        assert settings.CACHE_PREFIX is not None

    def test_cache_ttl_values(self) -> None:
        """Test cache TTL values are valid."""
        from app.config import settings

        assert settings.CACHE_DEFAULT_TTL >= 1
        assert settings.CACHE_USER_TTL >= 1
        assert settings.CACHE_ROLE_TTL >= 1
        assert settings.CACHE_TENANT_TTL >= 1


class TestSettingsJWTConfig:
    """Tests for JWT configuration settings."""

    def test_jwt_secret_key_exists(self) -> None:
        """Test JWT_SECRET_KEY exists."""
        from app.config import settings

        assert settings.JWT_SECRET_KEY is not None
        assert len(settings.JWT_SECRET_KEY) >= 32

    def test_jwt_algorithm_default(self) -> None:
        """Test JWT_ALGORITHM has default value."""
        from app.config import settings

        assert settings.JWT_ALGORITHM == "HS256"

    def test_access_token_expire_valid(self) -> None:
        """Test ACCESS_TOKEN_EXPIRE_MINUTES is valid."""
        from app.config import settings

        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES >= 1
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES <= 60

    def test_refresh_token_expire_valid(self) -> None:
        """Test REFRESH_TOKEN_EXPIRE_DAYS is valid."""
        from app.config import settings

        assert settings.REFRESH_TOKEN_EXPIRE_DAYS >= 1
        assert settings.REFRESH_TOKEN_EXPIRE_DAYS <= 30


class TestSettingsRateLimitConfig:
    """Tests for rate limiting configuration."""

    def test_rate_limit_enabled_is_bool(self) -> None:
        """Test RATE_LIMIT_ENABLED is boolean."""
        from app.config import settings

        assert isinstance(settings.RATE_LIMIT_ENABLED, bool)

    def test_rate_limit_requests_valid(self) -> None:
        """Test RATE_LIMIT_REQUESTS_PER_MINUTE is valid."""
        from app.config import settings

        assert settings.RATE_LIMIT_REQUESTS_PER_MINUTE >= 1


class TestGetSettingsCaching:
    """Tests for get_settings caching behavior."""

    def test_get_settings_returns_same_instance(self) -> None:
        """Test get_settings returns cached instance."""
        from app.config import get_settings

        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2

    def test_get_settings_returns_valid_settings(self) -> None:
        """Test get_settings returns valid Settings object."""
        from app.config import Settings, get_settings

        settings = get_settings()
        assert isinstance(settings, Settings)
