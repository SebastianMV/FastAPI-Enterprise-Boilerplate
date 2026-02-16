# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Extended tests for MFA model."""

from __future__ import annotations

from datetime import UTC
from uuid import uuid4


class TestMFAConfigModel:
    """Tests for MFAConfig database model."""

    def test_mfa_config_repr(self) -> None:
        """Test __repr__ method of MFAConfigModel."""
        from datetime import datetime

        from app.infrastructure.database.models.mfa import MFAConfigModel

        mfa_config = MFAConfigModel(
            id=uuid4(),
            user_id=uuid4(),
            is_enabled=True,
            secret="test_secret_base32",
            backup_codes=[],
            created_at=datetime.now(UTC),
        )

        repr_str = repr(mfa_config)

        assert "<MFAConfig(" in repr_str
        assert f"id={mfa_config.id}" in repr_str
        # user_id and enabled must NOT appear in repr (security)
        assert "user_id" not in repr_str
        assert "enabled" not in repr_str

    def test_mfa_config_repr_disabled(self) -> None:
        """Test __repr__ with disabled MFA."""
        from datetime import datetime

        from app.infrastructure.database.models.mfa import MFAConfigModel

        mfa_config = MFAConfigModel(
            id=uuid4(),
            user_id=uuid4(),
            is_enabled=False,
            secret="test_secret_base32",
            backup_codes=[],
            created_at=datetime.now(UTC),
        )

        repr_str = repr(mfa_config)

        # Sensitive fields must NOT appear in repr
        assert "enabled" not in repr_str
        assert "secret" not in repr_str
