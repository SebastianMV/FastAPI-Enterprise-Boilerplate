# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Entity configurations for data exchange.

This module registers all domain entities that support import/export/reports.
Each project should add their own entity configurations here.
"""

import re
from typing import Any
from uuid import UUID

from app.domain.ports.data_exchange import (
    EntityConfig,
    EntityRegistry,
    FieldConfig,
    FieldType,
)
from app.infrastructure.database.models.audit_log import AuditLogModel
from app.infrastructure.database.models.role import RoleModel
from app.infrastructure.database.models.tenant import TenantModel
from app.infrastructure.database.models.user import UserModel

# ============================================================================
# Validators
# ============================================================================


def validate_email(value: str) -> bool:
    """Validate email format."""
    if not value:
        return True
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return bool(re.match(pattern, value))


def validate_uuid(value: str) -> bool:
    """Validate UUID format."""
    if not value:
        return True
    try:
        UUID(value)
        return True
    except (ValueError, AttributeError):
        return False


def validate_boolean(value: Any) -> bool:
    """Validate and normalize boolean value."""
    valid_values = {
        "true",
        "false",
        "1",
        "0",
        "yes",
        "no",
        "si",
        "sí",
        True,
        False,
    }
    if isinstance(value, str):
        value = value.lower()
    return value in valid_values


# ============================================================================
# Transformers
# ============================================================================


def transform_email(value: str) -> str:
    """Transform email to lowercase."""
    return value.strip().lower() if value else ""


def transform_boolean(value: Any) -> bool:
    """Transform string to boolean."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        return value.lower() in {"true", "1", "yes", "si", "sí"}
    return False


def transform_uuid(value: str) -> str:
    """Transform and validate UUID."""
    if not value:
        return ""
    return str(UUID(value))


# ============================================================================
# User Entity Configuration
# ============================================================================

USER_FIELDS = [
    FieldConfig(
        name="id",
        display_name="ID",
        field_type=FieldType.UUID,
        required=False,
        exportable=True,
        importable=False,  # Auto-generated
    ),
    FieldConfig(
        name="email",
        display_name="Email",
        field_type=FieldType.EMAIL,
        required=True,
        exportable=True,
        importable=True,
        validator=validate_email,
        transformer=transform_email,
    ),
    FieldConfig(
        name="first_name",
        display_name="First Name",
        field_type=FieldType.STRING,
        required=True,
        exportable=True,
        importable=True,
    ),
    FieldConfig(
        name="last_name",
        display_name="Last Name",
        field_type=FieldType.STRING,
        required=True,
        exportable=True,
        importable=True,
    ),
    FieldConfig(
        name="is_active",
        display_name="Is Active",
        field_type=FieldType.BOOLEAN,
        required=False,
        exportable=True,
        importable=False,  # SECURITY: must not be set via bulk import (use admin UI)
        validator=validate_boolean,
        transformer=transform_boolean,
        default=True,
    ),
    FieldConfig(
        name="is_superuser",
        display_name="Is Superuser",
        field_type=FieldType.BOOLEAN,
        required=False,
        exportable=True,
        importable=False,  # SECURITY: must never be set via bulk import
        validator=validate_boolean,
        transformer=transform_boolean,
        default=False,
    ),
    FieldConfig(
        name="email_verified",
        display_name="Email Verified",
        field_type=FieldType.BOOLEAN,
        required=False,
        exportable=True,
        importable=False,  # Should not be set manually
        default=False,
    ),
    FieldConfig(
        name="created_at",
        display_name="Created At",
        field_type=FieldType.DATETIME,
        required=False,
        exportable=True,
        importable=False,  # Auto-generated
    ),
    FieldConfig(
        name="updated_at",
        display_name="Updated At",
        field_type=FieldType.DATETIME,
        required=False,
        exportable=True,
        importable=False,  # Auto-generated
    ),
]

USER_CONFIG = EntityConfig(
    name="users",
    display_name="Users",
    model=UserModel,
    fields=USER_FIELDS,
    permission_resource="users",
    unique_fields=["email"],
)


# ============================================================================
# Tenant Entity Configuration
# ============================================================================

TENANT_FIELDS = [
    FieldConfig(
        name="id",
        display_name="ID",
        field_type=FieldType.UUID,
        required=False,
        exportable=True,
        importable=False,
    ),
    FieldConfig(
        name="name",
        display_name="Name",
        field_type=FieldType.STRING,
        required=True,
        exportable=True,
        importable=True,
    ),
    FieldConfig(
        name="slug",
        display_name="Slug",
        field_type=FieldType.STRING,
        required=True,
        exportable=True,
        importable=True,
    ),
    FieldConfig(
        name="is_active",
        display_name="Is Active",
        field_type=FieldType.BOOLEAN,
        required=False,
        exportable=True,
        importable=True,
        validator=validate_boolean,
        transformer=transform_boolean,
        default=True,
    ),
    FieldConfig(
        name="email",
        display_name="Email",
        field_type=FieldType.EMAIL,
        required=False,
        exportable=True,
        importable=True,
        validator=validate_email,
        transformer=transform_email,
    ),
    FieldConfig(
        name="plan",
        display_name="Plan",
        field_type=FieldType.STRING,
        required=False,
        exportable=True,
        importable=True,
        default="free",
        choices=["free", "starter", "professional", "enterprise"],
    ),
    FieldConfig(
        name="created_at",
        display_name="Created At",
        field_type=FieldType.DATETIME,
        required=False,
        exportable=True,
        importable=False,
    ),
]

TENANT_CONFIG = EntityConfig(
    name="tenants",
    display_name="Tenants",
    model=TenantModel,
    fields=TENANT_FIELDS,
    permission_resource="tenants",
    unique_fields=["slug"],
)


# ============================================================================
# Audit Log Entity Configuration (Read-Only Export)
# ============================================================================

AUDIT_LOG_FIELDS = [
    FieldConfig(
        name="id",
        display_name="ID",
        field_type=FieldType.UUID,
        required=False,
        exportable=True,
        importable=False,
    ),
    FieldConfig(
        name="action",
        display_name="Action",
        field_type=FieldType.STRING,
        required=False,
        exportable=True,
        importable=False,
    ),
    FieldConfig(
        name="resource_type",
        display_name="Resource Type",
        field_type=FieldType.STRING,
        required=False,
        exportable=True,
        importable=False,
    ),
    FieldConfig(
        name="resource_id",
        display_name="Resource ID",
        field_type=FieldType.UUID,
        required=False,
        exportable=True,
        importable=False,
    ),
    FieldConfig(
        name="actor_id",
        display_name="Actor ID",
        field_type=FieldType.UUID,
        required=False,
        exportable=True,
        importable=False,
    ),
    FieldConfig(
        name="ip_address",
        display_name="IP Address",
        field_type=FieldType.STRING,
        required=False,
        exportable=True,
        importable=False,
    ),
    FieldConfig(
        name="timestamp",
        display_name="Timestamp",
        field_type=FieldType.DATETIME,
        required=False,
        exportable=True,
        importable=False,
    ),
]

AUDIT_LOG_CONFIG = EntityConfig(
    name="audit_logs",
    display_name="Audit Logs",
    model=AuditLogModel,
    fields=AUDIT_LOG_FIELDS,
    permission_resource="audit_logs",
    unique_fields=[],  # No unique constraint for logs
)


# ============================================================================
# Role Entity Configuration
# ============================================================================

ROLE_FIELDS = [
    FieldConfig(
        name="id",
        display_name="ID",
        field_type=FieldType.UUID,
        required=False,
        exportable=True,
        importable=False,
    ),
    FieldConfig(
        name="name",
        display_name="Name",
        field_type=FieldType.STRING,
        required=True,
        exportable=True,
        importable=True,
    ),
    FieldConfig(
        name="description",
        display_name="Description",
        field_type=FieldType.STRING,
        required=False,
        exportable=True,
        importable=True,
    ),
    FieldConfig(
        name="is_system_role",
        display_name="Is System Role",
        field_type=FieldType.BOOLEAN,
        required=False,
        exportable=True,
        importable=False,  # System roles should not be imported
        default=False,
    ),
    FieldConfig(
        name="created_at",
        display_name="Created At",
        field_type=FieldType.DATETIME,
        required=False,
        exportable=True,
        importable=False,
    ),
]

ROLE_CONFIG = EntityConfig(
    name="roles",
    display_name="Roles",
    model=RoleModel,
    fields=ROLE_FIELDS,
    permission_resource="roles",
    unique_fields=["name"],
)


# ============================================================================
# Register All Entities
# ============================================================================


def register_entities() -> None:
    """
    Register all entity configurations.

    Call this function at application startup to make entities
    available for import/export/reports.
    """
    EntityRegistry.register(USER_CONFIG)
    EntityRegistry.register(TENANT_CONFIG)
    EntityRegistry.register(AUDIT_LOG_CONFIG)
    EntityRegistry.register(ROLE_CONFIG)


def register_entity(config: EntityConfig) -> None:
    """
    Register a custom entity configuration.

    Use this to add project-specific entities.

    Example:
        >>> from app.infrastructure.data_exchange.entities import register_entity
        >>> register_entity(EntityConfig(
        ...     name="condominiums",
        ...     display_name="Condominiums",
        ...     model=CondominiumModel,
        ...     fields=[...],
        ...     permission_resource="condominiums",
        ... ))
    """
    EntityRegistry.register(config)


# Auto-register built-in entities on module import
register_entities()
