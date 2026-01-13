# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Database models package."""

from app.infrastructure.database.models.api_key import APIKeyModel
from app.infrastructure.database.models.audit_log import AuditLogModel
# from app.infrastructure.database.models.chat_message import ChatMessageModel
# from app.infrastructure.database.models.conversation import ConversationModel, ConversationParticipantModel
from app.infrastructure.database.models.mfa import MFAConfigModel
from app.infrastructure.database.models.notification import NotificationModel
from app.infrastructure.database.models.oauth import OAuthConnectionModel, SSOConfigurationModel
from app.infrastructure.database.models.role import RoleModel
from app.infrastructure.database.models.session import UserSessionModel
from app.infrastructure.database.models.tenant import TenantModel
from app.infrastructure.database.models.user import UserModel

__all__ = [
    "APIKeyModel",
    "AuditLogModel",
    # "ChatMessageModel",
    # "ConversationModel",
    # "ConversationParticipantModel",
    "MFAConfigModel",
    "NotificationModel",
    "OAuthConnectionModel",
    "RoleModel",
    "SSOConfigurationModel",
    "TenantModel",
    "UserModel",
    "UserSessionModel",
]
