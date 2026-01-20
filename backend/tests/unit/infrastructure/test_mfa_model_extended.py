# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Extended tests for MFA model."""

from __future__ import annotations

from uuid import uuid4
import pytest


class TestMFAConfigModel:
    """Tests for MFAConfig database model."""

    def test_mfa_config_repr(self) -> None:
        """Test __repr__ method of MFAConfigModel."""
        from app.infrastructure.database.models.mfa import MFAConfigModel
        from datetime import datetime, timezone
        
        mfa_config = MFAConfigModel(
            id=uuid4(),
            user_id=uuid4(),
            is_enabled=True,
            secret="test_secret_base32",
            backup_codes=[],
            created_at=datetime.now(timezone.utc),
        )
        
        repr_str = repr(mfa_config)
        
        assert "<MFAConfig(" in repr_str
        assert f"id={mfa_config.id}" in repr_str
        assert f"user_id={mfa_config.user_id}" in repr_str
        assert "enabled=True" in repr_str

    def test_mfa_config_repr_disabled(self) -> None:
        """Test __repr__ with disabled MFA."""
        from app.infrastructure.database.models.mfa import MFAConfigModel
        from datetime import datetime, timezone
        
        mfa_config = MFAConfigModel(
            id=uuid4(),
            user_id=uuid4(),
            is_enabled=False,
            secret="test_secret_base32",
            backup_codes=[],
            created_at=datetime.now(timezone.utc),
        )
        
        repr_str = repr(mfa_config)
        
        assert "enabled=False" in repr_str
