# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Tests for configuration endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestGetFeatureConfig:
    """Tests for get_feature_config endpoint."""

    @pytest.mark.asyncio
    async def test_get_feature_config_success(self) -> None:
        """Test successful retrieval of feature configuration."""
        from app.api.v1.endpoints.config import get_feature_config

        # Mock current user
        mock_user = MagicMock()

        # Mock settings
        with patch("app.api.v1.endpoints.config.settings") as mock_settings:
            mock_settings.WEBSOCKET_ENABLED = True
            mock_settings.WEBSOCKET_NOTIFICATIONS = True

            result = await get_feature_config(current_user=mock_user)

            assert result.websocket_enabled is True
            assert result.websocket_notifications is True

    @pytest.mark.asyncio
    async def test_get_feature_config_disabled_features(self) -> None:
        """Test feature config with disabled features."""
        from app.api.v1.endpoints.config import get_feature_config

        mock_user = MagicMock()

        with patch("app.api.v1.endpoints.config.settings") as mock_settings:
            mock_settings.WEBSOCKET_ENABLED = False
            mock_settings.WEBSOCKET_NOTIFICATIONS = False

            result = await get_feature_config(current_user=mock_user)

            assert result.websocket_enabled is False
            assert result.websocket_notifications is False
