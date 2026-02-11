# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Users CRUD endpoints."""

import uuid as uuid_module
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from app.api.deps import (
    CurrentTenantId,
    CurrentUserId,
    DbSession,
    SuperuserId,
    require_permission,
)
from app.api.v1.schemas.common import MessageResponse
from app.api.v1.schemas.users import (
    UserCreate,
    UserDetailResponse,
    UserListResponse,
    UserResponse,
    UserUpdate,
    UserUpdateSelf,
)
from app.application.use_cases.users.create_user import (
    CreateUserRequest,
    CreateUserUseCase,
)
from app.application.use_cases.users.delete_user import (
    DeleteUserRequest,
    DeleteUserUseCase,
)
from app.application.use_cases.users.get_user import GetUserRequest, GetUserUseCase
from app.application.use_cases.users.update_user import (
    UpdateUserRequest,
    UpdateUserUseCase,
)
from app.domain.exceptions.base import (
    ConflictError,
    EntityNotFoundError,
    ValidationError,
)
from app.infrastructure.database.repositories.user_repository import (
    SQLAlchemyUserRepository,
)
from app.infrastructure.observability.logging import get_logger
from app.infrastructure.storage import get_storage

router = APIRouter()

logger = get_logger(__name__)


@router.get(
    "",
    response_model=UserListResponse,
    summary="List users",
    description="List all users with pagination. Requires authentication.",
)
async def list_users(
    session: DbSession,
    current_user_id: UUID = Depends(require_permission("users", "read")),
    tenant_id: CurrentTenantId = None,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    is_active: bool | None = Query(default=None, description="Filter by active status"),
) -> UserListResponse:
    """
    List all users with pagination.

    - **page**: Page number (starts at 1)
    - **page_size**: Items per page (max 100)
    - **is_active**: Filter by active status
    """
    repo = SQLAlchemyUserRepository(session)

    skip = (page - 1) * page_size
    users = await repo.list(
        skip=skip, limit=page_size, is_active=is_active, tenant_id=tenant_id
    )
    total = await repo.count(is_active=is_active, tenant_id=tenant_id)

    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if page_size > 0 else 0,
    )


@router.get(
    "/{user_id}",
    response_model=UserDetailResponse,
    summary="Get user by ID",
    description="Get detailed user information by ID.",
)
async def get_user(
    user_id: UUID,
    session: DbSession,
    tenant_id: CurrentTenantId,
    current_user_id: UUID = Depends(require_permission("users", "read")),
) -> UserDetailResponse:
    """
    Get user by ID.

    Returns detailed user information including roles and tenant.
    """
    repo = SQLAlchemyUserRepository(session)
    use_case = GetUserUseCase(repo)

    try:
        result = await use_case.execute(GetUserRequest(user_id=user_id))
        # Tenant isolation: verify user belongs to current tenant
        if tenant_id and result.user.tenant_id and result.user.tenant_id != tenant_id:
            raise EntityNotFoundError(code="USER_NOT_FOUND", message="User not found")
        return UserDetailResponse.model_validate(result.user)
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "User not found"},
        ) from None


@router.post(
    "",
    response_model=UserDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
    description="Create a new user. Requires superuser privileges.",
)
async def create_user(
    request: UserCreate,
    superuser_id: SuperuserId,
    tenant_id: CurrentTenantId,
    session: DbSession,
) -> UserDetailResponse:
    """
    Create a new user (admin only).

    Password requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    """
    repo = SQLAlchemyUserRepository(session)
    use_case = CreateUserUseCase(repo)

    try:
        result = await use_case.execute(
            CreateUserRequest(
                email=request.email,
                password=request.password,
                first_name=request.first_name,
                last_name=request.last_name,
                tenant_id=tenant_id,
                is_active=request.is_active,
                is_superuser=request.is_superuser,
                roles=request.roles or None,
                created_by=superuser_id,
            )
        )
        return UserDetailResponse.model_validate(result.user)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": e.code, "message": e.message},
        ) from e
    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": e.code, "message": e.message},
        ) from e


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update current user",
    description="Update current user's profile (limited fields).",
)
async def update_self(
    request: UserUpdateSelf,
    current_user_id: CurrentUserId,
    session: DbSession,
) -> UserResponse:
    """
    Update current user's profile.

    Only name fields can be updated by the user themselves.
    """
    repo = SQLAlchemyUserRepository(session)
    user = await repo.get_by_id(current_user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "User not found"},
        )

    if request.first_name is not None:
        user.first_name = request.first_name

    if request.last_name is not None:
        user.last_name = request.last_name

    user.mark_updated(by_user=current_user_id)

    updated_user = await repo.update(user)
    await session.commit()
    return UserResponse.model_validate(updated_user)


@router.patch(
    "/{user_id}",
    response_model=UserDetailResponse,
    summary="Update user",
    description="Update user information. Requires superuser privileges.",
)
async def update_user(
    user_id: UUID,
    request: UserUpdate,
    superuser_id: SuperuserId,
    tenant_id: CurrentTenantId,
    session: DbSession,
) -> UserDetailResponse:
    """
    Update user by ID (admin only).

    Partial update - only provided fields will be modified.
    """
    repo = SQLAlchemyUserRepository(session)
    use_case = UpdateUserUseCase(repo)

    # Tenant isolation: verify user belongs to current tenant BEFORE mutation
    existing_user = await repo.get_by_id(user_id)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "User not found"},
        )
    if tenant_id and existing_user.tenant_id and existing_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "User not found"},
        )

    try:
        result = await use_case.execute(
            UpdateUserRequest(
                user_id=user_id,
                email=request.email,
                first_name=request.first_name,
                last_name=request.last_name,
                is_active=request.is_active,
                roles=request.roles,
                updated_by=superuser_id,
            )
        )
        return UserDetailResponse.model_validate(result.user)
    except EntityNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": e.code, "message": e.message},
        ) from e
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": e.code, "message": e.message},
        ) from e
    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": e.code, "message": e.message},
        ) from e


@router.delete(
    "/{user_id}",
    response_model=MessageResponse,
    summary="Delete user",
    description="Soft delete a user. Requires superuser privileges.",
)
async def delete_user(
    user_id: UUID,
    superuser_id: SuperuserId,
    tenant_id: CurrentTenantId,
    session: DbSession,
) -> MessageResponse:
    """
    Soft delete user by ID (admin only).

    User will be marked as deleted but data is retained.
    """
    # Prevent self-deletion
    if user_id == superuser_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "CANNOT_DELETE_SELF",
                "message": "Cannot delete your own account",
            },
        )

    repo = SQLAlchemyUserRepository(session)

    # Tenant isolation: verify user belongs to current tenant before deletion
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "User not found"},
        )
    if tenant_id and user.tenant_id and user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "User not found"},
        )

    use_case = DeleteUserUseCase(repo)

    try:
        await use_case.execute(DeleteUserRequest(user_id=user_id))
        return MessageResponse(
            message="User deleted successfully",
            success=True,
        )
    except EntityNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": e.code, "message": e.message},
        ) from e


# Maximum file size: 5MB
MAX_AVATAR_SIZE = 5 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}

# File magic byte signatures for image validation
_IMAGE_SIGNATURES: dict[str, list[bytes]] = {
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/gif": [b"GIF87a", b"GIF89a"],
    "image/webp": [b"RIFF"],  # Full check: RIFF....WEBP
}


def _validate_image_magic(content: bytes, content_type: str) -> bool:
    """Validate that file content matches claimed content type via magic bytes."""
    sigs = _IMAGE_SIGNATURES.get(content_type, [])
    if not sigs:
        return False
    for sig in sigs:
        if content[: len(sig)] == sig:
            # Extra check for WebP: bytes 8-12 must be 'WEBP'
            if content_type == "image/webp" and content[8:12] != b"WEBP":
                return False
            return True
    return False


@router.post(
    "/me/avatar",
    response_model=UserResponse,
    summary="Upload avatar",
    description="Upload a new profile picture for the current user.",
)
async def upload_avatar(
    current_user_id: CurrentUserId,
    session: DbSession,
    file: UploadFile = File(..., description="Image file (JPEG, PNG, GIF, WebP)"),
) -> UserResponse:
    """
    Upload a new avatar for the current user.

    - Accepts JPEG, PNG, GIF, WebP images
    - Maximum file size: 5MB
    - Previous avatar will be replaced
    """
    # Validate content type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_FILE_TYPE",
                "message": "File must be an image (JPEG, PNG, GIF, WebP)",
            },
        )

    # Read file content
    content = await file.read()

    # Validate file magic bytes match the declared content type
    if not _validate_image_magic(content, file.content_type or ""):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_FILE_TYPE",
                "message": "File content does not match declared content type",
            },
        )

    # Validate file size
    if len(content) > MAX_AVATAR_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "FILE_TOO_LARGE",
                "message": "File size must be less than 5MB",
            },
        )

    # Get user
    repo = SQLAlchemyUserRepository(session)
    user = await repo.get_by_id(current_user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "User not found"},
        )

    # Generate unique filename with extension allowlist
    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
    file_ext = (
        file.filename.split(".")[-1].lower()
        if file.filename and "." in file.filename
        else "jpg"
    )
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_FILE_TYPE",
                "message": f"File extension not allowed. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
            },
        )
    unique_id = uuid_module.uuid4().hex[:12]
    filename = f"avatars/{current_user_id}/{unique_id}.{file_ext}"

    # Upload to storage
    storage = get_storage()
    try:
        storage_file = await storage.upload(
            data=content,
            path=filename,
            content_type=file.content_type,
        )
        avatar_url = storage_file.path
    except Exception as e:
        logger.error("Failed to upload avatar for user %s: %s", current_user_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "UPLOAD_FAILED",
                "message": "Failed to upload avatar",
            },
        ) from e

    # Delete old avatar if exists
    if user.avatar_url:
        try:
            # Extract path from URL if it's a storage path
            old_path = user.avatar_url
            if old_path.startswith("/storage/"):
                old_path = old_path.removeprefix("/storage/")
            await storage.delete(old_path)
        except Exception as e:
            # Log but ignore errors when deleting old avatar
            logger.debug("Failed to delete old avatar %s: %s", user.avatar_url, e)

    # Update user with new avatar URL
    user.avatar_url = avatar_url
    user.mark_updated(by_user=current_user_id)

    updated_user = await repo.update(user)
    return UserResponse.model_validate(updated_user)


@router.delete(
    "/me/avatar",
    response_model=MessageResponse,
    summary="Delete avatar",
    description="Remove the current user's profile picture.",
)
async def delete_avatar(
    current_user_id: CurrentUserId,
    session: DbSession,
) -> MessageResponse:
    """Delete the current user's avatar."""
    repo = SQLAlchemyUserRepository(session)
    user = await repo.get_by_id(current_user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "User not found"},
        )

    if not user.avatar_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "NO_AVATAR", "message": "User has no avatar to delete"},
        )

    # Delete from storage
    storage = get_storage()
    try:
        old_path = user.avatar_url
        if old_path.startswith("/storage/"):
            old_path = old_path.removeprefix("/storage/")
        await storage.delete(old_path)
    except Exception as e:
        # Continue even if delete fails, but log it
        logger.debug("Failed to delete avatar file %s: %s", user.avatar_url, e)

    # Update user
    user.avatar_url = None
    user.mark_updated(by_user=current_user_id)

    await repo.update(user)
    return MessageResponse(message="Avatar deleted successfully")
