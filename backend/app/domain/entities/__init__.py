# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Domain entities package."""

from app.domain.entities.api_key import APIKey
from app.domain.entities.audit_log import AuditAction, AuditLog, AuditResourceType
from app.domain.entities.base import (
    AuditableEntity,
    BaseEntity,
    SoftDeletableEntity,
    TenantEntity,
    TenantSoftDeletableEntity,
)
from app.domain.entities.mfa import MFAConfig
from app.domain.entities.notification import (
    Notification,
    NotificationChannel,
    NotificationPriority,
    NotificationType,
)
from app.domain.entities.oauth import (
    OAuthConnection,
    OAuthProvider,
    OAuthState,
    OAuthUserInfo,
    SSOConfiguration,
)
from app.domain.entities.role import Permission, Role
from app.domain.entities.session import UserSession
from app.domain.entities.tenant import Tenant, TenantSettings
from app.domain.entities.user import User

__all__ = [
    "APIKey",
    "AuditAction",
    "AuditLog",
    "AuditResourceType",
    "AuditableEntity",
    "BaseEntity",
    "MFAConfig",
    "Notification",
    "NotificationChannel",
    "NotificationPriority",
    "NotificationType",
    "OAuthConnection",
    "OAuthProvider",
    "OAuthState",
    "OAuthUserInfo",
    "Permission",
    "Role",
    "SSOConfiguration",
    "SoftDeletableEntity",
    "Tenant",
    "TenantEntity",
    "TenantSettings",
    "TenantSoftDeletableEntity",
    "User",
    "UserSession",
]
