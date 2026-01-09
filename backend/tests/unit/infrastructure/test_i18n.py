# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for i18n (internationalization) service.

Tests for I18n class and translation functionality.
"""

import json
import tempfile
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

import pytest

from app.infrastructure.i18n import I18n


class TestI18n:
    """Tests for I18n service."""

    @pytest.fixture
    def temp_locales_dir(self) -> Iterator[Path]:
        """Create a temporary locales directory with test translations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            locales_dir = Path(tmpdir)
            
            # Create English translations
            en_translations = {
                "auth": {
                    "login_success": "Login successful",
                    "welcome": "Welcome, {name}!",
                    "logout": "You have been logged out",
                },
                "errors": {
                    "not_found": "Not found",
                    "forbidden": "Access denied",
                },
                "common": {
                    "yes": "Yes",
                    "no": "No",
                },
            }
            with open(locales_dir / "en.json", "w", encoding="utf-8") as f:
                json.dump(en_translations, f)
            
            # Create Spanish translations
            es_translations = {
                "auth": {
                    "login_success": "Inicio de sesión exitoso",
                    "welcome": "¡Bienvenido, {name}!",
                    "logout": "Has cerrado sesión",
                },
                "errors": {
                    "not_found": "No encontrado",
                    "forbidden": "Acceso denegado",
                },
                "common": {
                    "yes": "Sí",
                    "no": "No",
                },
            }
            with open(locales_dir / "es.json", "w", encoding="utf-8") as f:
                json.dump(es_translations, f)
            
            yield locales_dir

    def test_default_locale(self, temp_locales_dir: Path) -> None:
        """Test default locale is English."""
        i18n = I18n(translations_dir=temp_locales_dir)
        assert i18n.DEFAULT_LOCALE == "en"

    def test_supported_locales(self, temp_locales_dir: Path) -> None:
        """Test supported locales list."""
        i18n = I18n(translations_dir=temp_locales_dir)
        # Note: Full list depends on settings.SUPPORTED_LOCALES
        assert all(lang in i18n.SUPPORTED_LOCALES for lang in ["en", "es", "pt"])

    def test_translate_simple_key(self, temp_locales_dir: Path) -> None:
        """Test simple key translation."""
        i18n = I18n(translations_dir=temp_locales_dir)
        
        result = i18n.t("auth.login_success")
        assert result == "Login successful"

    def test_translate_with_locale(self, temp_locales_dir: Path) -> None:
        """Test translation with specific locale."""
        i18n = I18n(translations_dir=temp_locales_dir)
        
        result = i18n.t("auth.login_success", locale="es")
        assert result == "Inicio de sesión exitoso"

    def test_translate_with_parameters(self, temp_locales_dir: Path) -> None:
        """Test translation with parameter interpolation."""
        i18n = I18n(translations_dir=temp_locales_dir)
        
        result = i18n.t("auth.welcome", name="John")
        assert result == "Welcome, John!"

    def test_translate_with_parameters_and_locale(
        self, temp_locales_dir: Path
    ) -> None:
        """Test translation with parameters and locale."""
        i18n = I18n(translations_dir=temp_locales_dir)
        
        result = i18n.t("auth.welcome", locale="es", name="Juan")
        assert result == "¡Bienvenido, Juan!"

    def test_fallback_to_default_locale(self, temp_locales_dir: Path) -> None:
        """Test fallback to default locale when key not in requested locale."""
        i18n = I18n(translations_dir=temp_locales_dir)
        
        # Portuguese file doesn't exist, should fall back to English
        result = i18n.t("auth.login_success", locale="pt")
        assert result == "Login successful"

    def test_fallback_to_key(self, temp_locales_dir: Path) -> None:
        """Test fallback to key when translation not found."""
        i18n = I18n(translations_dir=temp_locales_dir)
        
        result = i18n.t("nonexistent.key")
        assert result == "nonexistent.key"

    def test_custom_default_value(self, temp_locales_dir: Path) -> None:
        """Test custom default value when key not found."""
        i18n = I18n(translations_dir=temp_locales_dir)
        
        result = i18n.t("nonexistent.key", default="Custom default")
        assert result == "Custom default"

    def test_nested_key_access(self, temp_locales_dir: Path) -> None:
        """Test accessing deeply nested keys."""
        i18n = I18n(translations_dir=temp_locales_dir)
        
        assert i18n.t("errors.not_found") == "Not found"
        assert i18n.t("errors.forbidden") == "Access denied"
        assert i18n.t("common.yes") == "Yes"

    def test_create_locales_dir_if_not_exists(self) -> None:
        """Test that locales directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = Path(tmpdir) / "new_locales"
            assert not new_dir.exists()
            
            i18n = I18n(translations_dir=new_dir)
            
            # Directory should now exist
            assert new_dir.exists()

    def test_missing_parameter_leaves_format_string(
        self, temp_locales_dir: Path
    ) -> None:
        """Test that missing parameters leave format string intact."""
        i18n = I18n(translations_dir=temp_locales_dir)
        
        # Don't provide 'name' parameter
        result = i18n.t("auth.welcome")
        # Should return the template string as-is or with placeholder
        assert "{name}" in result or "Welcome" in result


class TestI18nEdgeCases:
    """Edge case tests for I18n."""

    def test_empty_translations_file(self) -> None:
        """Test handling of empty translations file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            locales_dir = Path(tmpdir)
            with open(locales_dir / "en.json", "w") as f:
                json.dump({}, f)
            
            i18n = I18n(translations_dir=locales_dir)
            
            # Should fall back to key
            assert i18n.t("any.key") == "any.key"

    def test_special_characters_in_translation(self) -> None:
        """Test translations with special characters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            locales_dir = Path(tmpdir)
            translations = {
                "special": {
                    "emoji": "Hello 👋 World 🌍",
                    "unicode": "日本語テスト",
                    "accents": "Ñoño está aquí",
                }
            }
            with open(locales_dir / "en.json", "w", encoding="utf-8") as f:
                json.dump(translations, f, ensure_ascii=False)
            
            i18n = I18n(translations_dir=locales_dir)
            
            assert i18n.t("special.emoji") == "Hello 👋 World 🌍"
            assert i18n.t("special.unicode") == "日本語テスト"
            assert i18n.t("special.accents") == "Ñoño está aquí"

    def test_invalid_locale_falls_back(self) -> None:
        """Test that invalid locale falls back to default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            locales_dir = Path(tmpdir)
            with open(locales_dir / "en.json", "w") as f:
                json.dump({"test": "value"}, f)
            
            i18n = I18n(translations_dir=locales_dir)
            
            # Requesting invalid locale should fall back to en
            result = i18n.t("test", locale="invalid_locale")
            assert result == "value"


class TestI18nMethods:
    """Tests for I18n helper methods."""

    @pytest.fixture
    def temp_locales_dir(self) -> Iterator[Path]:
        """Create a temporary locales directory with test translations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            locales_dir = Path(tmpdir)
            
            # Create English translations
            with open(locales_dir / "en.json", "w", encoding="utf-8") as f:
                json.dump({"test": "English"}, f)
            
            # Create Spanish translations
            with open(locales_dir / "es.json", "w", encoding="utf-8") as f:
                json.dump({"test": "Español"}, f)
            
            yield locales_dir

    def test_get_available_locales(self, temp_locales_dir: Path) -> None:
        """Test get_available_locales returns only locales with translations."""
        i18n = I18n(translations_dir=temp_locales_dir)
        
        available = i18n.get_available_locales()
        
        assert "en" in available
        assert "es" in available
        assert "fr" not in available  # Not created

    def test_is_supported_returns_true(self, temp_locales_dir: Path) -> None:
        """Test is_supported returns True for supported locales."""
        i18n = I18n(translations_dir=temp_locales_dir)
        
        assert i18n.is_supported("en") is True
        assert i18n.is_supported("es") is True
        # Note: default settings only has en, es, pt, fr, de
        assert i18n.is_supported("pt") is True

    def test_is_supported_returns_false(self, temp_locales_dir: Path) -> None:
        """Test is_supported returns False for unsupported locales."""
        i18n = I18n(translations_dir=temp_locales_dir)
        
        assert i18n.is_supported("invalid") is False
        assert i18n.is_supported("xx") is False
        assert i18n.is_supported("") is False


class TestGetLocaleFromHeader:
    """Tests for get_locale_from_header method."""

    @pytest.fixture
    def i18n(self) -> I18n:
        """Create i18n instance with minimal setup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            locales_dir = Path(tmpdir)
            with open(locales_dir / "en.json", "w") as f:
                json.dump({}, f)
            return I18n(translations_dir=locales_dir)

    def test_none_header_returns_default(self, i18n: I18n) -> None:
        """Test None header returns default locale."""
        result = i18n.get_locale_from_header(None)
        assert result == "en"

    def test_none_header_with_custom_default(self, i18n: I18n) -> None:
        """Test None header returns custom default."""
        result = i18n.get_locale_from_header(None, default="es")
        assert result == "es"

    def test_empty_header_returns_default(self, i18n: I18n) -> None:
        """Test empty header returns default."""
        result = i18n.get_locale_from_header("")
        assert result == "en"

    def test_simple_locale(self, i18n: I18n) -> None:
        """Test simple locale header."""
        result = i18n.get_locale_from_header("es")
        assert result == "es"

    def test_locale_with_region(self, i18n: I18n) -> None:
        """Test locale with region code."""
        result = i18n.get_locale_from_header("es-MX")
        assert result == "es"

    def test_multiple_locales_selects_highest_quality(self, i18n: I18n) -> None:
        """Test multiple locales sorted by quality."""
        header = "fr;q=0.5,es;q=0.9,en;q=0.8"
        result = i18n.get_locale_from_header(header)
        assert result == "es"  # Highest quality supported

    def test_standard_accept_language_header(self, i18n: I18n) -> None:
        """Test standard Accept-Language header format."""
        header = "en-US,en;q=0.9,es;q=0.8,fr;q=0.7"
        result = i18n.get_locale_from_header(header)
        assert result == "en"

    def test_unsupported_locale_falls_back(self, i18n: I18n) -> None:
        """Test unsupported locale falls back to default."""
        result = i18n.get_locale_from_header("xx-XX")
        assert result == "en"

    def test_quality_default_is_one(self, i18n: I18n) -> None:
        """Test locale without quality has implicit q=1.0."""
        header = "de,es;q=0.9"
        result = i18n.get_locale_from_header(header)
        assert result == "de"  # Implicit q=1.0 > explicit q=0.9

    def test_invalid_quality_uses_default(self, i18n: I18n) -> None:
        """Test invalid quality value is ignored."""
        header = "es;q=invalid,en"
        result = i18n.get_locale_from_header(header)
        # Both have implicit 1.0 since invalid q is ignored
        assert result in ["es", "en"]

    def test_multiple_params_extracts_quality(self, i18n: I18n) -> None:
        """Test multiple semicolon params still extracts quality."""
        header = "es;level=1;q=0.8,en;q=0.9"
        result = i18n.get_locale_from_header(header)
        assert result == "en"

    def test_all_unsupported_returns_default(self, i18n: I18n) -> None:
        """Test all unsupported locales returns default."""
        header = "xx,yy,zz"
        result = i18n.get_locale_from_header(header)
        assert result == "en"

    def test_all_unsupported_with_custom_default(self, i18n: I18n) -> None:
        """Test all unsupported with custom default."""
        header = "xx,yy,zz"
        result = i18n.get_locale_from_header(header, default="es")
        assert result == "es"


class TestGetI18n:
    """Tests for get_i18n factory function."""

    def test_get_i18n_returns_instance(self) -> None:
        """Test get_i18n returns an I18n instance."""
        from app.infrastructure.i18n import get_i18n
        
        # Clear cache to ensure fresh instance
        get_i18n.cache_clear()
        
        result = get_i18n()
        
        assert isinstance(result, I18n)

    def test_get_i18n_is_cached(self) -> None:
        """Test get_i18n returns same cached instance."""
        from app.infrastructure.i18n import get_i18n
        
        # Clear cache
        get_i18n.cache_clear()
        
        instance1 = get_i18n()
        instance2 = get_i18n()
        
        assert instance1 is instance2

    def test_get_i18n_has_default_locale(self) -> None:
        """Test cached instance has default locale."""
        from app.infrastructure.i18n import get_i18n
        
        get_i18n.cache_clear()
        i18n = get_i18n()
        
        assert i18n.DEFAULT_LOCALE == "en"
