# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Users CRUD endpoints."""

import uuid as uuid_module
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status, UploadFile, File

from app.api.deps import CurrentUserId, CurrentTenantId, DbSession, SuperuserId
from app.api.v1.schemas.common import MessageResponse
from app.api.v1.schemas.users import (
    UserCreate,
    UserDetailResponse,
    UserListResponse,
    UserResponse,
    UserUpdate,
    UserUpdateSelf,
)
from app.domain.exceptions.base import ConflictError, EntityNotFoundError
from app.domain.value_objects.email import Email
from app.domain.value_objects.password import Password
from app.infrastructure.auth.jwt_handler import hash_password
from app.infrastructure.database.repositories.user_repository import (
    SQLAlchemyUserRepository,
)
from app.infrastructure.storage import get_storage

router = APIRouter()


@router.get(
    "",
    response_model=UserListResponse,
    summary="List users",
    description="List all users with pagination. Requires authentication.",
)
async def list_users(
    current_user_id: CurrentUserId,
    session: DbSession,
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
    users = await repo.list(skip=skip, limit=page_size, is_active=is_active)
    total = await repo.count(is_active=is_active)
    
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
    current_user_id: CurrentUserId,
    session: DbSession,
) -> UserDetailResponse:
    """
    Get user by ID.
    
    Returns detailed user information including roles and tenant.
    """
    repo = SQLAlchemyUserRepository(session)
    user = await repo.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": f"User {user_id} not found"},
        )
    
    return UserDetailResponse.model_validate(user)


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
    # Validate email
    try:
        email = Email(request.email)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_EMAIL", "message": str(e)},
        )
    
    # Validate password
    try:
        password = Password(request.password)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "WEAK_PASSWORD", "message": str(e)},
        )
    
    repo = SQLAlchemyUserRepository(session)
    
    # Check email uniqueness
    if await repo.exists_by_email(request.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "EMAIL_EXISTS", "message": "Email already registered"},
        )
    
    # Create user
    from uuid import uuid4
    from app.domain.entities.user import User
    
    user = User(
        id=uuid4(),
        tenant_id=tenant_id or uuid4(),
        email=email,
        password_hash=hash_password(password.value),
        first_name=request.first_name,
        last_name=request.last_name,
        is_active=request.is_active,
        is_superuser=request.is_superuser,
        roles=request.roles,
        created_by=superuser_id,
    )
    
    try:
        created_user = await repo.create(user)
        return UserDetailResponse.model_validate(created_user)
    
    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": e.code, "message": e.message},
        )


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
    session: DbSession,
) -> UserDetailResponse:
    """
    Update user by ID (admin only).
    
    Partial update - only provided fields will be modified.
    """
    repo = SQLAlchemyUserRepository(session)
    user = await repo.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": f"User {user_id} not found"},
        )
    
    # Update fields if provided
    if request.email is not None:
        try:
            user.email = Email(request.email)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_EMAIL", "message": str(e)},
            )
        
        # Check email uniqueness if changed
        if await repo.exists_by_email(request.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "EMAIL_EXISTS", "message": "Email already registered"},
            )
    
    if request.first_name is not None:
        user.first_name = request.first_name
    
    if request.last_name is not None:
        user.last_name = request.last_name
    
    if request.is_active is not None:
        user.is_active = request.is_active
    
    if request.roles is not None:
        user.roles = request.roles
    
    user.mark_updated(by_user=superuser_id)
    
    try:
        updated_user = await repo.update(user)
        return UserDetailResponse.model_validate(updated_user)
    
    except EntityNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": e.code, "message": e.message},
        )


@router.delete(
    "/{user_id}",
    response_model=MessageResponse,
    summary="Delete user",
    description="Soft delete a user. Requires superuser privileges.",
)
async def delete_user(
    user_id: UUID,
    superuser_id: SuperuserId,
    session: DbSession,
) -> MessageResponse:
    """
    Soft delete user by ID (admin only).
    
    User will be marked as deleted but data is retained.
    """
    repo = SQLAlchemyUserRepository(session)
    
    try:
        await repo.delete(user_id)
        return MessageResponse(
            message=f"User {user_id} deleted successfully",
            success=True,
        )
    
    except EntityNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": e.code, "message": e.message},
        )


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
    return UserResponse.model_validate(updated_user)


# Maximum file size: 5MB
MAX_AVATAR_SIZE = 5 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


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
                "message": f"File must be an image (JPEG, PNG, GIF, WebP). Got: {file.content_type}",
            },
        )
    
    # Read file content
    content = await file.read()
    
    # Validate file size
    if len(content) > MAX_AVATAR_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "FILE_TOO_LARGE",
                "message": f"File size must be less than 5MB. Got: {len(content) / (1024 * 1024):.2f}MB",
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
    
    # Generate unique filename
    file_ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"
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
        avatar_url = storage_file.url
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "UPLOAD_FAILED",
                "message": f"Failed to upload avatar: {str(e)}",
            },
        )
    
    # Delete old avatar if exists
    if user.avatar_url:
        try:
            # Extract path from URL if it's a storage path
            old_path = user.avatar_url
            if old_path.startswith("/storage/"):
                old_path = old_path[9:]  # Remove /storage/ prefix
            await storage.delete(old_path)
        except Exception:
            # Ignore errors when deleting old avatar
            pass
    
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
            old_path = old_path[9:]
        await storage.delete(old_path)
    except Exception:
        # Continue even if delete fails
        pass
    
    # Update user
    user.avatar_url = None
    user.mark_updated(by_user=current_user_id)
    
    await repo.update(user)
    return MessageResponse(message="Avatar deleted successfully")
