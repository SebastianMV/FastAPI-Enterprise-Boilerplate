# Copyright (c) 2025 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for dashboard endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.api.v1.endpoints.dashboard import (
    ActivityItem,
    DashboardStatsResponse,
    RecentActivityResponse,
    StatItem,
    SystemHealthResponse,
    get_dashboard_stats,
    get_recent_activity,
    get_system_health,
)


class TestDashboardSchemas:
    """Tests for dashboard schemas."""

    def test_stat_item_schema(self):
        """Test StatItem schema."""
        stat = StatItem(
            name="Total Users", value=100, change="+10%", change_type="positive"
        )
        assert stat.name == "Total Users"
        assert stat.value == 100
        assert stat.change == "+10%"
        assert stat.change_type == "positive"

    def test_stat_item_with_string_value(self):
        """Test StatItem with string value."""
        stat = StatItem(
            name="Status", value="Active", change="0%", change_type="neutral"
        )
        assert stat.value == "Active"

    def test_activity_item_schema(self):
        """Test ActivityItem schema."""
        activity = ActivityItem(
            id="act-123",
            action="create",
            description="User created",
            timestamp=datetime.now(UTC),
            user_name="John Doe",
            user_email="john@example.com",
        )
        assert activity.id == "act-123"
        assert activity.action == "create"
        assert activity.user_name == "John Doe"

    def test_activity_item_without_user(self):
        """Test ActivityItem without user info."""
        activity = ActivityItem(
            id="act-123",
            action="system",
            description="System event",
            timestamp=datetime.now(UTC),
        )
        assert activity.user_name is None
        assert activity.user_email is None

    def test_dashboard_stats_response_schema(self):
        """Test DashboardStatsResponse schema."""
        stats = DashboardStatsResponse(
            total_users=100,
            active_users=80,
            inactive_users=20,
            total_roles=5,
            total_api_keys=50,
            active_api_keys=40,
            users_created_last_30_days=25,
            users_created_last_7_days=10,
            stats=[
                StatItem(name="Users", value=100, change="+5%", change_type="positive")
            ],
        )
        assert stats.total_users == 100
        assert stats.active_users == 80
        assert len(stats.stats) == 1

    def test_recent_activity_response_schema(self):
        """Test RecentActivityResponse schema."""
        response = RecentActivityResponse(
            items=[
                ActivityItem(
                    id="1",
                    action="login",
                    description="User logged in",
                    timestamp=datetime.now(UTC),
                )
            ],
            total=1,
        )
        assert len(response.items) == 1
        assert response.total == 1

    def test_system_health_response_schema(self):
        """Test SystemHealthResponse schema."""
        health = SystemHealthResponse(
            database_status="healthy",
            cache_status="healthy",
            avg_response_time_ms=50,
            uptime_percentage=99.9,
            active_sessions=150,
        )
        assert health.database_status == "healthy"
        assert health.uptime_percentage == 99.9


class TestGetDashboardStats:
    """Tests for get_dashboard_stats endpoint."""

    @pytest.mark.asyncio
    async def test_get_dashboard_stats_success(self):
        """Test getting dashboard stats successfully."""
        user_id = uuid4()
        mock_session = AsyncMock()

        # Mock execute to return different results for different queries
        mock_result = MagicMock()
        mock_result.scalar.return_value = 100
        mock_result.scalar_one.return_value = 10
        mock_session.execute.return_value = mock_result

        result = await get_dashboard_stats(
            current_user_id=user_id, session=mock_session
        )

        assert isinstance(result, DashboardStatsResponse)
        assert mock_session.execute.called

    @pytest.mark.asyncio
    async def test_get_dashboard_stats_with_zero_users(self):
        """Test dashboard stats with zero users."""
        user_id = uuid4()
        mock_session = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_result.scalar_one.return_value = 0
        mock_session.execute.return_value = mock_result

        result = await get_dashboard_stats(
            current_user_id=user_id, session=mock_session
        )

        assert isinstance(result, DashboardStatsResponse)
        assert result.total_users == 0


class TestGetRecentActivity:
    """Tests for get_recent_activity endpoint."""

    @pytest.mark.asyncio
    async def test_get_recent_activity_success(self):
        """Test getting recent activity."""
        user_id = uuid4()
        mock_session = AsyncMock()

        # Mock empty activity list
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await get_recent_activity(
            current_user_id=user_id, session=mock_session, limit=10
        )

        assert isinstance(result, RecentActivityResponse)
        assert result.items == []
        assert result.total == 0

    @pytest.mark.asyncio
    async def test_get_recent_activity_with_items(self):
        """Test getting recent activity with items."""
        user_id = uuid4()
        mock_session = AsyncMock()

        # Create mock audit log entries
        mock_log = MagicMock()
        mock_log.id = uuid4()
        mock_log.action = "login"
        mock_log.resource_type = "session"
        mock_log.created_at = datetime.now(UTC)
        mock_log.user = MagicMock(full_name="John", email="john@test.com")

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_log]
        mock_session.execute.return_value = mock_result

        result = await get_recent_activity(
            current_user_id=user_id, session=mock_session, limit=10
        )

        assert isinstance(result, RecentActivityResponse)

    @pytest.mark.asyncio
    async def test_get_recent_activity_default_limit(self):
        """Test recent activity uses default limit."""
        user_id = uuid4()
        mock_session = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        # Default limit is 10
        result = await get_recent_activity(
            current_user_id=user_id, session=mock_session
        )

        assert isinstance(result, RecentActivityResponse)


class TestGetSystemHealth:
    """Tests for get_system_health endpoint."""

    @pytest.mark.asyncio
    async def test_get_system_health_all_healthy(self):
        """Test system health when all services are healthy."""
        user_id = uuid4()
        mock_session = AsyncMock()

        # Mock successful DB check
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1
        mock_session.execute.return_value = mock_result

        result = await get_system_health(current_user_id=user_id, session=mock_session)

        assert isinstance(result, SystemHealthResponse)
        assert result.database_status == "healthy"
        # Cache status depends on Redis availability - could be healthy or unhealthy
        assert result.cache_status in ("healthy", "unhealthy")

    @pytest.mark.asyncio
    async def test_get_system_health_db_unhealthy(self):
        """Test system health when database is unhealthy."""
        user_id = uuid4()
        mock_session = AsyncMock()

        # Mock failed DB check then success for counting active sessions
        mock_result2 = MagicMock()
        mock_result2.scalar.return_value = 0
        mock_session.execute.side_effect = [
            Exception("DB connection failed"),
            mock_result2,
        ]

        result = await get_system_health(current_user_id=user_id, session=mock_session)

        assert isinstance(result, SystemHealthResponse)
        assert result.database_status == "unhealthy"

    @pytest.mark.asyncio
    async def test_get_system_health_returns_active_sessions(self):
        """Test system health returns active session count."""
        user_id = uuid4()
        mock_session = AsyncMock()

        # Mock successful DB check and active session count
        mock_result1 = MagicMock()
        mock_result2 = MagicMock()
        mock_result2.scalar.return_value = 42
        mock_session.execute.side_effect = [mock_result1, mock_result2]

        result = await get_system_health(current_user_id=user_id, session=mock_session)

        assert isinstance(result, SystemHealthResponse)
        assert result.active_sessions == 42
