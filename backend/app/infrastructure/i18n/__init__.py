# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Internationalization (i18n) infrastructure.

Provides multi-language support for the application.
"""

from functools import lru_cache
from pathlib import Path
from typing import Any

import json

from app.config import settings


class I18n:
    """
    Internationalization service for multi-language support.
    
    Supports loading translations from JSON files and provides
    a simple interface for translating messages.
    
    Usage:
        i18n = get_i18n()
        message = i18n.t("auth.login_success", locale="es")
    """
    
    def __init__(self, translations_dir: Path | None = None) -> None:
        """
        Initialize the i18n service.
        
        Args:
            translations_dir: Directory containing translation JSON files.
                             Defaults to app/infrastructure/i18n/locales
        """
        # Use settings for default locale and supported locales
        self.DEFAULT_LOCALE = settings.DEFAULT_LOCALE
        self.SUPPORTED_LOCALES = settings.SUPPORTED_LOCALES
        
        if translations_dir is None:
            translations_dir = Path(__file__).parent / "locales"
        
        self._translations_dir = translations_dir
        self._translations: dict[str, dict[str, Any]] = {}
        self._load_translations()
    
    def _load_translations(self) -> None:
        """Load all translation files from the locales directory."""
        if not self._translations_dir.exists():
            self._translations_dir.mkdir(parents=True, exist_ok=True)
        
        for locale in self.SUPPORTED_LOCALES:
            locale_file = self._translations_dir / f"{locale}.json"
            if locale_file.exists():
                with open(locale_file, "r", encoding="utf-8") as f:
                    self._translations[locale] = json.load(f)
            else:
                self._translations[locale] = {}
    
    def t(
        self,
        key: str,
        locale: str | None = None,
        default: str | None = None,
        **params: Any,
    ) -> str:
        """
        Translate a message key to the specified locale.
        
        Args:
            key: The translation key (dot-notation: "auth.login_success")
            locale: Target locale (defaults to DEFAULT_LOCALE)
            default: Default value if key not found
            **params: Parameters for string interpolation
            
        Returns:
            Translated string with parameters interpolated
            
        Examples:
            >>> i18n.t("auth.welcome", name="John")
            "Welcome, John!"
            
            >>> i18n.t("errors.not_found", locale="es")
            "No encontrado"
        """
        locale = locale or self.DEFAULT_LOCALE
        
        # Fallback chain: requested locale -> default locale -> key
        message = self._get_nested(key, locale)
        if message is None and locale != self.DEFAULT_LOCALE:
            message = self._get_nested(key, self.DEFAULT_LOCALE)
        if message is None:
            message = default or key
        
        # Interpolate parameters
        if params:
            try:
                message = message.format(**params)
            except KeyError:
                pass  # Return message as-is if params don't match
        
        return message
    
    def _get_nested(self, key: str, locale: str) -> str | None:
        """
        Get a nested translation by dot-notation key.
        
        Args:
            key: Dot-separated key (e.g., "auth.errors.invalid_token")
            locale: Target locale
            
        Returns:
            Translation string or None if not found
        """
        translations = self._translations.get(locale, {})
        
        parts = key.split(".")
        current = translations
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        
        return current if isinstance(current, str) else None
    
    def get_available_locales(self) -> list[str]:
        """Get list of available locales with translations."""
        return [
            locale
            for locale in self.SUPPORTED_LOCALES
            if self._translations.get(locale)
        ]
    
    def is_supported(self, locale: str) -> bool:
        """Check if a locale is supported."""
        return locale in self.SUPPORTED_LOCALES
    
    def get_locale_from_header(
        self,
        accept_language: str | None,
        default: str | None = None,
    ) -> str:
        """
        Parse Accept-Language header and return best matching locale.
        
        Args:
            accept_language: Value of Accept-Language HTTP header
            default: Default locale if no match found
            
        Returns:
            Best matching locale code
            
        Example:
            >>> i18n.get_locale_from_header("es-MX,es;q=0.9,en;q=0.8")
            "es"
        """
        if not accept_language:
            return default or self.DEFAULT_LOCALE
        
        # Parse header: "en-US,en;q=0.9,es;q=0.8" -> [(en-US, 1.0), (en, 0.9), (es, 0.8)]
        locales_with_quality: list[tuple[str, float]] = []
        
        for item in accept_language.split(","):
            parts = item.strip().split(";")
            locale = parts[0].strip()
            
            # Extract quality factor
            quality = 1.0
            if len(parts) > 1:
                for param in parts[1:]:
                    if param.strip().startswith("q="):
                        try:
                            quality = float(param.strip()[2:])
                        except ValueError:
                            pass
            
            locales_with_quality.append((locale, quality))
        
        # Sort by quality (highest first)
        locales_with_quality.sort(key=lambda x: x[1], reverse=True)
        
        # Find first matching supported locale
        for locale, _ in locales_with_quality:
            # Try exact match
            if locale in self.SUPPORTED_LOCALES:
                return locale
            
            # Try language code only (e.g., "en-US" -> "en")
            lang_code = locale.split("-")[0]
            if lang_code in self.SUPPORTED_LOCALES:
                return lang_code
        
        return default or self.DEFAULT_LOCALE


@lru_cache
def get_i18n() -> I18n:
    """Get cached i18n instance."""
    return I18n()
