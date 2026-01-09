# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for UptimeTracker.

Tests for uptime tracking, health check recording, and incident management.
"""

from __future__ import annotations

from datetime import datetime, timedelta, UTC
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.infrastructure.monitoring.uptime_tracker import UptimeTracker


class TestUptimeTrackerInit:
    """Tests for UptimeTracker initialization."""

    def test_tracker_creation(self) -> None:
        """Test tracker can be created."""
        tracker = UptimeTracker()
        
        assert tracker._redis_client is None
        assert tracker._local_check_count == 0
        assert tracker._local_success_count == 0
        assert tracker._start_time is not None

    def test_key_prefix(self) -> None:
        """Test key prefix constant."""
        assert UptimeTracker.KEY_PREFIX == "uptime:"

    def test_check_interval(self) -> None:
        """Test check interval constant."""
        assert UptimeTracker.CHECK_INTERVAL_SECONDS == 60

    def test_incident_ttl(self) -> None:
        """Test incident TTL constant."""
        assert UptimeTracker.INCIDENT_TTL_SECONDS == 7 * 24 * 60 * 60


class TestUptimeTrackerKeyBuilding:
    """Tests for Redis key building."""

    def test_key_method(self) -> None:
        """Test _key method builds correct Redis key."""
        tracker = UptimeTracker()
        
        assert tracker._key("start_time") == "uptime:start_time"
        assert tracker._key("last_ping") == "uptime:last_ping"
        assert tracker._key("check_count") == "uptime:check_count"


class TestUptimeTrackerInitialization:
    """Tests for uptime tracker initialization."""

    @pytest.mark.asyncio
    async def test_initialize_success(self) -> None:
        """Test successful initialization."""
        tracker = UptimeTracker()
        
        mock_redis = AsyncMock()
        mock_redis.exists.return_value = False
        mock_redis.set.return_value = True
        mock_redis.setnx.return_value = True
        
        with patch.object(tracker, "_get_redis_client", return_value=mock_redis):
            await tracker.initialize()
            
            # Should set start_time if not exists
            mock_redis.exists.assert_called_once()
            mock_redis.set.assert_called_once()
            
            # Should initialize counters
            assert mock_redis.setnx.call_count >= 2

    @pytest.mark.asyncio
    async def test_initialize_already_initialized(self) -> None:
        """Test initialization when already initialized."""
        tracker = UptimeTracker()
        
        mock_redis = AsyncMock()
        mock_redis.exists.return_value = True  # Already exists
        
        with patch.object(tracker, "_get_redis_client", return_value=mock_redis):
            await tracker.initialize()
            
            # Should not set start_time if exists
            mock_redis.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_initialize_redis_failure(self) -> None:
        """Test initialization handles Redis failure gracefully."""
        tracker = UptimeTracker()
        
        mock_redis = AsyncMock()
        mock_redis.exists.side_effect = Exception("Redis unavailable")
        
        with patch.object(tracker, "_get_redis_client", return_value=mock_redis):
            # Should not raise exception
            await tracker.initialize()


class TestRecordPing:
    """Tests for recording health check pings."""

    @pytest.mark.asyncio
    async def test_record_healthy_ping(self) -> None:
        """Test recording a healthy ping."""
        tracker = UptimeTracker()
        
        mock_redis = AsyncMock()
        
        with patch.object(tracker, "_get_redis_client", return_value=mock_redis):
            await tracker.record_ping(is_healthy=True)
            
            # Should increment both counters
            assert mock_redis.incr.call_count == 2
            assert tracker._local_check_count == 1
            assert tracker._local_success_count == 1
            
            # Should update last_ping
            mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_unhealthy_ping(self) -> None:
        """Test recording an unhealthy ping."""
        tracker = UptimeTracker()
        
        mock_redis = AsyncMock()
        
        with patch.object(tracker, "_get_redis_client", return_value=mock_redis):
            await tracker.record_ping(is_healthy=False)
            
            # Should increment check_count but not success_count
            assert mock_redis.incr.call_count == 1
            assert tracker._local_check_count == 1
            assert tracker._local_success_count == 0
            
            # Should record incident
            mock_redis.lpush.assert_called_once()
            mock_redis.ltrim.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_ping_updates_timestamp(self) -> None:
        """Test that ping records current timestamp."""
        tracker = UptimeTracker()
        
        mock_redis = AsyncMock()
        
        with patch.object(tracker, "_get_redis_client", return_value=mock_redis):
            before = datetime.now(UTC)
            await tracker.record_ping(is_healthy=True)
            after = datetime.now(UTC)
            
            # Should set last_ping with current time
            call_args = mock_redis.set.call_args
            assert call_args[0][0] == "uptime:last_ping"
            
            # Timestamp should be between before and after
            timestamp_str = call_args[0][1]
            timestamp = datetime.fromisoformat(timestamp_str)
            assert before <= timestamp <= after

    @pytest.mark.asyncio
    async def test_record_ping_redis_failure(self) -> None:
        """Test record_ping handles Redis failure gracefully."""
        tracker = UptimeTracker()
        
        mock_redis = AsyncMock()
        mock_redis.incr.side_effect = Exception("Redis error")
        
        with patch.object(tracker, "_get_redis_client", return_value=mock_redis):
            # Should not raise exception
            await tracker.record_ping(is_healthy=True)
            
            # Local counters should still be updated
            assert tracker._local_check_count == 1
            assert tracker._local_success_count == 1

    @pytest.mark.asyncio
    async def test_record_multiple_pings(self) -> None:
        """Test recording multiple pings."""
        tracker = UptimeTracker()
        
        mock_redis = AsyncMock()
        
        with patch.object(tracker, "_get_redis_client", return_value=mock_redis):
            await tracker.record_ping(is_healthy=True)
            await tracker.record_ping(is_healthy=True)
            await tracker.record_ping(is_healthy=False)
            
            assert tracker._local_check_count == 3
            assert tracker._local_success_count == 2


class TestGetUptimePercentage:
    """Tests for uptime percentage calculation."""

    @pytest.mark.asyncio
    async def test_uptime_percentage_100_percent(self) -> None:
        """Test 100% uptime calculation."""
        tracker = UptimeTracker()
        
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = ["100", "100"]  # check_count, success_count
        
        with patch.object(tracker, "_get_redis_client", return_value=mock_redis):
            uptime = await tracker.get_uptime_percentage()
            
            assert uptime == 100.0

    @pytest.mark.asyncio
    async def test_uptime_percentage_partial(self) -> None:
        """Test partial uptime calculation."""
        tracker = UptimeTracker()
        
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = ["100", "95"]  # 95 successes out of 100
        
        with patch.object(tracker, "_get_redis_client", return_value=mock_redis):
            uptime = await tracker.get_uptime_percentage()
            
            assert uptime == 95.0

    @pytest.mark.asyncio
    async def test_uptime_percentage_no_checks(self) -> None:
        """Test uptime with no health checks."""
        tracker = UptimeTracker()
        
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = ["0", "0"]  # No checks yet
        
        with patch.object(tracker, "_get_redis_client", return_value=mock_redis):
            uptime = await tracker.get_uptime_percentage()
            
            # Should return 100% when no checks (benefit of doubt)
            assert uptime == 100.0

    @pytest.mark.asyncio
    async def test_uptime_percentage_redis_failure(self) -> None:
        """Test uptime calculation handles Redis failure."""
        tracker = UptimeTracker()
        
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = Exception("Redis error")
        
        with patch.object(tracker, "_get_redis_client", return_value=mock_redis):
            uptime = await tracker.get_uptime_percentage()
            
            # Should return 100.0 on error (fallback when no checks yet)
            assert uptime == 100.0


class TestGetRedisClient:
    """Tests for Redis client management."""

    @pytest.mark.asyncio
    async def test_get_redis_client_creates_client(self) -> None:
        """Test that _get_redis_client creates client."""
        tracker = UptimeTracker()
        
        with patch("app.infrastructure.monitoring.uptime_tracker.redis.Redis") as mock_redis_class:
            mock_client = AsyncMock()
            mock_redis_class.return_value = mock_client
            
            client = await tracker._get_redis_client()
            
            assert client == mock_client
            mock_redis_class.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_redis_client_reuses_client(self) -> None:
        """Test that _get_redis_client reuses existing client."""
        tracker = UptimeTracker()
        
        with patch("app.infrastructure.monitoring.uptime_tracker.redis.Redis") as mock_redis_class:
            mock_client = AsyncMock()
            mock_redis_class.return_value = mock_client
            
            client1 = await tracker._get_redis_client()
            client2 = await tracker._get_redis_client()
            
            assert client1 is client2
            # Should only create once
            mock_redis_class.assert_called_once()


class TestIncidentRecording:
    """Tests for incident recording."""

    @pytest.mark.asyncio
    async def test_unhealthy_ping_creates_incident(self) -> None:
        """Test that unhealthy ping creates an incident."""
        tracker = UptimeTracker()
        
        mock_redis = AsyncMock()
        
        with patch.object(tracker, "_get_redis_client", return_value=mock_redis):
            await tracker.record_ping(is_healthy=False)
            
            # Should push incident to list
            mock_redis.lpush.assert_called_once()
            
            # Should trim old incidents
            mock_redis.ltrim.assert_called_once()
            trim_args = mock_redis.ltrim.call_args[0]
            assert trim_args[0] == "uptime:incidents"
            assert trim_args[1] == 0
            assert trim_args[2] == 999  # Keep last 1000

    @pytest.mark.asyncio
    async def test_healthy_ping_no_incident(self) -> None:
        """Test that healthy ping doesn't create incident."""
        tracker = UptimeTracker()
        
        mock_redis = AsyncMock()
        
        with patch.object(tracker, "_get_redis_client", return_value=mock_redis):
            await tracker.record_ping(is_healthy=True)
            
            # Should not push incident
            mock_redis.lpush.assert_not_called()


class TestUptimeDuration:
    """Tests for uptime duration tracking."""

    @pytest.mark.asyncio
    async def test_get_uptime_duration_from_redis(self) -> None:
        """Test getting uptime duration from Redis."""
        tracker = UptimeTracker()
        
        # Mock start time 1 hour ago
        start_time = datetime.now(UTC) - timedelta(hours=1)
        
        mock_redis = AsyncMock()
        mock_redis.get.return_value = start_time.isoformat()
        
        with patch.object(tracker, "_get_redis_client", return_value=mock_redis):
            duration = await tracker.get_uptime_duration()
            
            # Should be approximately 1 hour
            assert duration.total_seconds() >= 3599
            assert duration.total_seconds() <= 3601

    @pytest.mark.asyncio
    async def test_get_uptime_duration_fallback(self) -> None:
        """Test uptime duration fallback to local time."""
        tracker = UptimeTracker()
        
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        
        with patch.object(tracker, "_get_redis_client", return_value=mock_redis):
            duration = await tracker.get_uptime_duration()
            
            # Should use local start time (very recent)
            assert duration.total_seconds() < 5

    @pytest.mark.asyncio
    async def test_get_uptime_duration_redis_error(self) -> None:
        """Test uptime duration when Redis fails."""
        tracker = UptimeTracker()
        
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = Exception("Redis error")
        
        with patch.object(tracker, "_get_redis_client", return_value=mock_redis):
            duration = await tracker.get_uptime_duration()
            
            # Should fall back to local start time
            assert duration.total_seconds() < 5


class TestLastPing:
    """Tests for last ping tracking."""

    @pytest.mark.asyncio
    async def test_get_last_ping_success(self) -> None:
        """Test getting last ping timestamp."""
        tracker = UptimeTracker()
        
        last_ping_time = datetime.now(UTC)
        
        mock_redis = AsyncMock()
        mock_redis.get.return_value = last_ping_time.isoformat()
        
        with patch.object(tracker, "_get_redis_client", return_value=mock_redis):
            last_ping = await tracker.get_last_ping()
            
            assert last_ping is not None
            assert abs((last_ping - last_ping_time).total_seconds()) < 1

    @pytest.mark.asyncio
    async def test_get_last_ping_none(self) -> None:
        """Test get last ping when no ping recorded."""
        tracker = UptimeTracker()
        
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        
        with patch.object(tracker, "_get_redis_client", return_value=mock_redis):
            last_ping = await tracker.get_last_ping()
            
            assert last_ping is None

    @pytest.mark.asyncio
    async def test_get_last_ping_redis_error(self) -> None:
        """Test get last ping when Redis fails."""
        tracker = UptimeTracker()
        
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = Exception("Redis error")
        
        with patch.object(tracker, "_get_redis_client", return_value=mock_redis):
            last_ping = await tracker.get_last_ping()
            
            assert last_ping is None


class TestRecentIncidents:
    """Tests for incident retrieval."""

    @pytest.mark.asyncio
    async def test_get_recent_incidents_success(self) -> None:
        """Test getting recent incidents."""
        tracker = UptimeTracker()
        
        incidents = [
            "{'timestamp': '2025-01-01T00:00:00Z', 'duration': 60}",
            "{'timestamp': '2025-01-02T00:00:00Z', 'duration': 120}",
        ]
        
        mock_redis = AsyncMock()
        mock_redis.lrange.return_value = incidents
        
        with patch.object(tracker, "_get_redis_client", return_value=mock_redis):
            result = await tracker.get_recent_incidents(limit=5)
            
            assert len(result) == 2
            assert result[0]["duration"] == 60
            assert result[1]["duration"] == 120
            
            # Check Redis was called with correct params
            mock_redis.lrange.assert_called_once_with("uptime:incidents", 0, 4)

    @pytest.mark.asyncio
    async def test_get_recent_incidents_empty(self) -> None:
        """Test getting incidents when none exist."""
        tracker = UptimeTracker()
        
        mock_redis = AsyncMock()
        mock_redis.lrange.return_value = []
        
        with patch.object(tracker, "_get_redis_client", return_value=mock_redis):
            result = await tracker.get_recent_incidents()
            
            assert result == []

    @pytest.mark.asyncio
    async def test_get_recent_incidents_redis_error(self) -> None:
        """Test getting incidents when Redis fails."""
        tracker = UptimeTracker()
        
        mock_redis = AsyncMock()
        mock_redis.lrange.side_effect = Exception("Redis error")
        
        with patch.object(tracker, "_get_redis_client", return_value=mock_redis):
            result = await tracker.get_recent_incidents()
            
            assert result == []


class TestGetStats:
    """Tests for comprehensive stats."""

    @pytest.mark.asyncio
    async def test_get_stats_complete(self) -> None:
        """Test getting complete uptime statistics."""
        tracker = UptimeTracker()
        tracker._local_check_count = 100
        
        last_ping_time = datetime.now(UTC)
        start_time = datetime.now(UTC) - timedelta(hours=2)
        
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = [
            "100",  # check_count
            "95",   # success_count
            start_time.isoformat(),  # start_time
            last_ping_time.isoformat(),  # last_ping
        ]
        mock_redis.lrange.return_value = []
        
        with patch.object(tracker, "_get_redis_client", return_value=mock_redis):
            stats = await tracker.get_stats()
            
            assert "uptime_percentage" in stats
            assert stats["uptime_percentage"] == 95.0
            assert "uptime_duration_seconds" in stats
            assert stats["uptime_duration_seconds"] >= 7199
            assert "uptime_duration_human" in stats
            assert "last_ping" in stats
            assert stats["last_ping"] is not None
            assert "recent_incidents" in stats
            assert stats["recent_incidents"] == []
            assert stats["total_checks"] == 100


class TestGetUptimeTrackerSingleton:
    """Tests for singleton pattern."""

    def test_get_uptime_tracker_singleton(self) -> None:
        """Test that get_uptime_tracker returns same instance."""
        from app.infrastructure.monitoring.uptime_tracker import (
            get_uptime_tracker,
            _uptime_tracker,
        )
        
        # Reset singleton
        import app.infrastructure.monitoring.uptime_tracker as module
        module._uptime_tracker = None
        
        # Get first instance
        tracker1 = get_uptime_tracker()
        
        # Get second instance
        tracker2 = get_uptime_tracker()
        
        # Should be same instance
        assert tracker1 is tracker2
