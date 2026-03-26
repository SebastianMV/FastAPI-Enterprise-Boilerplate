# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Domain ports (interfaces) package."""

from app.domain.ports.api_key_repository import APIKeyRepositoryPort
from app.domain.ports.audit_log_repository import AuditLogRepository
from app.domain.ports.notification_repository import NotificationRepositoryPort
from app.domain.ports.oauth_repository import OAuthRepositoryPort
from app.domain.ports.role_repository import RoleRepositoryPort
from app.domain.ports.session_repository import SessionRepositoryPort
from app.domain.ports.storage import StoragePort
from app.domain.ports.tenant_repository import TenantRepositoryPort
from app.domain.ports.user_repository import UserRepositoryPort
from app.domain.ports.websocket import WebSocketPort

__all__ = [
    "APIKeyRepositoryPort",
    "AuditLogRepository",
    "NotificationRepositoryPort",
    "OAuthRepositoryPort",
    "RoleRepositoryPort",
    "SessionRepositoryPort",
    "StoragePort",
    "TenantRepositoryPort",
    "UserRepositoryPort",
    "WebSocketPort",
]
