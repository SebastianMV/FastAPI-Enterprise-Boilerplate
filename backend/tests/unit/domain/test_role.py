# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for Role entity."""

import pytest
from uuid import uuid4

from app.domain.entities.role import Permission, Role


class TestPermission:
    """Tests for Permission value object."""
    
    def test_permission_creation(self):
        """Test creating a permission."""
        perm = Permission(resource="users", action="read")
        assert perm.resource == "users"
        assert perm.action == "read"
    
    def test_permission_string(self):
        """Test string representation."""
        perm = Permission(resource="users", action="read")
        assert str(perm) == "users:read"
    
    def test_permission_from_string(self):
        """Test creating permission from string."""
        perm = Permission.from_string("users:create")
        assert perm.resource == "users"
        assert perm.action == "create"
    
    def test_permission_from_string_invalid(self):
        """Test invalid permission string raises ValueError."""
        with pytest.raises(ValueError, match="Invalid permission format"):
            Permission.from_string("invalid-format")
        
        with pytest.raises(ValueError, match="Invalid permission format"):
            Permission.from_string("too:many:colons")
    
    def test_permission_equality_with_permission(self):
        """Test permission equality."""
        perm1 = Permission(resource="users", action="read")
        perm2 = Permission(resource="users", action="read")
        perm3 = Permission(resource="users", action="write")
        
        assert perm1 == perm2
        assert perm1 != perm3
    
    def test_permission_equality_with_string(self):
        """Test permission equality with string."""
        perm = Permission(resource="users", action="read")
        assert perm == "users:read"
        assert perm != "users:write"
    
    def test_permission_hash(self):
        """Test permissions can be used in sets."""
        perm1 = Permission(resource="users", action="read")
        perm2 = Permission(resource="users", action="read")
        perm3 = Permission(resource="users", action="write")
        
        perms = {perm1, perm2, perm3}
        assert len(perms) == 2  # perm1 and perm2 are the same


class TestRole:
    """Tests for Role entity."""
    
    def test_role_creation(self):
        """Test creating a role."""
        role = Role(
            id=uuid4(),
            tenant_id=uuid4(),
            name="admin",
            description="Administrator role",
        )
        assert role.name == "admin"
        assert role.description == "Administrator role"
        assert role.permissions == []
    
    def test_add_permission(self):
        """Test adding permission to role."""
        role = Role(id=uuid4(), tenant_id=uuid4(), name="test")
        perm = Permission(resource="users", action="read")
        
        role.add_permission(perm)
        
        assert len(role.permissions) == 1
        assert perm in role.permissions
    
    def test_add_permission_duplicate(self):
        """Test adding duplicate permission is ignored."""
        role = Role(id=uuid4(), tenant_id=uuid4(), name="test")
        perm = Permission(resource="users", action="read")
        
        role.add_permission(perm)
        role.add_permission(perm)
        
        assert len(role.permissions) == 1
    
    def test_remove_permission(self):
        """Test removing permission from role."""
        perm = Permission(resource="users", action="read")
        role = Role(
            id=uuid4(),
            tenant_id=uuid4(),
            name="test",
            permissions=[perm],
        )
        
        role.remove_permission(perm)
        
        assert len(role.permissions) == 0
    
    def test_has_permission(self):
        """Test checking if role has permission."""
        perm = Permission(resource="users", action="read")
        role = Role(
            id=uuid4(),
            tenant_id=uuid4(),
            name="test",
            permissions=[perm],
        )
        
        assert role.has_permission("users", "read") is True
        assert role.has_permission("users", "write") is False
    
    def test_has_permission_wildcard_action(self):
        """Test wildcard action permission."""
        perm = Permission(resource="users", action="*")
        role = Role(
            id=uuid4(),
            tenant_id=uuid4(),
            name="test",
            permissions=[perm],
        )
        
        assert role.has_permission("users", "read") is True
        assert role.has_permission("users", "write") is True
        assert role.has_permission("users", "delete") is True
        assert role.has_permission("roles", "read") is False
    
    def test_has_permission_wildcard_resource(self):
        """Test wildcard resource permission."""
        perm = Permission(resource="*", action="read")
        role = Role(
            id=uuid4(),
            tenant_id=uuid4(),
            name="test",
            permissions=[perm],
        )
        
        assert role.has_permission("users", "read") is True
        assert role.has_permission("roles", "read") is True
        assert role.has_permission("users", "write") is False
    
    def test_has_permission_full_wildcard(self):
        """Test full wildcard permission (superadmin)."""
        perm = Permission(resource="*", action="*")
        role = Role(
            id=uuid4(),
            tenant_id=uuid4(),
            name="superadmin",
            permissions=[perm],
        )
        
        assert role.has_permission("users", "read") is True
        assert role.has_permission("roles", "delete") is True
        assert role.has_permission("anything", "anything") is True
    
    def test_has_any_permission(self):
        """Test checking if role has any of given permissions."""
        perms = [
            Permission(resource="users", action="read"),
            Permission(resource="roles", action="read"),
        ]
        role = Role(
            id=uuid4(),
            tenant_id=uuid4(),
            name="test",
            permissions=perms,
        )
        
        assert role.has_any_permission([("users", "read"), ("settings", "read")]) is True
        assert role.has_any_permission([("settings", "read"), ("logs", "read")]) is False
    
    def test_has_all_permissions(self):
        """Test checking if role has all given permissions."""
        perms = [
            Permission(resource="users", action="read"),
            Permission(resource="roles", action="read"),
        ]
        role = Role(
            id=uuid4(),
            tenant_id=uuid4(),
            name="test",
            permissions=perms,
        )
        
        assert role.has_all_permissions([("users", "read"), ("roles", "read")]) is True
        assert role.has_all_permissions([("users", "read"), ("settings", "read")]) is False
    
    def test_permission_strings(self):
        """Test getting permissions as strings."""
        perms = [
            Permission(resource="users", action="read"),
            Permission(resource="roles", action="create"),
        ]
        role = Role(
            id=uuid4(),
            tenant_id=uuid4(),
            name="test",
            permissions=perms,
        )
        
        strings = role.permission_strings
        assert "users:read" in strings
        assert "roles:create" in strings

    def test_permission_equality_with_invalid_type(self):
        """Test permission equality returns False for invalid types."""
        perm = Permission(resource="users", action="read")
        
        # Comparing with non-Permission, non-string types returns False
        assert (perm == 123) is False
        assert (perm == None) is False
        assert (perm == ["users", "read"]) is False
        assert (perm == {"resource": "users"}) is False

    def test_permission_equality_with_invalid_string_format(self):
        """Test permission equality with malformed string returns False."""
        perm = Permission(resource="users", action="read")
        
        # String without colon doesn't match
        assert (perm == "users-read") is False
        # String with one colon but empty parts
        assert (perm == ":read") is False
        assert (perm == "users:") is False
