# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for MFA domain entity.

Tests for MFA configuration and backup codes.
"""

from datetime import UTC, datetime
from uuid import uuid4

from app.domain.entities.mfa import MFAConfig


class TestMFAConfig:
    """Tests for MFAConfig entity."""

    def test_create_basic_mfa_config(self) -> None:
        """Test creating basic MFA config."""
        user_id = uuid4()

        mfa = MFAConfig(
            user_id=user_id,
            secret="JBSWY3DPEHPK3PXP",
        )

        assert mfa.user_id == user_id
        assert mfa.secret == "JBSWY3DPEHPK3PXP"
        assert mfa.is_enabled is False

    def test_default_values(self) -> None:
        """Test default values."""
        mfa = MFAConfig()

        assert mfa.id is not None
        assert mfa.user_id is not None
        assert mfa.secret == ""
        assert mfa.is_enabled is False
        assert mfa.backup_codes == []
        assert mfa.created_at is not None
        assert mfa.enabled_at is None
        assert mfa.last_used_at is None

    def test_with_backup_codes(self) -> None:
        """Test MFA config with backup codes."""
        codes = ["ABC12345", "DEF67890", "GHI11111"]

        mfa = MFAConfig(backup_codes=codes)

        assert len(mfa.backup_codes) == 3
        assert "ABC12345" in mfa.backup_codes


class TestMFAConfigGenerateBackupCodes:
    """Tests for generate_backup_codes static method."""

    def test_generate_default_count(self) -> None:
        """Test generating default count of backup codes."""
        codes = MFAConfig.generate_backup_codes()

        assert len(codes) == 10

    def test_generate_custom_count(self) -> None:
        """Test generating custom count of backup codes."""
        codes = MFAConfig.generate_backup_codes(count=5)

        assert len(codes) == 5

    def test_generate_codes_are_unique(self) -> None:
        """Test generated codes are unique."""
        codes = MFAConfig.generate_backup_codes(count=100)

        # All codes should be unique
        assert len(codes) == len(set(codes))

    def test_generate_codes_format(self) -> None:
        """Test generated codes format."""
        codes = MFAConfig.generate_backup_codes()

        for code in codes:
            # Should be 8 characters
            assert len(code) == 8
            # Should be uppercase hex
            assert code.upper() == code
            assert all(c in "0123456789ABCDEF" for c in code)

    def test_generate_codes_randomness(self) -> None:
        """Test that generated codes are random."""
        codes1 = MFAConfig.generate_backup_codes()
        codes2 = MFAConfig.generate_backup_codes()

        # Two generations should produce different codes
        assert codes1 != codes2


class TestMFAConfigUseBackupCode:
    """Tests for use_backup_code method."""

    def test_use_valid_backup_code(self) -> None:
        """Test using valid backup code."""
        mfa = MFAConfig(backup_codes=["ABC12345", "DEF67890"])

        result = mfa.use_backup_code("ABC12345")

        assert result is True
        assert "ABC12345" not in mfa.backup_codes
        assert len(mfa.backup_codes) == 1

    def test_use_invalid_backup_code(self) -> None:
        """Test using invalid backup code."""
        mfa = MFAConfig(backup_codes=["ABC12345", "DEF67890"])

        result = mfa.use_backup_code("INVALID1")

        assert result is False
        assert len(mfa.backup_codes) == 2

    def test_use_backup_code_lowercase(self) -> None:
        """Test using backup code in lowercase."""
        mfa = MFAConfig(backup_codes=["ABC12345"])

        result = mfa.use_backup_code("abc12345")

        assert result is True
        assert len(mfa.backup_codes) == 0

    def test_use_backup_code_with_dashes(self) -> None:
        """Test using backup code with dashes."""
        mfa = MFAConfig(backup_codes=["ABC12345"])

        result = mfa.use_backup_code("ABC1-2345")

        assert result is True

    def test_use_backup_code_with_spaces(self) -> None:
        """Test using backup code with spaces."""
        mfa = MFAConfig(backup_codes=["ABC12345"])

        result = mfa.use_backup_code("ABC1 2345")

        assert result is True

    def test_use_backup_code_updates_last_used(self) -> None:
        """Test that using backup code updates last_used_at."""
        mfa = MFAConfig(backup_codes=["ABC12345"])

        assert mfa.last_used_at is None

        before = datetime.now(UTC)
        mfa.use_backup_code("ABC12345")
        after = datetime.now(UTC)

        assert mfa.last_used_at is not None  # First assertion
        assert mfa.last_used_at is not None  # Type narrowing
        assert before <= mfa.last_used_at <= after

    def test_use_backup_code_single_use(self) -> None:
        """Test backup codes can only be used once."""
        mfa = MFAConfig(backup_codes=["ABC12345"])

        # First use
        assert mfa.use_backup_code("ABC12345") is True

        # Second use
        assert mfa.use_backup_code("ABC12345") is False


class TestMFAConfigRegenerateBackupCodes:
    """Tests for regenerate_backup_codes method."""

    def test_regenerate_replaces_codes(self) -> None:
        """Test regenerate replaces old codes."""
        mfa = MFAConfig(backup_codes=["OLD1CODE", "OLD2CODE"])
        old_codes = mfa.backup_codes.copy()

        new_codes = mfa.regenerate_backup_codes()

        assert mfa.backup_codes != old_codes
        assert len(mfa.backup_codes) == 10
        assert new_codes == mfa.backup_codes

    def test_regenerate_returns_new_codes(self) -> None:
        """Test regenerate returns the new codes."""
        mfa = MFAConfig()

        new_codes = mfa.regenerate_backup_codes()

        assert len(new_codes) == 10
        assert new_codes == mfa.backup_codes


class TestMFAConfigEnable:
    """Tests for enable method."""

    def test_enable_mfa(self) -> None:
        """Test enabling MFA."""
        mfa = MFAConfig()

        assert mfa.is_enabled is False
        assert mfa.enabled_at is None

        before = datetime.now(UTC)
        mfa.enable()
        after = datetime.now(UTC)

        assert mfa.is_enabled is True
        assert mfa.enabled_at is not None  # Type narrowing
        assert before <= mfa.enabled_at <= after

    def test_enable_already_enabled(self) -> None:
        """Test enabling already enabled MFA."""
        mfa = MFAConfig(is_enabled=True)

        mfa.enable()

        assert mfa.is_enabled is True


class TestMFAConfigDisable:
    """Tests for disable method."""

    def test_disable_mfa(self) -> None:
        """Test disabling MFA."""
        mfa = MFAConfig()
        mfa.enable()

        assert mfa.is_enabled is True

        mfa.disable()

        assert mfa.is_enabled is False
        assert mfa.enabled_at is None

    def test_disable_already_disabled(self) -> None:
        """Test disabling already disabled MFA."""
        mfa = MFAConfig()

        mfa.disable()

        assert mfa.is_enabled is False


class TestMFAConfigRecordUse:
    """Tests for record_use method."""

    def test_record_use_updates_timestamp(self) -> None:
        """Test record_use updates last_used_at."""
        mfa = MFAConfig()

        assert mfa.last_used_at is None

        before = datetime.now(UTC)
        mfa.record_use()
        after = datetime.now(UTC)

        assert mfa.last_used_at is not None
        assert before <= mfa.last_used_at <= after

    def test_record_use_multiple_times(self) -> None:
        """Test recording use multiple times."""
        mfa = MFAConfig()

        mfa.record_use()
        first_use = mfa.last_used_at
        assert first_use is not None  # Type narrowing

        mfa.record_use()
        second_use = mfa.last_used_at
        assert second_use is not None  # Type narrowing

        assert second_use >= first_use
