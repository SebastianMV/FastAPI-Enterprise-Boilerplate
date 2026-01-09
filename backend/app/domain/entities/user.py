# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""User domain entity."""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from uuid import UUID

from app.domain.entities.base import SoftDeletableEntity
from app.domain.value_objects.email import Email
from app.domain.value_objects.password import Password


@dataclass
class User(SoftDeletableEntity):
    """
    User domain entity.
    
    Represents a user in the system with authentication
    and authorization capabilities.
    """
    
    email: Email = field(default_factory=lambda: Email("user@example.com"))
    password_hash: str = ""
    first_name: str = ""
    last_name: str = ""
    is_active: bool = True
    is_superuser: bool = False
    last_login: datetime | None = None
    roles: list[UUID] = field(default_factory=list)
    
    @property
    def full_name(self) -> str:
        """Get user's full name."""
        return f"{self.first_name} {self.last_name}".strip()
    
    def set_password(self, password: Password, hasher: callable) -> None:
        """
        Set user password using provided hasher.
        
        Args:
            password: Validated password value object
            hasher: Function to hash the password
        """
        self.password_hash = hasher(password.value)
    
    def verify_password(self, plain_password: str, verifier: callable) -> bool:
        """
        Verify password against stored hash.
        
        Args:
            plain_password: Plain text password to verify
            verifier: Function to verify password
            
        Returns:
            True if password matches, False otherwise
        """
        return verifier(plain_password, self.password_hash)
    
    def record_login(self) -> None:
        """Record successful login timestamp."""
        self.last_login = datetime.now(UTC)
    
    def activate(self) -> None:
        """Activate user account."""
        self.is_active = True
    
    def deactivate(self) -> None:
        """Deactivate user account."""
        self.is_active = False
    
    def add_role(self, role_id: UUID) -> None:
        """Add role to user if not already assigned."""
        if role_id not in self.roles:
            self.roles.append(role_id)
    
    def remove_role(self, role_id: UUID) -> None:
        """Remove role from user."""
        if role_id in self.roles:
            self.roles.remove(role_id)
    
    def has_role(self, role_id: UUID) -> bool:
        """Check if user has specific role."""
        return role_id in self.roles
