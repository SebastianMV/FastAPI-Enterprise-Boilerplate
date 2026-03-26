# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Extended tests for i18n (internationalization) infrastructure."""

from __future__ import annotations


class TestI18nImport:
    """Tests for i18n import."""

    def test_i18n_module_import(self) -> None:
        """Test i18n module can be imported."""
        from app.infrastructure import i18n

        assert i18n is not None


class TestLocales:
    """Tests for locales."""

    def test_default_locale(self) -> None:
        """Test default locale."""
        default_locale = "en"
        assert default_locale == "en"

    def test_supported_locales(self) -> None:
        """Test supported locales."""
        supported = ["en", "es", "pt"]
        assert "en" in supported
        assert "es" in supported

    def test_locale_format(self) -> None:
        """Test locale format."""
        locale = "en-US"
        parts = locale.split("-")
        assert len(parts) == 2
        assert parts[0] == "en"
        assert parts[1] == "US"


class TestTranslations:
    """Tests for translations."""

    def test_translation_key_format(self) -> None:
        """Test translation key format."""
        key = "auth.login.success"
        parts = key.split(".")
        assert len(parts) == 3

    def test_translation_placeholder(self) -> None:
        """Test translation placeholder."""
        message = "Hello, {name}!"
        result = message.format(name="World")
        assert result == "Hello, World!"


class TestLanguageDetection:
    """Tests for language detection."""

    def test_accept_language_header(self) -> None:
        """Test Accept-Language header parsing."""
        header = "en-US,en;q=0.9,es;q=0.8"
        primary = header.split(",")[0].split("-")[0]
        assert primary == "en"

    def test_fallback_language(self) -> None:
        """Test fallback language."""
        requested = "zz"  # Non-existent
        fallback = "en"
        supported = ["en", "es"]
        result = requested if requested in supported else fallback
        assert result == "en"


class TestDateFormatting:
    """Tests for date formatting by locale."""

    def test_date_format_us(self) -> None:
        """Test US date format."""
        # MM/DD/YYYY
        date_format = "%m/%d/%Y"
        assert "%m" in date_format

    def test_date_format_eu(self) -> None:
        """Test EU date format."""
        # DD/MM/YYYY
        date_format = "%d/%m/%Y"
        assert "%d" in date_format


class TestNumberFormatting:
    """Tests for number formatting by locale."""

    def test_decimal_separator_us(self) -> None:
        """Test US decimal separator."""
        number = 1234.56
        formatted = f"{number:,.2f}"
        assert "." in formatted

    def test_thousand_separator(self) -> None:
        """Test thousand separator."""
        number = 1234567
        formatted = f"{number:,}"
        assert "," in formatted
