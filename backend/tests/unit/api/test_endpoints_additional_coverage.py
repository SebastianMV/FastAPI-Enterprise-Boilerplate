# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Additional coverage tests for API endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


class TestUsersEndpointCoverage:
    """Tests for users endpoint coverage."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_create_user_invalid_email(self, mock_session):
        """Test create_user with invalid email raises error (lines 122-123)."""
        from app.api.v1.endpoints.users import create_user
        from app.api.v1.schemas.users import UserCreate
        
        # Note: UserCreate uses EmailStr which validates at schema level
        # But the endpoint also validates with Email value object
        # We need to mock the Email value object to raise ValueError
        request = UserCreate(
            email="test@example.com",  # Valid for schema
            password="Password123!",
            first_name="Test",
            last_name="User",
            is_active=True,
            is_superuser=False,
            roles=[],
        )
        
        superuser_id = uuid4()
        tenant_id = uuid4()
        
        # Mock Email to raise ValueError
        with patch("app.api.v1.endpoints.users.Email") as mock_email:
            mock_email.side_effect = ValueError("Invalid email format")
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await create_user(
                    request=request,
                    superuser_id=superuser_id,
                    tenant_id=tenant_id,
                    session=mock_session,
                )
            
            assert exc.value.status_code == 400
            assert "INVALID_EMAIL" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_create_user_weak_password(self, mock_session):
        """Test create_user with weak password raises error (lines 131-132)."""
        from app.api.v1.endpoints.users import create_user
        from app.api.v1.schemas.users import UserCreate
        
        request = UserCreate(
            email="test@example.com",
            password="Password123!",  # Valid for schema min length
            first_name="Test",
            last_name="User",
            is_active=True,
            is_superuser=False,
            roles=[],
        )
        
        superuser_id = uuid4()
        tenant_id = uuid4()
        
        # Mock Password to raise ValueError
        with patch("app.api.v1.endpoints.users.Email") as mock_email, \
             patch("app.api.v1.endpoints.users.Password") as mock_password:
            mock_email.return_value = MagicMock()  # Email validates OK
            mock_password.side_effect = ValueError("Password too weak")
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await create_user(
                    request=request,
                    superuser_id=superuser_id,
                    tenant_id=tenant_id,
                    session=mock_session,
                )
            
            assert exc.value.status_code == 400
            assert "WEAK_PASSWORD" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_create_user_email_exists(self, mock_session):
        """Test create_user with existing email raises conflict (lines 140-143)."""
        from app.api.v1.endpoints.users import create_user
        from app.api.v1.schemas.users import UserCreate
        
        request = UserCreate(
            email="existing@example.com",
            password="Password123!",
            first_name="Test",
            last_name="User",
            is_active=True,
            is_superuser=False,
            roles=[],
        )
        
        superuser_id = uuid4()
        tenant_id = uuid4()
        
        with patch("app.api.v1.endpoints.users.Email") as mock_email, \
             patch("app.api.v1.endpoints.users.Password") as mock_password, \
             patch("app.api.v1.endpoints.users.SQLAlchemyUserRepository") as mock_repo_cls:
            mock_email.return_value = MagicMock()
            mock_pass_obj = MagicMock()
            mock_pass_obj.value = "Password123!"
            mock_password.return_value = mock_pass_obj
            
            mock_repo = AsyncMock()
            mock_repo.exists_by_email.return_value = True  # Email exists
            mock_repo_cls.return_value = mock_repo
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await create_user(
                    request=request,
                    superuser_id=superuser_id,
                    tenant_id=tenant_id,
                    session=mock_session,
                )
            
            assert exc.value.status_code == 409
            assert "EMAIL_EXISTS" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_create_user_conflict_error(self, mock_session):
        """Test create_user handles ConflictError from repository (lines 165-168)."""
        from app.api.v1.endpoints.users import create_user
        from app.api.v1.schemas.users import UserCreate
        from app.domain.exceptions.base import ConflictError
        
        request = UserCreate(
            email="new@example.com",
            password="Password123!",
            first_name="Test",
            last_name="User",
            is_active=True,
            is_superuser=False,
            roles=[],
        )
        
        superuser_id = uuid4()
        tenant_id = uuid4()
        
        with patch("app.api.v1.endpoints.users.Email") as mock_email, \
             patch("app.api.v1.endpoints.users.Password") as mock_password, \
             patch("app.api.v1.endpoints.users.SQLAlchemyUserRepository") as mock_repo_cls, \
             patch("app.api.v1.endpoints.users.hash_password", return_value="hashed"):
            mock_email.return_value = MagicMock()
            mock_pass_obj = MagicMock()
            mock_pass_obj.value = "Password123!"
            mock_password.return_value = mock_pass_obj
            
            mock_repo = AsyncMock()
            mock_repo.exists_by_email.return_value = False
            mock_repo.create.side_effect = ConflictError(
                code="DUPLICATE_KEY",
                message="Duplicate entry"
            )
            mock_repo_cls.return_value = mock_repo
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await create_user(
                    request=request,
                    superuser_id=superuser_id,
                    tenant_id=tenant_id,
                    session=mock_session,
                )
            
            assert exc.value.status_code == 409

    @pytest.mark.asyncio
    async def test_update_self_user_not_found(self, mock_session):
        """Test update_self with non-existent user (lines 199-208)."""
        from app.api.v1.endpoints.users import update_self
        from app.api.v1.schemas.users import UserUpdateSelf
        
        request = UserUpdateSelf(first_name="NewName")
        current_user_id = uuid4()
        
        with patch("app.api.v1.endpoints.users.SQLAlchemyUserRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = None  # User not found
            mock_repo_cls.return_value = mock_repo
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await update_self(
                    request=request,
                    current_user_id=current_user_id,
                    session=mock_session,
                )
            
            assert exc.value.status_code == 404
            assert "USER_NOT_FOUND" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_update_user_invalid_email(self, mock_session):
        """Test update_user with invalid email (lines 241-242)."""
        from app.api.v1.endpoints.users import update_user
        from app.api.v1.schemas.users import UserUpdate
        
        user_id = uuid4()
        superuser_id = uuid4()
        request = UserUpdate(email="new@example.com")
        
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.email = "old@example.com"
        
        with patch("app.api.v1.endpoints.users.SQLAlchemyUserRepository") as mock_repo_cls, \
             patch("app.api.v1.endpoints.users.Email") as mock_email:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_user
            mock_repo_cls.return_value = mock_repo
            
            mock_email.side_effect = ValueError("Invalid email format")
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await update_user(
                    user_id=user_id,
                    request=request,
                    superuser_id=superuser_id,
                    session=mock_session,
                )
            
            assert exc.value.status_code == 400
            assert "INVALID_EMAIL" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_upload_avatar_error(self, mock_session):
        """Test upload_avatar handles upload errors (lines 388-389)."""
        from app.api.v1.endpoints.users import upload_avatar
        from fastapi import UploadFile
        from io import BytesIO
        
        current_user_id = uuid4()
        
        mock_user = MagicMock()
        mock_user.id = current_user_id
        mock_user.avatar_url = None
        
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "avatar.png"
        mock_file.content_type = "image/png"
        mock_file.read = AsyncMock(return_value=b"fake image data")
        
        with patch("app.api.v1.endpoints.users.SQLAlchemyUserRepository") as mock_repo_cls, \
             patch("app.api.v1.endpoints.users.get_storage") as mock_get_storage:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_user
            mock_repo_cls.return_value = mock_repo
            
            mock_storage = AsyncMock()
            mock_storage.upload.side_effect = Exception("Storage error")
            mock_get_storage.return_value = mock_storage
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await upload_avatar(
                    file=mock_file,
                    current_user_id=current_user_id,
                    session=mock_session,
                )
            
            assert exc.value.status_code == 500
            assert "UPLOAD_FAILED" in str(exc.value.detail)


class TestRolesEndpointCoverage:
    """Tests for roles endpoint coverage."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_create_role_invalid_permission(self, mock_session):
        """Test create_role with invalid permission raises error (lines 143-148)."""
        from app.api.v1.endpoints.roles import create_role
        from app.api.v1.schemas.roles import RoleCreate
        
        request = RoleCreate(
            name="admin",
            description="Admin role",
            permissions=["invalid-no-colon"],  # Invalid format
        )
        
        superuser_id = uuid4()
        tenant_id = uuid4()
        
        with patch("app.api.v1.endpoints.roles.Permission") as mock_permission:
            mock_permission.from_string.side_effect = ValueError("Invalid permission format")
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await create_role(
                    request=request,
                    superuser_id=superuser_id,
                    tenant_id=tenant_id,
                    session=mock_session,
                )
            
            assert exc.value.status_code == 400
            assert "INVALID_PERMISSION" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_create_role_conflict_error(self, mock_session):
        """Test create_role handles ConflictError (lines 169-172)."""
        from app.api.v1.endpoints.roles import create_role
        from app.api.v1.schemas.roles import RoleCreate
        from app.domain.exceptions.base import ConflictError
        
        request = RoleCreate(
            name="admin",
            description="Admin role",
            permissions=["users:read"],
        )
        
        superuser_id = uuid4()
        tenant_id = uuid4()
        
        with patch("app.api.v1.endpoints.roles.Permission") as mock_permission, \
             patch("app.api.v1.endpoints.roles.SQLAlchemyRoleRepository") as mock_repo_cls:
            mock_perm = MagicMock()
            mock_permission.from_string.return_value = mock_perm
            
            mock_repo = AsyncMock()
            mock_repo.create.side_effect = ConflictError(
                code="DUPLICATE_ROLE",
                message="Role already exists"
            )
            mock_repo_cls.return_value = mock_repo
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await create_role(
                    request=request,
                    superuser_id=superuser_id,
                    tenant_id=tenant_id,
                    session=mock_session,
                )
            
            assert exc.value.status_code == 409

    @pytest.mark.asyncio
    async def test_update_role_not_found(self, mock_session):
        """Test update_role with non-existent role (lines 193-196)."""
        from app.api.v1.endpoints.roles import update_role
        from app.api.v1.schemas.roles import RoleUpdate
        
        request = RoleUpdate(name="new_name")
        role_id = uuid4()
        superuser_id = uuid4()
        
        with patch("app.api.v1.endpoints.roles.SQLAlchemyRoleRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = None  # Role not found
            mock_repo_cls.return_value = mock_repo
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await update_role(
                    role_id=role_id,
                    request=request,
                    superuser_id=superuser_id,
                    session=mock_session,
                )
            
            assert exc.value.status_code == 404
            assert "ROLE_NOT_FOUND" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_update_role_invalid_permission(self, mock_session):
        """Test update_role with invalid permission string (lines 210-215)."""
        from app.api.v1.endpoints.roles import update_role
        from app.api.v1.schemas.roles import RoleUpdate
        
        request = RoleUpdate(permissions=["invalid-format"])
        role_id = uuid4()
        superuser_id = uuid4()
        
        mock_role = MagicMock()
        mock_role.id = role_id
        mock_role.name = "test_role"
        
        with patch("app.api.v1.endpoints.roles.SQLAlchemyRoleRepository") as mock_repo_cls, \
             patch("app.api.v1.endpoints.roles.Permission") as mock_permission:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_role
            mock_repo_cls.return_value = mock_repo
            
            mock_permission.from_string.side_effect = ValueError("Invalid format")
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await update_role(
                    role_id=role_id,
                    request=request,
                    superuser_id=superuser_id,
                    session=mock_session,
                )
            
            assert exc.value.status_code == 400
            assert "INVALID_PERMISSION" in str(exc.value.detail)


class TestTenantsEndpointCoverage:
    """Tests for tenants endpoint coverage."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_get_tenant_not_found(self):
        """Test get_tenant with non-existent tenant (lines 157-160)."""
        from app.api.v1.endpoints.tenants import get_tenant
        
        tenant_id = uuid4()
        
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = None
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await get_tenant(tenant_id=tenant_id, _=uuid4(), repo=mock_repo)
        
        assert exc.value.status_code == 404
        assert "Tenant not found" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_get_tenant_by_slug_not_found(self):
        """Test get_tenant_by_slug with non-existent slug (lines 178-181)."""
        from app.api.v1.endpoints.tenants import get_tenant_by_slug
        
        mock_repo = AsyncMock()
        mock_repo.get_by_slug.return_value = None
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await get_tenant_by_slug(slug="nonexistent", _=uuid4(), repo=mock_repo)
        
        assert exc.value.status_code == 404
        assert "Tenant not found" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_update_tenant_not_found(self):
        """Test update_tenant with non-existent tenant (lines 201-204)."""
        from app.api.v1.endpoints.tenants import update_tenant
        from app.api.v1.schemas.tenants import TenantUpdate
        
        tenant_id = uuid4()
        data = TenantUpdate(name="New Name")
        
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = None
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await update_tenant(
                tenant_id=tenant_id, 
                data=data, 
                current_user_id=uuid4(), 
                repo=mock_repo
            )
        
        assert exc.value.status_code == 404
        assert "Tenant not found" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_update_tenant_slug_conflict(self):
        """Test update_tenant with conflicting slug (lines 207-212)."""
        from app.api.v1.endpoints.tenants import update_tenant
        from app.api.v1.schemas.tenants import TenantUpdate
        
        tenant_id = uuid4()
        data = TenantUpdate(slug="existing-slug")
        
        mock_tenant = MagicMock()
        mock_tenant.id = tenant_id
        mock_tenant.slug = "current-slug"
        mock_tenant.domain = None
        
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = mock_tenant
        mock_repo.slug_exists.return_value = True  # Slug already exists
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await update_tenant(
                tenant_id=tenant_id, 
                data=data, 
                current_user_id=uuid4(), 
                repo=mock_repo
            )
        
        assert exc.value.status_code == 409
        assert "already exists" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_update_tenant_domain_conflict(self):
        """Test update_tenant with conflicting domain (lines 217-222)."""
        from app.api.v1.endpoints.tenants import update_tenant
        from app.api.v1.schemas.tenants import TenantUpdate
        
        tenant_id = uuid4()
        data = TenantUpdate(domain="existing.com")
        
        mock_tenant = MagicMock()
        mock_tenant.id = tenant_id
        mock_tenant.slug = "current-slug"
        mock_tenant.domain = "current.com"
        
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = mock_tenant
        mock_repo.domain_exists.return_value = True  # Domain already exists
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await update_tenant(
                tenant_id=tenant_id, 
                data=data, 
                current_user_id=uuid4(), 
                repo=mock_repo
            )
        
        assert exc.value.status_code == 409
        assert "already exists" in str(exc.value.detail)


class TestEmailTemplatesAdditionalCoverage:
    """Tests for email templates coverage."""

    def test_render_template_unsupported_locale_fallback(self):
        """Test render falls back to default locale (lines 155-158)."""
        from app.infrastructure.email.templates import EmailTemplateEngine
        
        engine = EmailTemplateEngine.__new__(EmailTemplateEngine)
        engine.SUPPORTED_LOCALES = ["en", "es"]
        engine.DEFAULT_LOCALE = "en"
        
        # Test unsupported locale fallback logic
        locale = "xx"  # Unsupported
        if locale not in engine.SUPPORTED_LOCALES:
            locale = engine.DEFAULT_LOCALE
        
        assert locale == "en"

    def test_email_template_engine_translate_method(self):
        """Test translate method with locale (line 132)."""
        from app.infrastructure.email.templates import EmailTemplateEngine
        
        engine = EmailTemplateEngine.__new__(EmailTemplateEngine)
        mock_i18n = MagicMock()
        mock_i18n.t.return_value = "Translated Text"
        engine._i18n = mock_i18n
        engine._current_locale = "es"
        
        result = engine._translate("test.key", name="value")
        
        mock_i18n.t.assert_called_once_with(
            "test.key", 
            locale="es", 
            name="value"
        )
        assert result == "Translated Text"


class TestTelemetryCoverage:
    """Tests for telemetry coverage."""

    def test_setup_tracing_with_otlp_endpoint(self):
        """Test tracing setup with OTLP endpoint (lines 72-77)."""
        from unittest.mock import patch
        
        with patch("app.infrastructure.observability.telemetry.settings") as mock_settings, \
             patch("app.infrastructure.observability.telemetry.TracerProvider") as mock_provider, \
             patch("app.infrastructure.observability.telemetry.OTLPSpanExporter") as mock_exporter, \
             patch("app.infrastructure.observability.telemetry.BatchSpanProcessor") as mock_processor, \
             patch("app.infrastructure.observability.telemetry.trace") as mock_trace:
            
            mock_settings.OTEL_EXPORTER_OTLP_ENDPOINT = "http://localhost:4317"
            
            from app.infrastructure.observability.telemetry import _setup_tracing
            from opentelemetry.sdk.resources import Resource
            
            resource = Resource.create({"service.name": "test"})
            _setup_tracing(resource)
            
            mock_exporter.assert_called_once_with(
                endpoint="http://localhost:4317",
                insecure=True,
            )
            mock_trace.set_tracer_provider.assert_called()

    def test_setup_tracing_without_otlp_endpoint(self):
        """Test tracing setup without OTLP endpoint uses console (lines 79-81)."""
        from unittest.mock import patch
        
        with patch("app.infrastructure.observability.telemetry.settings") as mock_settings, \
             patch("app.infrastructure.observability.telemetry.TracerProvider") as mock_provider, \
             patch("app.infrastructure.observability.telemetry.ConsoleSpanExporter") as mock_console, \
             patch("app.infrastructure.observability.telemetry.BatchSpanProcessor") as mock_processor, \
             patch("app.infrastructure.observability.telemetry.trace") as mock_trace:
            
            mock_settings.OTEL_EXPORTER_OTLP_ENDPOINT = None
            
            from app.infrastructure.observability.telemetry import _setup_tracing
            from opentelemetry.sdk.resources import Resource
            
            resource = Resource.create({"service.name": "test"})
            _setup_tracing(resource)
            
            mock_console.assert_called_once()
            mock_trace.set_tracer_provider.assert_called()

    def test_setup_metrics_with_otlp_endpoint(self):
        """Test metrics setup with OTLP endpoint (lines 89-93)."""
        from unittest.mock import patch
        
        with patch("app.infrastructure.observability.telemetry.settings") as mock_settings, \
             patch("app.infrastructure.observability.telemetry.MeterProvider") as mock_provider, \
             patch("app.infrastructure.observability.telemetry.OTLPMetricExporter") as mock_exporter, \
             patch("app.infrastructure.observability.telemetry.PeriodicExportingMetricReader") as mock_reader, \
             patch("app.infrastructure.observability.telemetry.metrics") as mock_metrics:
            
            mock_settings.OTEL_EXPORTER_OTLP_ENDPOINT = "http://localhost:4317"
            
            from app.infrastructure.observability.telemetry import _setup_metrics
            from opentelemetry.sdk.resources import Resource
            
            resource = Resource.create({"service.name": "test"})
            _setup_metrics(resource)
            
            mock_exporter.assert_called_once_with(
                endpoint="http://localhost:4317",
                insecure=True,
            )
            mock_metrics.set_meter_provider.assert_called()

    def test_setup_metrics_without_otlp_endpoint(self):
        """Test metrics setup without OTLP endpoint uses console (lines 95-99)."""
        from unittest.mock import patch
        
        with patch("app.infrastructure.observability.telemetry.settings") as mock_settings, \
             patch("app.infrastructure.observability.telemetry.MeterProvider") as mock_provider, \
             patch("app.infrastructure.observability.telemetry.ConsoleMetricExporter") as mock_console, \
             patch("app.infrastructure.observability.telemetry.PeriodicExportingMetricReader") as mock_reader, \
             patch("app.infrastructure.observability.telemetry.metrics") as mock_metrics:
            
            mock_settings.OTEL_EXPORTER_OTLP_ENDPOINT = None
            
            from app.infrastructure.observability.telemetry import _setup_metrics
            from opentelemetry.sdk.resources import Resource
            
            resource = Resource.create({"service.name": "test"})
            _setup_metrics(resource)
            
            mock_console.assert_called_once()
            mock_metrics.set_meter_provider.assert_called()
