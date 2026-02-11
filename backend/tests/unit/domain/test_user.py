# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for User entity."""

from datetime import datetime
from uuid import uuid4

from app.domain.entities.user import User
from app.domain.value_objects.email import Email


class TestUser:
    """Tests for User entity."""

    def test_user_creation(self):
        """Test creating a user."""
        user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email=Email("test@example.com"),
            password_hash="hashed_password",
            first_name="John",
            last_name="Doe",
        )

        assert str(user.email) == "test@example.com"
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.is_active is True
        assert user.is_superuser is False

    def test_full_name(self):
        """Test full_name property."""
        user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            first_name="John",
            last_name="Doe",
        )

        assert user.full_name == "John Doe"

    def test_full_name_empty(self):
        """Test full_name with empty names."""
        user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            first_name="",
            last_name="",
        )

        assert user.full_name == ""

    def test_record_login(self):
        """Test recording login timestamp."""
        user = User(id=uuid4(), tenant_id=uuid4())
        assert user.last_login is None

        user.record_login()

        assert user.last_login is not None
        assert isinstance(user.last_login, datetime)

    def test_activate_deactivate(self):
        """Test activate and deactivate methods."""
        user = User(id=uuid4(), tenant_id=uuid4(), is_active=True)

        user.deactivate()
        assert user.is_active is False

        user.activate()
        assert user.is_active is True

    def test_add_role(self):
        """Test adding role to user."""
        user = User(id=uuid4(), tenant_id=uuid4())
        role_id = uuid4()

        user.add_role(role_id)

        assert role_id in user.roles
        assert len(user.roles) == 1

    def test_add_role_duplicate(self):
        """Test adding duplicate role is ignored."""
        user = User(id=uuid4(), tenant_id=uuid4())
        role_id = uuid4()

        user.add_role(role_id)
        user.add_role(role_id)

        assert len(user.roles) == 1

    def test_remove_role(self):
        """Test removing role from user."""
        role_id = uuid4()
        user = User(id=uuid4(), tenant_id=uuid4(), roles=[role_id])

        user.remove_role(role_id)

        assert role_id not in user.roles
        assert len(user.roles) == 0

    def test_remove_role_not_present(self):
        """Test removing non-existent role is ignored."""
        user = User(id=uuid4(), tenant_id=uuid4())
        role_id = uuid4()

        # Should not raise
        user.remove_role(role_id)

        assert len(user.roles) == 0

    def test_has_role(self):
        """Test checking if user has role."""
        role_id = uuid4()
        user = User(id=uuid4(), tenant_id=uuid4(), roles=[role_id])

        assert user.has_role(role_id) is True
        assert user.has_role(uuid4()) is False
