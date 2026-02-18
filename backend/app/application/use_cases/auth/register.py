# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Register use case — creates new user account."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.config import settings
from app.domain.entities.user import User
from app.domain.exceptions.base import ConflictError, ValidationError
from app.domain.ports.tenant_repository import TenantRepositoryPort
from app.domain.ports.user_repository import UserRepositoryPort
from app.domain.value_objects.email import Email
from app.domain.value_objects.password import Password
from app.infrastructure.auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    hash_password,
)
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class RegisterRequest:
    """Input for register use case."""

    email: str
    password: str
    first_name: str
    last_name: str


@dataclass(frozen=True)
class RegisterResult:
    """Output of register use case."""

    user: User
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int = 0
    requires_verification: bool = False


class RegisterUseCase:
    """Create a new user, optionally send verification email, issue tokens."""

    def __init__(
        self,
        user_repository: UserRepositoryPort,
        tenant_repository: TenantRepositoryPort,
        db_session: Any,
    ) -> None:
        self._user_repo = user_repository
        self._tenant_repo = tenant_repository
        self._db_session = db_session

    async def execute(self, request: RegisterRequest) -> RegisterResult:
        # Validate email
        try:
            email = Email(request.email)
        except ValueError:
            raise ValidationError(
                message="Invalid email format",
                code="INVALID_EMAIL",
                field="email",
            ) from None

        # Validate password strength
        try:
            Password(request.password)
        except ValueError:
            raise ValidationError(
                message="Password does not meet security requirements",
                code="WEAK_PASSWORD",
                field="password",
            ) from None

        # Name length validation
        if request.first_name and len(request.first_name) > 200:
            raise ValidationError(
                message="First name must not exceed 200 characters",
                code="INVALID_LENGTH",
                field="first_name",
            )
        if request.last_name and len(request.last_name) > 200:
            raise ValidationError(
                message="Last name must not exceed 200 characters",
                code="INVALID_LENGTH",
                field="last_name",
            )

        # Uniqueness check
        existing = await self._user_repo.get_by_email(request.email)
        if existing:
            raise ConflictError(
                message="Email already registered",
                code="EMAIL_EXISTS",
            )

        # Ensure a default tenant exists
        default_tenant = await self._tenant_repo.get_default_tenant()
        if not default_tenant:
            from app.domain.entities.tenant import Tenant

            default_tenant = Tenant(
                id=uuid4(),
                name="Default",
                slug="default",
                is_active=True,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            default_tenant = await self._tenant_repo.create(default_tenant)

        # Build user entity
        now = datetime.now(UTC)
        new_user = User(
            id=uuid4(),
            tenant_id=default_tenant.id,
            email=email,
            password_hash=hash_password(request.password),
            first_name=request.first_name,
            last_name=request.last_name,
            is_active=True,
            is_superuser=False,
            roles=[],
            created_at=now,
            updated_at=now,
            last_login=None,
            email_verified=False,
        )

        # Generate verification token
        verification_token = None
        if settings.EMAIL_VERIFICATION_REQUIRED:
            verification_token = new_user.generate_verification_token()

        created_user = await self._user_repo.create(new_user)
        try:
            await self._db_session.commit()
        except Exception:
            await self._db_session.rollback()
            # IntegrityError on commit = concurrent insert (TOCTOU race)
            raise ConflictError(
                message="Email already registered",
                code="EMAIL_EXISTS",
            ) from None

        # Send verification email (fire-and-forget)
        if settings.EMAIL_VERIFICATION_REQUIRED and verification_token:
            await self._send_verification_email(created_user, verification_token)

        # Issue tokens only when email verification is NOT required
        access_token: str | None = None
        refresh_token: str | None = None
        expires_in = 0

        if not settings.EMAIL_VERIFICATION_REQUIRED:
            access_token = create_access_token(
                user_id=created_user.id,
                tenant_id=created_user.tenant_id,
                extra_claims={
                    "is_superuser": created_user.is_superuser,
                    "roles": [str(r) for r in created_user.roles],
                },
            )
            refresh_token = create_refresh_token(
                user_id=created_user.id,
                tenant_id=created_user.tenant_id,
            )
            expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

        return RegisterResult(
            user=created_user,
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=expires_in,
            requires_verification=settings.EMAIL_VERIFICATION_REQUIRED,
        )

    # ------------------------------------------------------------------
    async def _send_verification_email(self, user: User, token: str) -> None:
        try:
            from urllib.parse import quote

            from app.infrastructure.email import get_email_service

            verification_url = (
                f"{settings.FRONTEND_URL}/verify-email?token={quote(token, safe='')}"
            )
            email_service = get_email_service()
            await email_service.send_verification_email(
                to_email=str(user.email),
                to_name=user.first_name,
                verification_url=verification_url,
                expires_in_hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS,
            )
        except Exception:
            logger.warning(
                "verification_email_send_failed",
                exc_info=True,
            )
