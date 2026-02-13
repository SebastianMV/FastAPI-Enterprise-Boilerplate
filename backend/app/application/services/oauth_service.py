# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
OAuth2/SSO service for handling OAuth authentication flows.
"""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.domain.entities.oauth import (
    OAuthConnection,
    OAuthProvider,
    OAuthState,
    OAuthUserInfo,
    SSOConfiguration,
)
from app.domain.entities.user import User
from app.domain.exceptions.base import (
    AuthenticationError,
    BusinessRuleViolationError,
    ConflictError,
    EntityNotFoundError,
    ValidationError as DomainValidationError,
)
from app.infrastructure.auth.encryption import decrypt_value, encrypt_value
from app.infrastructure.auth.oauth_providers import (
    OAuthProviderBase,
    get_oauth_provider,
)
from app.infrastructure.cache import get_cache
from app.infrastructure.database.models.oauth import (
    OAuthConnectionModel,
    SSOConfigurationModel,
)
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


class OAuthService:
    """
    Service for OAuth2/SSO authentication.

    Handles:
    - OAuth flow initiation and callback
    - User account linking/creation
    - SSO configuration management
    - Token management
    """

    # State expiration (10 minutes)
    STATE_EXPIRATION_SECONDS = 600

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._cache = get_cache()

    # =========================================
    # OAuth Flow
    # =========================================

    async def initiate_oauth(
        self,
        provider: OAuthProvider,
        tenant_id: UUID | None = None,
        redirect_uri: str | None = None,
        scopes: list[str] | None = None,
        linking_user_id: UUID | None = None,
    ) -> tuple[str, str]:
        """
        Initiate OAuth flow.

        Args:
            provider: OAuth provider to use
            tenant_id: Tenant context (optional)
            redirect_uri: Custom redirect URI (optional)
            scopes: Additional scopes to request
            linking_user_id: If linking to existing account

        Returns:
            Tuple of (authorization_url, state)
        """
        # Get provider config
        oauth_provider = await self._get_provider(provider, tenant_id)

        # Generate state and PKCE
        state = secrets.token_urlsafe(32)
        code_verifier, code_challenge = oauth_provider.generate_pkce()
        nonce = secrets.token_urlsafe(16)

        # Store state in cache
        state_data = OAuthState(
            state=state,
            provider=provider,
            tenant_id=tenant_id,
            redirect_uri=redirect_uri or oauth_provider.redirect_uri,
            nonce=nonce,
            code_verifier=code_verifier,
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC)
            + timedelta(seconds=self.STATE_EXPIRATION_SECONDS),
            is_linking=linking_user_id is not None,
            existing_user_id=linking_user_id,
        )

        await self._store_oauth_state(state, state_data)

        # Build authorization URL
        auth_url = oauth_provider.get_authorization_url(
            state=state,
            scopes=scopes,
            code_challenge=code_challenge,
            extra_params={"nonce": nonce} if provider == OAuthProvider.GOOGLE else None,
        )

        return auth_url, state

    async def handle_callback(
        self,
        provider: OAuthProvider,
        code: str,
        state: str,
    ) -> tuple[User, OAuthConnection, bool]:
        """
        Handle OAuth callback.

        Args:
            provider: OAuth provider
            code: Authorization code
            state: State from callback

        Returns:
            Tuple of (user, oauth_connection, is_new_user)

        Raises:
            ValueError: If state is invalid or expired
        """
        # Validate state
        state_data = await self._get_oauth_state(state)
        if not state_data:
            raise AuthenticationError(
                message="Invalid or expired OAuth state",
                code="INVALID_OAUTH_STATE",
            )

        if state_data.provider != provider:
            raise AuthenticationError(
                message="Provider mismatch",
                code="PROVIDER_MISMATCH",
            )

        # Clean up state
        await self._delete_oauth_state(state)

        # Get provider and exchange code
        oauth_provider = await self._get_provider(provider, state_data.tenant_id)
        tokens = await oauth_provider.exchange_code(
            code=code,
            code_verifier=state_data.code_verifier,
        )

        # Get user info from provider
        user_info = await oauth_provider.get_user_info(tokens.access_token)

        # Find or create user
        if state_data.is_linking and state_data.existing_user_id:
            # Linking to existing account
            user, connection = await self._link_oauth_account(
                user_id=state_data.existing_user_id,
                tenant_id=state_data.tenant_id or await self._get_default_tenant_id(),
                user_info=user_info,
                tokens=tokens,
            )
            is_new_user = False
        else:
            # Login or register
            user, connection, is_new_user = await self._find_or_create_user(
                tenant_id=state_data.tenant_id or await self._get_default_tenant_id(),
                user_info=user_info,
                tokens=tokens,
            )

        return user, connection, is_new_user

    async def _find_or_create_user(
        self,
        tenant_id: UUID,
        user_info: OAuthUserInfo,
        tokens: Any,
    ) -> tuple[User, OAuthConnection, bool]:
        """Find existing user or create new one from OAuth info."""
        # Validate email against allowed_domains if configured
        if user_info.email:
            await self._check_allowed_domains(
                user_info.provider, user_info.email, tenant_id=tenant_id
            )

        # First, check if OAuth connection exists for this tenant
        existing_conn = await self._get_oauth_connection(
            provider=user_info.provider,
            provider_user_id=user_info.provider_user_id,
        )

        if existing_conn:
            # Verify the connection belongs to the correct tenant
            conn_user = await self._get_user_by_id(existing_conn.user_id)
            if not conn_user:
                raise EntityNotFoundError(
                    entity_type="User",
                    message="User not found for OAuth connection",
                )
            if conn_user.tenant_id != tenant_id:
                # Cross-tenant OAuth identity — treat as new user for this tenant
                existing_conn = None
            else:
                # Update tokens and return existing user
                await self._update_oauth_connection(
                    connection_id=existing_conn.id,
                    access_token=tokens.access_token,
                    refresh_token=tokens.refresh_token,
                    expires_in=tokens.expires_in,
                )

                if not conn_user.is_active:
                    raise AuthenticationError(
                        message="User account is disabled",
                        code="USER_INACTIVE",
                    )

                return conn_user, existing_conn, False

        # Check if user with email exists
        if user_info.email:
            existing_user = await self._get_user_by_email(user_info.email, tenant_id)

            if existing_user:
                # Only auto-link if the OAuth provider verified the email
                if not user_info.email_verified:
                    raise BusinessRuleViolationError(
                        message="Cannot link account: email not verified by provider",
                        rule="oauth_email_verification_required",
                    )

                # Block disabled accounts from re-authenticating via OAuth
                if not existing_user.is_active:
                    raise AuthenticationError(
                        message="User account is disabled",
                        code="USER_INACTIVE",
                    )

                # Link OAuth to existing user
                connection = await self._create_oauth_connection(
                    user_id=existing_user.id,
                    tenant_id=tenant_id,
                    user_info=user_info,
                    tokens=tokens,
                )
                return existing_user, connection, False

        # Create new user
        user = await self._create_user_from_oauth(
            tenant_id=tenant_id,
            user_info=user_info,
        )

        connection = await self._create_oauth_connection(
            user_id=user.id,
            tenant_id=tenant_id,
            user_info=user_info,
            tokens=tokens,
            is_primary=True,
        )

        return user, connection, True

    async def _link_oauth_account(
        self,
        user_id: UUID,
        tenant_id: UUID,
        user_info: OAuthUserInfo,
        tokens: Any,
    ) -> tuple[User, OAuthConnection]:
        """Link OAuth account to existing user."""
        # Check if already linked
        existing = await self._get_oauth_connection(
            provider=user_info.provider,
            provider_user_id=user_info.provider_user_id,
        )

        if existing:
            if existing.user_id != user_id:
                raise ConflictError(
                    message="This OAuth account is linked to another user",
                    conflicting_field="provider_user_id",
                )
            return await self._get_user_by_id(user_id), existing  # type: ignore

        # Create new connection
        connection = await self._create_oauth_connection(
            user_id=user_id,
            tenant_id=tenant_id,
            user_info=user_info,
            tokens=tokens,
        )

        user = await self._get_user_by_id(user_id)
        if not user:
            raise EntityNotFoundError(
                entity_type="User",
                message="User not found",
            )

        return user, connection

    # =========================================
    # Connection Management
    # =========================================

    async def get_user_connections(
        self,
        user_id: UUID,
    ) -> list[OAuthConnection]:
        """Get all OAuth connections for a user."""
        stmt = select(OAuthConnectionModel).where(
            OAuthConnectionModel.user_id == user_id,
            OAuthConnectionModel.is_active == True,
        )

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_connection(m) for m in models]

    async def unlink_oauth_account(
        self,
        user_id: UUID,
        connection_id: UUID,
    ) -> bool:
        """Unlink an OAuth account from user."""
        stmt = select(OAuthConnectionModel).where(
            OAuthConnectionModel.id == connection_id,
            OAuthConnectionModel.user_id == user_id,
        )

        result = await self._session.execute(stmt)
        connection = result.scalar_one_or_none()

        if not connection:
            return False

        # Check if it's the only login method
        if connection.is_primary:
            # Check if user has password
            user_stmt = select(UserModel).where(UserModel.id == user_id)
            user_result = await self._session.execute(user_stmt)
            user = user_result.scalar_one_or_none()

            if user and (not user.password_hash or user.password_hash == "!oauth"):
                raise BusinessRuleViolationError(
                    message="Cannot unlink primary OAuth account without setting a password",
                    rule="oauth_primary_unlink_requires_password",
                )

        # Soft delete
        connection.is_active = False
        connection.updated_at = datetime.now(UTC)

        await self._session.flush()
        return True

    # =========================================
    # SSO Configuration
    # =========================================

    async def get_sso_config(
        self,
        tenant_id: UUID,
        provider: OAuthProvider | None = None,
        decrypt_secrets: bool = False,
    ) -> list[SSOConfiguration]:
        """Get SSO configurations for a tenant.

        Args:
            tenant_id: Tenant to get configs for
            provider: Optional filter by provider
            decrypt_secrets: If True, decrypt client_secret (only for provider use)
        """
        stmt = select(SSOConfigurationModel).where(
            SSOConfigurationModel.tenant_id == tenant_id,
            SSOConfigurationModel.is_enabled == True,
        )

        if provider:
            stmt = stmt.where(SSOConfigurationModel.provider == provider.value)

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        if decrypt_secrets:
            return [self._model_to_sso_config(m) for m in models]
        return [self._model_to_sso_config_safe(m) for m in models]

    async def create_sso_config(
        self,
        tenant_id: UUID,
        provider: OAuthProvider,
        name: str,
        client_id: str,
        client_secret: str,
        **kwargs: Any,
    ) -> SSOConfiguration:
        """Create SSO configuration for a tenant."""
        config_id = uuid4()
        now = datetime.now(UTC)

        model = SSOConfigurationModel(
            id=config_id,
            tenant_id=tenant_id,
            provider=provider.value,
            name=name,
            client_id=client_id,
            client_secret=encrypt_value(client_secret),
            scopes=kwargs.get("scopes", []),
            attribute_mapping=kwargs.get("attribute_mapping", {}),
            auto_create_users=kwargs.get("auto_create_users", True),
            auto_update_users=kwargs.get("auto_update_users", True),
            default_role_id=kwargs.get("default_role_id"),
            allowed_domains=kwargs.get("allowed_domains", []),
            is_required=kwargs.get("is_required", False),
            is_enabled=True,
            created_at=now,
            updated_at=now,
        )

        self._session.add(model)
        await self._session.flush()

        return self._model_to_sso_config(model)

    # =========================================
    # Helper Methods
    # =========================================

    async def _get_provider(
        self,
        provider: OAuthProvider,
        tenant_id: UUID | None = None,
    ) -> OAuthProviderBase:
        """Get OAuth provider instance with config."""
        # Check for tenant-specific SSO config
        if tenant_id:
            sso_configs = await self.get_sso_config(
                tenant_id, provider, decrypt_secrets=True
            )
            if sso_configs:
                config = sso_configs[0]
                return get_oauth_provider(
                    provider=provider,
                    client_id=config.client_id,
                    client_secret=config.client_secret,
                    redirect_uri=self._get_redirect_uri(provider),
                )

        # Use default config from settings
        client_id, client_secret = self._get_default_oauth_config(provider)

        return get_oauth_provider(
            provider=provider,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=self._get_redirect_uri(provider),
        )

    def _get_default_oauth_config(
        self,
        provider: OAuthProvider,
    ) -> tuple[str, str]:
        """Get default OAuth config from settings."""
        config_map = {
            OAuthProvider.GOOGLE: (
                getattr(settings, "OAUTH_GOOGLE_CLIENT_ID", ""),
                getattr(settings, "OAUTH_GOOGLE_CLIENT_SECRET", ""),
            ),
            OAuthProvider.GITHUB: (
                getattr(settings, "OAUTH_GITHUB_CLIENT_ID", ""),
                getattr(settings, "OAUTH_GITHUB_CLIENT_SECRET", ""),
            ),
            OAuthProvider.MICROSOFT: (
                getattr(settings, "OAUTH_MICROSOFT_CLIENT_ID", ""),
                getattr(settings, "OAUTH_MICROSOFT_CLIENT_SECRET", ""),
            ),
        }

        return config_map.get(provider, ("", ""))

    def _get_redirect_uri(self, provider: OAuthProvider) -> str:
        """Build redirect URI for provider."""
        base_url = getattr(settings, "APP_BASE_URL", "http://localhost:8000")
        if settings.ENVIRONMENT in (
            "production",
            "staging",
        ) and not base_url.startswith("https://"):
            logger.warning("app_base_url_not_https", environment=settings.ENVIRONMENT)
        return f"{base_url}/api/v1/auth/oauth/{provider.value}/callback"

    async def _store_oauth_state(self, state: str, data: OAuthState) -> None:
        """Store OAuth state in cache.

        Raises ``ServiceUnavailableError`` if the cache is unavailable so
        that the caller receives an immediate error instead of a confusing
        failure on the callback leg.
        """
        from app.domain.exceptions.base import ServiceUnavailableError

        cache_key = f"oauth_state:{state}"
        cache_data = {
            "state": data.state,
            "provider": data.provider.value,
            "tenant_id": str(data.tenant_id) if data.tenant_id else None,
            "redirect_uri": data.redirect_uri,
            "nonce": data.nonce,
            "code_verifier": data.code_verifier,
            "is_linking": data.is_linking,
            "existing_user_id": str(data.existing_user_id)
            if data.existing_user_id
            else None,
        }

        stored = await self._cache.set(
            cache_key,
            cache_data,
            ttl=self.STATE_EXPIRATION_SECONDS,
        )
        if stored is False:
            raise ServiceUnavailableError(
                service="cache",
                message="Unable to initiate OAuth flow. Please try again later.",
            )

    async def _get_oauth_state(self, state: str) -> OAuthState | None:
        """Get OAuth state from cache."""
        cache_key = f"oauth_state:{state}"
        data = await self._cache.get(cache_key)

        if not data:
            return None

        return OAuthState(
            state=data["state"],
            provider=OAuthProvider(data["provider"]),
            tenant_id=UUID(data["tenant_id"]) if data.get("tenant_id") else None,
            redirect_uri=data.get("redirect_uri"),
            nonce=data.get("nonce"),
            code_verifier=data.get("code_verifier"),
            is_linking=data.get("is_linking", False),
            existing_user_id=UUID(data["existing_user_id"])
            if data.get("existing_user_id")
            else None,
        )

    async def _delete_oauth_state(self, state: str) -> None:
        """Delete OAuth state from cache."""
        cache_key = f"oauth_state:{state}"
        await self._cache.delete(cache_key)

    async def _check_allowed_domains(
        self, provider: OAuthProvider, email: str, tenant_id: UUID | None = None
    ) -> None:
        """Validate email against the SSO provider's allowed_domains list (if configured)."""
        from app.infrastructure.database.models.oauth import SSOConfigurationModel

        conditions = [
            SSOConfigurationModel.provider == provider.value,
            SSOConfigurationModel.is_enabled == True,
        ]
        if tenant_id:
            conditions.append(SSOConfigurationModel.tenant_id == tenant_id)

        stmt = select(SSOConfigurationModel).where(*conditions)
        result = await self._session.execute(stmt)
        sso_config = result.scalar_one_or_none()

        if sso_config and sso_config.allowed_domains:
            email_domain = email.rsplit("@", 1)[-1].lower()
            if email_domain not in [d.lower() for d in sso_config.allowed_domains]:
                raise BusinessRuleViolationError(
                    message="Email domain not allowed for this provider",
                    rule="sso_domain_restriction",
                )

    async def _get_default_tenant_id(self) -> UUID:
        """Get default tenant ID."""
        # This should return a default tenant - implementation depends on your setup
        from app.infrastructure.database.models.tenant import TenantModel

        stmt = select(TenantModel).order_by(TenantModel.created_at).limit(1)
        result = await self._session.execute(stmt)
        tenant = result.scalar_one_or_none()

        if tenant:
            return UUID(str(tenant.id))

        raise EntityNotFoundError(
            entity_type="Tenant",
            message="No default tenant found",
        )

    async def _get_oauth_connection(
        self,
        provider: OAuthProvider,
        provider_user_id: str,
    ) -> OAuthConnection | None:
        """Get OAuth connection by provider and provider user ID."""
        stmt = select(OAuthConnectionModel).where(
            OAuthConnectionModel.provider == provider.value,
            OAuthConnectionModel.provider_user_id == provider_user_id,
            OAuthConnectionModel.is_active == True,
        )

        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        return self._model_to_connection(model) if model else None

    async def _create_oauth_connection(
        self,
        user_id: UUID,
        tenant_id: UUID,
        user_info: OAuthUserInfo,
        tokens: Any,
        is_primary: bool = False,
    ) -> OAuthConnection:
        """Create new OAuth connection."""
        connection_id = uuid4()
        now = datetime.now(UTC)

        expires_at = None
        if tokens.expires_in:
            expires_at = now + timedelta(seconds=tokens.expires_in)

        model = OAuthConnectionModel(
            id=connection_id,
            user_id=user_id,
            tenant_id=tenant_id,
            provider=user_info.provider.value,
            provider_user_id=user_info.provider_user_id,
            provider_email=user_info.email,
            provider_username=user_info.raw_data.get("login"),  # GitHub username
            provider_display_name=user_info.name,
            provider_avatar_url=user_info.picture,
            access_token=encrypt_value(tokens.access_token)
            if tokens.access_token
            else None,
            refresh_token=encrypt_value(tokens.refresh_token)
            if tokens.refresh_token
            else None,
            token_expires_at=expires_at,
            scopes=tokens.scope.split() if tokens.scope else [],
            raw_data=user_info.raw_data,
            is_primary=is_primary,
            is_active=True,
            last_used_at=now,
            created_at=now,
            updated_at=now,
        )

        self._session.add(model)
        await self._session.flush()

        return self._model_to_connection(model)

    async def _update_oauth_connection(
        self,
        connection_id: UUID,
        access_token: str,
        refresh_token: str | None,
        expires_in: int | None,
    ) -> None:
        """Update OAuth connection tokens."""
        stmt = select(OAuthConnectionModel).where(
            OAuthConnectionModel.id == connection_id
        )

        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            now = datetime.now(UTC)
            model.access_token = encrypt_value(access_token)
            if refresh_token:
                model.refresh_token = encrypt_value(refresh_token)
            if expires_in:
                model.token_expires_at = now + timedelta(seconds=expires_in)
            model.last_used_at = now
            model.updated_at = now

            await self._session.flush()

    async def _get_user_by_id(self, user_id: UUID) -> User | None:
        """Get user by ID."""
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        from app.domain.value_objects.email import Email

        return User(
            id=UUID(str(model.id)),
            tenant_id=UUID(str(model.tenant_id)),
            email=Email(model.email),
            password_hash=model.password_hash or "",
            first_name=model.first_name or "",
            last_name=model.last_name or "",
            is_active=model.is_active,
            is_superuser=model.is_superuser,
            roles=model.roles or [],
        )

    async def _get_user_by_email(
        self,
        email: str,
        tenant_id: UUID,
    ) -> User | None:
        """Get user by email within tenant."""
        stmt = select(UserModel).where(
            UserModel.email == email,
            UserModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        from app.domain.value_objects.email import Email

        return User(
            id=UUID(str(model.id)),
            tenant_id=UUID(str(model.tenant_id)),
            email=Email(model.email),
            password_hash=model.password_hash or "",
            first_name=model.first_name or "",
            last_name=model.last_name or "",
            is_active=model.is_active,
            is_superuser=model.is_superuser,
            roles=model.roles or [],
        )

    async def _create_user_from_oauth(
        self,
        tenant_id: UUID,
        user_info: OAuthUserInfo,
    ) -> User:
        """Create new user from OAuth info."""
        user_id = uuid4()
        now = datetime.now(UTC)

        # Build name parts
        first_name = user_info.given_name or ""
        last_name = user_info.family_name or ""

        # Fallback: try to split full name
        if not first_name and not last_name and user_info.name:
            parts = user_info.name.split(" ", 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else ""

        # Default first_name if still empty
        if not first_name:
            first_name = user_info.email.split("@")[0] if user_info.email else "User"

        from app.domain.value_objects.email import Email

        if not user_info.email:
            raise DomainValidationError(
                message="OAuth provider did not return an email address",
                field="email",
            )

        model = UserModel(
            id=user_id,
            tenant_id=tenant_id,
            email=user_info.email,
            password_hash="!oauth",  # Non-empty sentinel — OAuth users cannot login with password
            first_name=first_name,
            last_name=last_name,
            is_active=True,
            is_superuser=False,
            email_verified=bool(user_info.email_verified) if user_info.email else False,
            created_at=now,
            updated_at=now,
        )

        self._session.add(model)
        try:
            async with self._session.begin_nested():
                await self._session.flush()
        except Exception:
            # Race condition: concurrent request may have created the user
            existing = await self._get_user_by_email(user_info.email, tenant_id)
            if existing:
                return existing
            raise

        return User(
            id=user_id,
            tenant_id=tenant_id,
            email=Email(user_info.email),
            password_hash="!oauth",
            first_name=first_name,
            last_name=last_name,
            is_active=True,
            is_superuser=False,
            email_verified=bool(user_info.email_verified),
        )

    def _model_to_connection(self, model: OAuthConnectionModel) -> OAuthConnection:
        """Convert model to entity (decrypts tokens at rest)."""
        return OAuthConnection(
            id=UUID(str(model.id)),
            user_id=UUID(str(model.user_id)),
            tenant_id=UUID(str(model.tenant_id)),
            provider=OAuthProvider(model.provider),
            provider_user_id=model.provider_user_id,
            provider_email=model.provider_email,
            provider_username=model.provider_username,
            provider_display_name=model.provider_display_name,
            provider_avatar_url=model.provider_avatar_url,
            access_token=decrypt_value(model.access_token)
            if model.access_token
            else None,
            refresh_token=decrypt_value(model.refresh_token)
            if model.refresh_token
            else None,
            token_expires_at=model.token_expires_at,
            scopes=model.scopes,
            raw_data=model.raw_data,
            is_primary=model.is_primary,
            is_active=model.is_active,
            last_used_at=model.last_used_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _model_to_sso_config(self, model: SSOConfigurationModel) -> SSOConfiguration:
        """Convert model to entity (with decrypted client_secret for provider use)."""
        return SSOConfiguration(
            id=UUID(str(model.id)),
            tenant_id=UUID(str(model.tenant_id)),
            provider=OAuthProvider(model.provider),
            name=model.name,
            client_id=model.client_id,
            client_secret=decrypt_value(model.client_secret)
            if model.client_secret
            else "",
            authorization_url=model.authorization_url,
            token_url=model.token_url,
            userinfo_url=model.userinfo_url,
            scopes=model.scopes,
            attribute_mapping=model.attribute_mapping,
            auto_create_users=model.auto_create_users,
            auto_update_users=model.auto_update_users,
            default_role_id=UUID(str(model.default_role_id))
            if model.default_role_id
            else None,
            allowed_domains=model.allowed_domains,
            is_required=model.is_required,
            is_enabled=model.is_enabled,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _model_to_sso_config_safe(
        self, model: SSOConfigurationModel
    ) -> SSOConfiguration:
        """Convert model to entity WITHOUT decrypting client_secret (for listing/display)."""
        return SSOConfiguration(
            id=UUID(str(model.id)),
            tenant_id=UUID(str(model.tenant_id)),
            provider=OAuthProvider(model.provider),
            name=model.name,
            client_id=model.client_id,
            client_secret="",  # Never expose in listings
            authorization_url=model.authorization_url,
            token_url=model.token_url,
            userinfo_url=model.userinfo_url,
            scopes=model.scopes,
            attribute_mapping=model.attribute_mapping,
            auto_create_users=model.auto_create_users,
            auto_update_users=model.auto_update_users,
            default_role_id=UUID(str(model.default_role_id))
            if model.default_role_id
            else None,
            allowed_domains=model.allowed_domains,
            is_required=model.is_required,
            is_enabled=model.is_enabled,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
