# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Bulk Operations API endpoints.

Provides efficient batch operations for users, roles, and tenants.
Supports bulk create, update, delete with validation and error handling.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentTenantId, DbSession, SuperuserId
from app.api.v1.schemas.common import NameStr, PasswordStr
from app.domain.entities.audit_log import AuditAction, AuditLog, AuditResourceType
from app.domain.entities.user import User
from app.domain.exceptions.base import ValidationError as DomainValidationError
from app.domain.value_objects.email import Email
from app.domain.value_objects.password import Password
from app.infrastructure.auth.jwt_handler import hash_password
from app.infrastructure.database.repositories import (
    SQLAlchemyAuditLogRepository,
    SQLAlchemyRoleRepository,
    SQLAlchemyUserRepository,
)
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/bulk", tags=["Bulk Operations"])


# ====================
# Enums
# ====================


class BulkOperationType(str, Enum):
    """Types of bulk operations."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    ACTIVATE = "activate"
    DEACTIVATE = "deactivate"
    ASSIGN_ROLE = "assign_role"
    REMOVE_ROLE = "remove_role"


class BulkEntityType(str, Enum):
    """Entity types for bulk operations."""

    USERS = "users"
    ROLES = "roles"


# ====================
# Request Schemas
# ====================


class BulkUserCreate(BaseModel):
    """Single user for bulk creation."""

    email: EmailStr
    password: PasswordStr
    first_name: NameStr
    last_name: NameStr
    is_active: bool = True
    roles: list[UUID] = Field(default_factory=list)


class BulkUserUpdate(BaseModel):
    """Single user update for bulk operations."""

    id: UUID
    first_name: NameStr | None = None
    last_name: NameStr | None = None
    is_active: bool | None = None
    roles: list[UUID] | None = None


class BulkUserDelete(BaseModel):
    """Request to delete multiple users."""

    user_ids: list[UUID] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of user IDs to delete (max 100)",
    )
    hard_delete: bool = Field(
        default=False,
        description="If true, permanently delete. Otherwise soft-delete.",
    )


class BulkUserStatusUpdate(BaseModel):
    """Request to update status of multiple users."""

    user_ids: list[UUID] = Field(
        ...,
        min_length=1,
        max_length=100,
    )
    is_active: bool


class BulkRoleAssignment(BaseModel):
    """Request to assign/remove roles for multiple users."""

    user_ids: list[UUID] = Field(
        ...,
        min_length=1,
        max_length=100,
    )
    role_ids: list[UUID] = Field(
        ...,
        min_length=1,
        max_length=10,
    )
    operation: Literal["assign", "remove"] = Field(
        ...,
        description="'assign' to add roles, 'remove' to remove roles",
    )


class BulkUsersCreateRequest(BaseModel):
    """Request to create multiple users."""

    users: list[BulkUserCreate] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of users to create (max 100)",
    )
    skip_duplicates: bool = Field(
        default=True,
        description="Skip users with existing emails instead of failing",
    )
    send_welcome_email: bool = Field(
        default=False,
        description="Send welcome email to created users",
    )


class BulkUsersUpdateRequest(BaseModel):
    """Request to update multiple users."""

    users: list[BulkUserUpdate] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of user updates (max 100)",
    )
    skip_not_found: bool = Field(
        default=True,
        description="Skip users that don't exist instead of failing",
    )


# ====================
# Response Schemas
# ====================


class BulkOperationItemResult(BaseModel):
    """Result for a single item in bulk operation."""

    id: UUID | str | None = None
    success: bool
    error: str | None = None
    message: str | None = None


class BulkOperationResult(BaseModel):
    """Result of a bulk operation."""

    operation: BulkOperationType
    entity_type: BulkEntityType
    total_requested: int
    successful: int
    failed: int
    skipped: int
    results: list[BulkOperationItemResult]
    started_at: datetime
    completed_at: datetime
    duration_ms: int


class BulkOperationSummary(BaseModel):
    """Summary for quick bulk operations."""

    operation: str = Field(max_length=50)
    total: int
    successful: int
    failed: int
    message: str = Field(max_length=500)


# ====================
# Helper Functions
# ====================


async def log_bulk_operation(
    session: AsyncSession,
    user_id: UUID,
    action: AuditAction,
    entity_type: str,
    details: dict[str, Any],
) -> None:
    """Log bulk operation to audit log."""
    audit_repo = SQLAlchemyAuditLogRepository(session)

    # Use correct AuditLog dataclass parameters

    # Map entity_type string to AuditResourceType
    resource_type_map = {
        "users": AuditResourceType.USER,
        "roles": AuditResourceType.ROLE,
        "tenants": AuditResourceType.TENANT,
    }
    resource_type = resource_type_map.get(entity_type, AuditResourceType.SYSTEM)

    log_entry = AuditLog(
        actor_id=user_id,
        action=action,
        resource_type=resource_type,
        metadata=details,
    )

    await audit_repo.create(log_entry)


# ====================
# User Bulk Endpoints
# ====================


@router.post(
    "/users/create",
    response_model=BulkOperationResult,
    status_code=status.HTTP_201_CREATED,
    summary="Bulk create users",
    description="Create multiple users in a single request. Max 100 users.",
)
async def bulk_create_users(
    request: BulkUsersCreateRequest,
    current_user_id: SuperuserId,
    tenant_id: CurrentTenantId,
    session: DbSession,
    background_tasks: BackgroundTasks,
) -> BulkOperationResult:
    """
    Create multiple users at once.

    - Validates all users before creation
    - Skips duplicates if skip_duplicates=true
    - Optionally sends welcome emails
    - Returns detailed results for each user
    """
    started_at = datetime.now(UTC)
    user_repo = SQLAlchemyUserRepository(session)

    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "TENANT_REQUIRED",
                "message": "Tenant context is required for bulk user creation",
            },
        )

    results: list[BulkOperationItemResult] = []
    successful = 0
    failed = 0
    skipped = 0

    for idx, user_data in enumerate(request.users):
        try:
            # Check if email already exists
            existing = await user_repo.get_by_email(user_data.email)
            if existing:
                if request.skip_duplicates:
                    results.append(
                        BulkOperationItemResult(
                            id=f"row-{idx}",
                            success=False,
                            error="duplicate",
                            message="A user with this email already exists",
                        )
                    )
                    skipped += 1
                    continue
                results.append(
                    BulkOperationItemResult(
                        id=f"row-{idx}",
                        success=False,
                        error="duplicate",
                        message="A user with this email already exists",
                    )
                )
                failed += 1
                continue

            # Create user

            # Validate password strength (same rules as single-user create)
            try:
                Password(user_data.password)
            except (ValueError, DomainValidationError):
                results.append(
                    BulkOperationItemResult(
                        id=f"row-{idx}",
                        success=False,
                        error="weak_password",
                        message="Password does not meet security requirements",
                    )
                )
                failed += 1
                continue

            # Validate role tenant ownership (B11 — prevent cross-tenant role assignment)
            validated_role_ids: list[UUID] = []
            if user_data.roles:
                from app.infrastructure.database.repositories.role_repository import (
                    SQLAlchemyRoleRepository,
                )

                role_repo = SQLAlchemyRoleRepository(session)
                role_validation_failed = False
                for role_id in user_data.roles:
                    role = await role_repo.get_by_id(role_id)
                    if not role or (
                        role.tenant_id and tenant_id and role.tenant_id != tenant_id
                    ):
                        results.append(
                            BulkOperationItemResult(
                                id=f"row-{idx}",
                                success=False,
                                error="role_not_found",
                                message="Role not found or not accessible",
                            )
                        )
                        failed += 1
                        role_validation_failed = True
                        break
                    validated_role_ids.append(role_id)
                if role_validation_failed:
                    continue

            new_user = User(
                email=Email(user_data.email),
                password_hash=hash_password(user_data.password),
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                is_active=user_data.is_active,
                roles=list(validated_role_ids) if user_data.roles else [],
                tenant_id=tenant_id,
            )

            created_user = await user_repo.create(new_user)

            results.append(
                BulkOperationItemResult(
                    id=created_user.id,
                    success=True,
                    message="User created successfully",
                )
            )
            successful += 1

        except Exception as e:
            logger.error("bulk_user_create_failed", row=idx, error=type(e).__name__)
            results.append(
                BulkOperationItemResult(
                    id=f"row-{idx}",
                    success=False,
                    error="creation_failed",
                    message="Failed to create user",
                )
            )
            failed += 1

    completed_at = datetime.now(UTC)
    duration_ms = int((completed_at - started_at).total_seconds() * 1000)

    # Log the bulk operation
    await log_bulk_operation(
        session,
        current_user_id,
        AuditAction.BULK_UPDATE,
        "users",
        {
            "operation": "bulk_create",
            "total_requested": len(request.users),
            "successful": successful,
            "failed": failed,
            "skipped": skipped,
        },
    )

    await session.commit()

    return BulkOperationResult(
        operation=BulkOperationType.CREATE,
        entity_type=BulkEntityType.USERS,
        total_requested=len(request.users),
        successful=successful,
        failed=failed,
        skipped=skipped,
        results=results,
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=duration_ms,
    )


@router.post(
    "/users/update",
    response_model=BulkOperationResult,
    summary="Bulk update users",
    description="Update multiple users in a single request.",
)
async def bulk_update_users(
    request: BulkUsersUpdateRequest,
    current_user_id: SuperuserId,
    tenant_id: CurrentTenantId,
    session: DbSession,
) -> BulkOperationResult:
    """
    Update multiple users at once.

    - Only updates provided fields
    - Skips not found users if skip_not_found=true
    - Returns detailed results for each user
    """
    started_at = datetime.now(UTC)
    user_repo = SQLAlchemyUserRepository(session)

    results: list[BulkOperationItemResult] = []
    successful = 0
    failed = 0
    skipped = 0

    for update_data in request.users:
        try:
            user = await user_repo.get_by_id(update_data.id)
            if not user:
                if request.skip_not_found:
                    results.append(
                        BulkOperationItemResult(
                            id=update_data.id,
                            success=False,
                            error="not_found",
                            message="User not found",
                        )
                    )
                    skipped += 1
                    continue
                results.append(
                    BulkOperationItemResult(
                        id=update_data.id,
                        success=False,
                        error="not_found",
                        message="User not found",
                    )
                )
                failed += 1
                continue

            # B-03: Verify user belongs to the same tenant
            if tenant_id and user.tenant_id and user.tenant_id != tenant_id:
                results.append(
                    BulkOperationItemResult(
                        id=update_data.id,
                        success=False,
                        error="not_found",
                        message="User not found",
                    )
                )
                skipped += 1
                continue

            # Apply updates
            if update_data.first_name is not None:
                user.first_name = update_data.first_name
            if update_data.last_name is not None:
                user.last_name = update_data.last_name
            if update_data.is_active is not None:
                user.is_active = update_data.is_active

            # Update roles if specified - validate tenant ownership (B31)
            if update_data.roles is not None:
                role_repo = SQLAlchemyRoleRepository(session)
                validated_role_ids: list[UUID] = []
                role_validation_failed = False
                for role_id in update_data.roles:
                    role = await role_repo.get_by_id(role_id)
                    if not role or (
                        role.tenant_id and tenant_id and role.tenant_id != tenant_id
                    ):
                        results.append(
                            BulkOperationItemResult(
                                id=update_data.id,
                                success=False,
                                error="role_not_found",
                                message="Role not found or not accessible",
                            )
                        )
                        failed += 1
                        role_validation_failed = True
                        break
                    validated_role_ids.append(role_id)
                if role_validation_failed:
                    continue
                user.roles = list(validated_role_ids)

            await user_repo.update(user)

            results.append(
                BulkOperationItemResult(
                    id=update_data.id,
                    success=True,
                    message="User updated successfully",
                )
            )
            successful += 1

        except Exception as e:
            logger.error(
                "bulk_user_update_failed",
                user_id=str(update_data.id),
                error=type(e).__name__,
            )
            results.append(
                BulkOperationItemResult(
                    id=update_data.id,
                    success=False,
                    error="update_failed",
                    message="Failed to update user",
                )
            )
            failed += 1

    completed_at = datetime.now(UTC)
    duration_ms = int((completed_at - started_at).total_seconds() * 1000)

    await log_bulk_operation(
        session,
        current_user_id,
        AuditAction.BULK_UPDATE,
        "users",
        {
            "operation": "bulk_update",
            "total_requested": len(request.users),
            "successful": successful,
            "failed": failed,
            "skipped": skipped,
        },
    )

    await session.commit()

    return BulkOperationResult(
        operation=BulkOperationType.UPDATE,
        entity_type=BulkEntityType.USERS,
        total_requested=len(request.users),
        successful=successful,
        failed=failed,
        skipped=skipped,
        results=results,
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=duration_ms,
    )


@router.post(
    "/users/delete",
    response_model=BulkOperationResult,
    summary="Bulk delete users",
    description="Delete multiple users in a single request.",
)
async def bulk_delete_users(
    request: BulkUserDelete,
    current_user_id: SuperuserId,
    tenant_id: CurrentTenantId,
    session: DbSession,
) -> BulkOperationResult:
    """
    Delete multiple users at once.

    - Soft delete by default (sets is_active=false)
    - Hard delete permanently removes users
    - Cannot delete yourself or other superusers
    """
    started_at = datetime.now(UTC)
    user_repo = SQLAlchemyUserRepository(session)

    results: list[BulkOperationItemResult] = []
    successful = 0
    failed = 0
    skipped = 0

    for user_id in request.user_ids:
        try:
            # Prevent self-deletion
            if user_id == current_user_id:
                results.append(
                    BulkOperationItemResult(
                        id=user_id,
                        success=False,
                        error="self_deletion",
                        message="Cannot delete yourself",
                    )
                )
                skipped += 1
                continue

            user = await user_repo.get_by_id(user_id)
            if not user:
                results.append(
                    BulkOperationItemResult(
                        id=user_id,
                        success=False,
                        error="not_found",
                        message="User not found",
                    )
                )
                skipped += 1
                continue

            # B-03: Verify user belongs to the same tenant
            if tenant_id and user.tenant_id and user.tenant_id != tenant_id:
                results.append(
                    BulkOperationItemResult(
                        id=user_id,
                        success=False,
                        error="not_found",
                        message="User not found",
                    )
                )
                skipped += 1
                continue

            # Prevent deleting other superusers
            if user.is_superuser:
                results.append(
                    BulkOperationItemResult(
                        id=user_id,
                        success=False,
                        error="protected_user",
                        message="Cannot delete superuser accounts",
                    )
                )
                skipped += 1
                continue

            if request.hard_delete:
                await user_repo.delete(user_id)
            else:
                user.is_active = False
                await user_repo.update(user)

            # Revoke all sessions for deactivated/deleted user
            try:
                from app.infrastructure.database.repositories.session_repository import (
                    SQLAlchemySessionRepository,
                )

                session_repo = SQLAlchemySessionRepository(session)
                await session_repo.revoke_all(user_id)
            except Exception:
                logger.warning("bulk_session_revoke_failed", user_id=str(user_id))

            results.append(
                BulkOperationItemResult(
                    id=user_id,
                    success=True,
                    message="User deleted successfully"
                    if request.hard_delete
                    else "User deactivated",
                )
            )
            successful += 1

        except Exception as e:
            logger.error(
                "bulk_user_delete_failed", user_id=str(user_id), error=type(e).__name__
            )
            results.append(
                BulkOperationItemResult(
                    id=user_id,
                    success=False,
                    error="deletion_failed",
                    message="Failed to delete user",
                )
            )
            failed += 1

    completed_at = datetime.now(UTC)
    duration_ms = int((completed_at - started_at).total_seconds() * 1000)

    await log_bulk_operation(
        session,
        current_user_id,
        AuditAction.BULK_DELETE,
        "users",
        {
            "operation": "bulk_delete",
            "hard_delete": request.hard_delete,
            "total_requested": len(request.user_ids),
            "successful": successful,
            "failed": failed,
            "skipped": skipped,
        },
    )

    await session.commit()

    return BulkOperationResult(
        operation=BulkOperationType.DELETE,
        entity_type=BulkEntityType.USERS,
        total_requested=len(request.user_ids),
        successful=successful,
        failed=failed,
        skipped=skipped,
        results=results,
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=duration_ms,
    )


@router.post(
    "/users/status",
    response_model=BulkOperationSummary,
    summary="Bulk update user status",
    description="Activate or deactivate multiple users.",
)
async def bulk_update_user_status(
    request: BulkUserStatusUpdate,
    current_user_id: SuperuserId,
    tenant_id: CurrentTenantId,
    session: DbSession,
) -> BulkOperationSummary:
    """
    Activate or deactivate multiple users at once.

    - Quick operation for status changes
    - Cannot deactivate yourself
    """
    user_repo = SQLAlchemyUserRepository(session)

    successful = 0
    failed = 0

    for user_id in request.user_ids:
        try:
            if user_id == current_user_id and not request.is_active:
                failed += 1
                continue

            user = await user_repo.get_by_id(user_id)
            if not user:
                failed += 1
                continue

            # Verify tenant ownership
            if tenant_id and user.tenant_id and user.tenant_id != tenant_id:
                failed += 1
                continue

            user.is_active = request.is_active
            await user_repo.update(user)
            successful += 1

        except Exception:
            logger.warning("bulk_status_update_failed", user_id=str(user_id))
            failed += 1

    action = AuditAction.BULK_UPDATE
    await log_bulk_operation(
        session,
        current_user_id,
        action,
        "users",
        {
            "operation": "bulk_status_update",
            "is_active": request.is_active,
            "total": len(request.user_ids),
            "successful": successful,
        },
    )

    await session.commit()

    status_text = "activated" if request.is_active else "deactivated"

    return BulkOperationSummary(
        operation=f"bulk_{status_text}",
        total=len(request.user_ids),
        successful=successful,
        failed=failed,
        message=f"Successfully {status_text} {successful} of {len(request.user_ids)} users",
    )


@router.post(
    "/users/roles",
    response_model=BulkOperationSummary,
    summary="Bulk role assignment",
    description="Assign or remove roles for multiple users.",
)
async def bulk_role_assignment(
    request: BulkRoleAssignment,
    current_user_id: SuperuserId,
    tenant_id: CurrentTenantId,
    session: DbSession,
) -> BulkOperationSummary:
    """
    Assign or remove roles for multiple users.

    - operation="assign": Add roles to users
    - operation="remove": Remove roles from users
    """
    user_repo = SQLAlchemyUserRepository(session)
    role_repo = SQLAlchemyRoleRepository(session)

    # Validate roles exist and belong to the same tenant
    valid_role_ids = []
    for role_id in request.role_ids:
        role = await role_repo.get_by_id(role_id)
        if role and (
            not tenant_id or not role.tenant_id or role.tenant_id == tenant_id
        ):
            valid_role_ids.append(role_id)

    if not valid_role_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "NO_VALID_ROLES", "message": "No valid roles found"},
        )

    successful = 0
    failed = 0

    for user_id in request.user_ids:
        try:
            user = await user_repo.get_by_id(user_id)
            if not user:
                failed += 1
                continue

            # Verify tenant ownership
            if tenant_id and user.tenant_id and user.tenant_id != tenant_id:
                failed += 1
                continue

            # Manage roles directly on user.roles list
            current_roles = set(user.roles or [])

            for role_id in valid_role_ids:
                if request.operation == "assign":
                    current_roles.add(role_id)
                else:
                    current_roles.discard(role_id)

            user.roles = list(current_roles)
            await user_repo.update(user)

            successful += 1

        except Exception:
            logger.warning("bulk_role_assignment_failed", user_id=str(user_id))
            failed += 1

    await log_bulk_operation(
        session,
        current_user_id,
        AuditAction.BULK_UPDATE,
        "users",
        {
            "operation": f"bulk_role_{request.operation}",
            "role_ids": [str(r) for r in valid_role_ids],
            "total_users": len(request.user_ids),
            "successful": successful,
        },
    )

    await session.commit()

    action_text = "assigned to" if request.operation == "assign" else "removed from"

    return BulkOperationSummary(
        operation=f"bulk_role_{request.operation}",
        total=len(request.user_ids),
        successful=successful,
        failed=failed,
        message=f"Roles {action_text} {successful} of {len(request.user_ids)} users",
    )


# ====================
# Validation Endpoint
# ====================


class BulkValidationRequest(BaseModel):
    """Request to validate data before bulk operation."""

    entity_type: BulkEntityType
    operation: BulkOperationType
    data: list[dict[str, Any]] = Field(max_length=100)


class BulkValidationResult(BaseModel):
    """Result of bulk validation."""

    valid: bool
    total: int
    valid_count: int
    invalid_count: int
    errors: list[dict[str, Any]]


_BULK_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
_BULK_PASSWORD_RE = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]).{8,}$"
)


def _validate_email_format(email: str) -> bool:
    """Validate email format using a proper regex."""
    return bool(_BULK_EMAIL_RE.match(email))


def _validate_password_complexity(password: str) -> bool:
    """Validate password complexity (8+ chars, upper, lower, digit, special)."""
    return bool(len(password) >= 8 and _BULK_PASSWORD_RE.match(password))


@router.post(
    "/validate",
    response_model=BulkValidationResult,
    summary="Validate bulk operation data",
    description="Validate data before performing a bulk operation.",
)
async def validate_bulk_data(
    request: BulkValidationRequest,
    current_user_id: SuperuserId,
    tenant_id: CurrentTenantId,
    session: DbSession,
) -> BulkValidationResult:
    """
    Validate data before bulk operation.

    - Checks required fields
    - Validates email formats
    - Checks for duplicates
    - Returns detailed validation errors
    """
    errors: list[dict[str, Any]] = []
    valid_count = 0

    user_repo = SQLAlchemyUserRepository(session)

    for idx, item in enumerate(request.data):
        item_errors = []

        if request.entity_type == BulkEntityType.USERS:
            if request.operation == BulkOperationType.CREATE:
                # Validate user creation data
                if not item.get("email"):
                    item_errors.append("email is required")
                elif not isinstance(
                    item.get("email"), str
                ) or not _validate_email_format(item.get("email", "")):
                    item_errors.append("invalid email format")
                else:
                    # Check for duplicate
                    existing = await user_repo.get_by_email(item["email"])
                    if existing:
                        item_errors.append("a user with this email already exists")

                if not item.get("password"):
                    item_errors.append("password is required")
                elif not _validate_password_complexity(item.get("password", "")):
                    item_errors.append(
                        "password must be at least 8 characters with uppercase, lowercase, digit, and special character"
                    )

                if not item.get("first_name"):
                    item_errors.append("first_name is required")
                if not item.get("last_name"):
                    item_errors.append("last_name is required")

            elif request.operation in (
                BulkOperationType.UPDATE,
                BulkOperationType.DELETE,
            ):
                if not item.get("id"):
                    item_errors.append("id is required")

        if item_errors:
            errors.append(
                {
                    "index": idx,
                    "errors": item_errors,
                }
            )
        else:
            valid_count += 1

    return BulkValidationResult(
        valid=len(errors) == 0,
        total=len(request.data),
        valid_count=valid_count,
        invalid_count=len(errors),
        errors=errors,
    )
