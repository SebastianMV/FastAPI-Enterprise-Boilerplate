# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for SQLAlchemy model __repr__ methods.

Covers the string representation methods for debugging.
"""

from unittest.mock import MagicMock
from uuid import uuid4


class TestAPIKeyModelRepr:
    """Tests for APIKeyModel.__repr__ (line 116)."""

    def test_repr_returns_formatted_string(self):
        """Test APIKeyModel repr method."""
        from app.infrastructure.database.models.api_key import APIKeyModel

        # Create a mock instance with required attributes
        model = MagicMock(spec=APIKeyModel)
        model.id = uuid4()
        model.name = "Test API Key"
        model.prefix = "test_"

        # Call the actual __repr__ method
        result = APIKeyModel.__repr__(model)

        assert "<APIKey(" in result
        assert "name='Test API Key'" in result
        assert "prefix='test_'" in result


class TestAuditLogModelRepr:
    """Tests for AuditLogModel.__repr__ (line 156)."""

    def test_repr_returns_formatted_string(self):
        """Test AuditLogModel repr method."""
        from app.infrastructure.database.models.audit_log import AuditLogModel

        model = MagicMock(spec=AuditLogModel)
        model.id = uuid4()
        model.action = "CREATE"
        model.resource_type = "user"
        model.resource_id = str(uuid4())

        result = AuditLogModel.__repr__(model)

        assert "<AuditLog(" in result
        assert "action=CREATE" in result
        assert "resource=user/" in result


class TestUserSessionModelRepr:
    """Tests for UserSessionModel.__repr__ (line 137)."""

    def test_repr_returns_formatted_string(self):
        """Test UserSessionModel repr method."""
        from app.infrastructure.database.models.session import UserSessionModel

        model = MagicMock(spec=UserSessionModel)
        model.id = uuid4()
        model.user_id = uuid4()
        model.device_name = "Chrome on Windows"

        result = UserSessionModel.__repr__(model)

        assert "<UserSession(" in result
        assert "device=Chrome on Windows" in result


class TestUserModelRepr:
    """Tests for UserModel.__repr__ (line 181)."""

    def test_repr_returns_formatted_string(self):
        """Test UserModel repr method."""
        from app.infrastructure.database.models.user import UserModel

        model = MagicMock(spec=UserModel)
        model.id = uuid4()
        model.email = "test@example.com"

        result = UserModel.__repr__(model)

        assert "<User(" in result
        assert "email=test@example.com" in result


class TestTenantModelRepr:
    """Tests for TenantModel.__repr__ (line 117)."""

    def test_repr_returns_formatted_string(self):
        """Test TenantModel repr method."""
        from app.infrastructure.database.models.tenant import TenantModel

        model = MagicMock(spec=TenantModel)
        model.id = uuid4()
        model.name = "Test Tenant"
        model.slug = "test-tenant"

        result = TenantModel.__repr__(model)

        assert "<Tenant(" in result or "TenantModel" in result
