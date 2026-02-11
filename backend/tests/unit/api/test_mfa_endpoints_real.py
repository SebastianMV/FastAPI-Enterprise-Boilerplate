# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Tests for MFA endpoints API."""

from __future__ import annotations

from uuid import uuid4


class TestMFAEndpointsStructure:
    """Tests for MFA endpoints structure."""

    def test_router_import(self) -> None:
        """Test router can be imported."""
        from app.api.v1.endpoints.mfa import router

        assert router is not None

    def test_router_is_api_router(self) -> None:
        """Test router is an APIRouter."""
        from fastapi import APIRouter

        from app.api.v1.endpoints.mfa import router

        assert isinstance(router, APIRouter)

    def test_get_mfa_config_function(self) -> None:
        """Test get_mfa_config can be imported."""
        from app.api.v1.endpoints.mfa import get_mfa_config

        assert get_mfa_config is not None
        assert callable(get_mfa_config)

    def test_save_mfa_config_function(self) -> None:
        """Test save_mfa_config can be imported."""
        from app.api.v1.endpoints.mfa import save_mfa_config

        assert save_mfa_config is not None
        assert callable(save_mfa_config)


class TestMFASchemas:
    """Tests for MFA API schemas."""

    def test_mfa_status_response_schema(self) -> None:
        """Test MFAStatusResponse schema."""
        from app.api.v1.schemas.mfa import MFAStatusResponse

        data = MFAStatusResponse(
            is_enabled=False,
            backup_codes_remaining=0,
            enabled_at=None,
            last_used_at=None,
        )
        assert data.is_enabled is False

    def test_mfa_setup_response_schema(self) -> None:
        """Test MFASetupResponse schema."""
        from app.api.v1.schemas.mfa import MFASetupResponse

        assert MFASetupResponse is not None

    def test_mfa_verify_request_schema(self) -> None:
        """Test MFAVerifyRequest schema."""
        from app.api.v1.schemas.mfa import MFAVerifyRequest

        data = MFAVerifyRequest(code="123456")
        assert data.code == "123456"

    def test_mfa_verify_response_schema(self) -> None:
        """Test MFAVerifyResponse schema."""
        from app.api.v1.schemas.mfa import MFAVerifyResponse

        assert MFAVerifyResponse is not None

    def test_mfa_enable_response_schema(self) -> None:
        """Test MFAEnableResponse schema."""
        from app.api.v1.schemas.mfa import MFAEnableResponse

        assert MFAEnableResponse is not None

    def test_mfa_disable_request_schema(self) -> None:
        """Test MFADisableRequest schema."""
        from app.api.v1.schemas.mfa import MFADisableRequest

        data = MFADisableRequest(code="123456", password="password123")
        assert data.code == "123456"

    def test_mfa_disable_response_schema(self) -> None:
        """Test MFADisableResponse schema."""
        from app.api.v1.schemas.mfa import MFADisableResponse

        assert MFADisableResponse is not None

    def test_mfa_backup_codes_response_schema(self) -> None:
        """Test MFABackupCodesResponse schema."""
        from app.api.v1.schemas.mfa import MFABackupCodesResponse

        assert MFABackupCodesResponse is not None


class TestMFARouterRoutes:
    """Tests for MFA router route registration."""

    def test_status_route_exists(self) -> None:
        """Test status route is registered."""
        from app.api.v1.endpoints.mfa import router

        routes = [getattr(r, "path", None) for r in router.routes]
        assert "/mfa/status" in routes

    def test_router_has_multiple_routes(self) -> None:
        """Test router has multiple routes."""
        from app.api.v1.endpoints.mfa import router

        assert len(router.routes) >= 2


class TestMFAConfigEntity:
    """Tests for MFAConfig entity."""

    def test_mfa_config_import(self) -> None:
        """Test MFAConfig can be imported."""
        from app.domain.entities.mfa import MFAConfig

        assert MFAConfig is not None

    def test_mfa_config_creation(self) -> None:
        """Test MFAConfig entity creation."""
        from app.domain.entities.mfa import MFAConfig

        user_id = uuid4()
        config = MFAConfig(
            user_id=user_id,
            secret="JBSWY3DPEHPK3PXP",
            is_enabled=False,
            backup_codes=["12345678", "23456789"],
        )
        assert config.user_id == user_id
        assert config.is_enabled is False

    def test_mfa_config_backup_codes(self) -> None:
        """Test MFAConfig backup codes."""
        from app.domain.entities.mfa import MFAConfig

        user_id = uuid4()
        codes = ["code1", "code2", "code3"]
        config = MFAConfig(user_id=user_id, secret="SECRET", backup_codes=codes)
        assert len(config.backup_codes) == 3


class TestMFAService:
    """Tests for MFA service."""

    def test_mfa_service_import(self) -> None:
        """Test MFAService can be imported."""
        from app.application.services.mfa_service import MFAService

        assert MFAService is not None

    def test_get_mfa_service_import(self) -> None:
        """Test get_mfa_service can be imported."""
        from app.application.services.mfa_service import get_mfa_service

        assert get_mfa_service is not None
        assert callable(get_mfa_service)
