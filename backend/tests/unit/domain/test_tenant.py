# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for Tenant entity."""

import pytest
from datetime import datetime, timedelta, UTC
from uuid import uuid4

from app.domain.entities.tenant import Tenant, TenantSettings


class TestTenantSettings:
    """Tests for TenantSettings dataclass."""
    
    def test_default_settings(self):
        """Test default settings values."""
        settings = TenantSettings()
        
        assert settings.enable_2fa is False
        assert settings.enable_api_keys is True
        assert settings.max_users == 100
        assert settings.password_min_length == 8
    
    def test_to_dict(self):
        """Test converting settings to dict."""
        settings = TenantSettings(
            enable_2fa=True,
            max_users=50,
            primary_color="#FF0000",
        )
        
        data = settings.to_dict()
        
        assert data["enable_2fa"] is True
        assert data["max_users"] == 50
        assert data["primary_color"] == "#FF0000"
    
    def test_from_dict(self):
        """Test creating settings from dict."""
        data = {
            "enable_2fa": True,
            "max_users": 50,
            "primary_color": "#FF0000",
        }
        
        settings = TenantSettings.from_dict(data)
        
        assert settings.enable_2fa is True
        assert settings.max_users == 50
        assert settings.primary_color == "#FF0000"
    
    def test_from_dict_with_defaults(self):
        """Test creating settings from partial dict uses defaults."""
        data = {"enable_2fa": True}
        
        settings = TenantSettings.from_dict(data)
        
        assert settings.enable_2fa is True
        assert settings.max_users == 100  # Default
        assert settings.password_min_length == 8  # Default


class TestTenant:
    """Tests for Tenant entity."""
    
    def test_tenant_creation(self):
        """Test creating a tenant."""
        tenant = Tenant(
            id=uuid4(),
            name="Acme Corp",
            slug="acme-corp",
            email="admin@acme.com",
        )
        
        assert tenant.name == "Acme Corp"
        assert tenant.slug == "acme-corp"
        assert tenant.is_active is True
        assert tenant.is_verified is False
        assert tenant.plan == "free"
    
    def test_activate_deactivate(self):
        """Test activate and deactivate methods."""
        tenant = Tenant(id=uuid4(), name="Test", slug="test")
        
        tenant.deactivate()
        assert tenant.is_active is False
        
        tenant.activate()
        assert tenant.is_active is True
    
    def test_verify(self):
        """Test verify method."""
        tenant = Tenant(id=uuid4(), name="Test", slug="test")
        
        assert tenant.is_verified is False
        
        tenant.verify()
        assert tenant.is_verified is True
    
    def test_update_plan(self):
        """Test updating subscription plan."""
        tenant = Tenant(id=uuid4(), name="Test", slug="test")
        expires = datetime.now(UTC) + timedelta(days=30)
        
        tenant.update_plan("professional", expires)
        
        assert tenant.plan == "professional"
        assert tenant.plan_expires_at == expires
    
    def test_update_plan_invalid(self):
        """Test updating with invalid plan raises error."""
        tenant = Tenant(id=uuid4(), name="Test", slug="test")
        
        with pytest.raises(ValueError, match="Invalid plan"):
            tenant.update_plan("invalid_plan")
    
    def test_is_plan_expired_no_expiry(self):
        """Test plan with no expiry is not expired."""
        tenant = Tenant(id=uuid4(), name="Test", slug="test")
        
        assert tenant.is_plan_expired() is False
    
    def test_is_plan_expired_future(self):
        """Test plan with future expiry is not expired."""
        tenant = Tenant(
            id=uuid4(),
            name="Test",
            slug="test",
            plan_expires_at=datetime.now(UTC) + timedelta(days=30),
        )
        
        assert tenant.is_plan_expired() is False
    
    def test_is_plan_expired_past(self):
        """Test plan with past expiry is expired."""
        tenant = Tenant(
            id=uuid4(),
            name="Test",
            slug="test",
            plan_expires_at=datetime.now(UTC) - timedelta(days=1),
        )
        
        assert tenant.is_plan_expired() is True
    
    def test_can_add_users(self):
        """Test can_add_users based on plan limits."""
        tenant = Tenant(
            id=uuid4(),
            name="Test",
            slug="test",
            settings=TenantSettings(max_users=10),
        )
        
        assert tenant.can_add_users(5) is True
        assert tenant.can_add_users(10) is False
        assert tenant.can_add_users(15) is False
    
    def test_update_settings(self):
        """Test updating tenant settings."""
        tenant = Tenant(id=uuid4(), name="Test", slug="test")
        
        tenant.update_settings(
            enable_2fa=True,
            max_users=200,
            primary_color="#00FF00",
        )
        
        assert tenant.settings.enable_2fa is True
        assert tenant.settings.max_users == 200
        assert tenant.settings.primary_color == "#00FF00"
    
    def test_update_settings_invalid_key_ignored(self):
        """Test invalid settings keys are ignored."""
        tenant = Tenant(id=uuid4(), name="Test", slug="test")
        
        # Should not raise
        tenant.update_settings(
            invalid_key="value",
            max_users=50,
        )
        
        assert tenant.settings.max_users == 50
