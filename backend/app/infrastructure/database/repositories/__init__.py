# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Infrastructure database repositories package."""

from app.infrastructure.database.repositories.audit_log_repository import (
    SQLAlchemyAuditLogRepository,
)
from app.infrastructure.database.repositories.cached_role_repository import (
    CachedRoleRepository,
    get_cached_role_repository,
)
from app.infrastructure.database.repositories.cached_tenant_repository import (
    CachedTenantRepository,
    get_cached_tenant_repository,
)
from app.infrastructure.database.repositories.role_repository import (
    SQLAlchemyRoleRepository,
)
from app.infrastructure.database.repositories.tenant_repository import (
    SQLAlchemyTenantRepository,
)
from app.infrastructure.database.repositories.user_repository import (
    SQLAlchemyUserRepository,
)

__all__ = [
    # Base repositories
    "SQLAlchemyUserRepository",
    "SQLAlchemyRoleRepository",
    "SQLAlchemyTenantRepository",
    "SQLAlchemyAuditLogRepository",
    # Cached repositories
    "CachedRoleRepository",
    "CachedTenantRepository",
    "get_cached_role_repository",
    "get_cached_tenant_repository",
]
