# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Uptime tracking service.

Tracks application uptime using Redis for persistence across restarts.
"""

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import redis.asyncio as redis

from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)

# Global uptime tracker instance
_uptime_tracker: "UptimeTracker | None" = None


class UptimeTracker:
    """
    Tracks application uptime with Redis persistence.

    Features:
    - Records health check pings
    - Calculates uptime percentage
    - Tracks downtime incidents
    - Persists across application restarts

    Storage keys in Redis:
    - uptime:start_time - Application start timestamp
    - uptime:last_ping - Last successful health check
    - uptime:check_count - Total health checks
    - uptime:success_count - Successful health checks
    - uptime:incidents - List of downtime incidents
    """

    # Keys prefix
    KEY_PREFIX = "uptime:"

    # Health check interval (expected seconds between checks)
    CHECK_INTERVAL_SECONDS = 60

    # How long to keep incident history (7 days)
    INCIDENT_TTL_SECONDS = 7 * 24 * 60 * 60

    def __init__(self) -> None:
        self._redis_client: redis.Redis | None = None
        self._start_time: datetime = datetime.now(UTC)
        self._local_check_count = 0
        self._local_success_count = 0

    async def _get_redis_client(self) -> redis.Redis:
        """Get Redis client from shared cache."""
        if self._redis_client is None:
            from app.infrastructure.cache import get_cache

            cache = get_cache()
            self._redis_client = cache.get_redis_client()
        return self._redis_client

    def _key(self, name: str) -> str:
        """Build Redis key with prefix."""
        return f"{self.KEY_PREFIX}{name}"

    async def initialize(self) -> None:
        """
        Initialize uptime tracking.

        Should be called on application startup.
        """
        try:
            client = await self._get_redis_client()

            # Set start time if not exists
            start_key = self._key("start_time")
            if not await client.exists(start_key):
                await client.set(start_key, self._start_time.isoformat())

            # Initialize counters if not exists
            await client.setnx(self._key("check_count"), 0)
            await client.setnx(self._key("success_count"), 0)

            logger.info("uptime_tracker_initialized")

        except Exception as e:
            logger.warning("uptime_tracker_init_failed", error=type(e).__name__)

    async def record_ping(self, is_healthy: bool) -> None:
        """
        Record a health check ping.

        Args:
            is_healthy: Whether the health check passed
        """
        now = datetime.now(UTC)
        self._local_check_count += 1

        if is_healthy:
            self._local_success_count += 1

        try:
            client = await self._get_redis_client()

            # Increment counters
            await client.incr(self._key("check_count"))
            if is_healthy:
                await client.incr(self._key("success_count"))

            # Update last ping
            await client.set(self._key("last_ping"), now.isoformat())

            # Record incident if unhealthy
            if not is_healthy:
                incident = {
                    "timestamp": now.isoformat(),
                    "type": "health_check_failed",
                }
                await client.lpush(
                    self._key("incidents"),
                    json.dumps(incident),
                )
                # Trim old incidents
                await client.ltrim(
                    self._key("incidents"),
                    0,
                    999,  # Keep last 1000 incidents
                )

        except Exception as e:
            logger.warning("uptime_record_ping_failed", error=type(e).__name__)

    async def get_uptime_percentage(self) -> float:
        """
        Calculate uptime percentage.

        Returns:
            Uptime percentage (0-100)
        """
        try:
            client = await self._get_redis_client()

            check_count = await client.get(self._key("check_count"))
            success_count = await client.get(self._key("success_count"))

            if check_count and success_count:
                total = int(check_count)
                success = int(success_count)

                if total > 0:
                    return round((success / total) * 100, 2)

            # Fallback to local counters
            if self._local_check_count > 0:
                return round(
                    (self._local_success_count / self._local_check_count) * 100,
                    2,
                )

            return 100.0  # No checks yet, assume healthy

        except Exception as e:
            logger.warning("uptime_percentage_failed", error=type(e).__name__)

            # Fallback to local counters
            if self._local_check_count > 0:
                return round(
                    (self._local_success_count / self._local_check_count) * 100,
                    2,
                )
            return 100.0

    async def get_uptime_duration(self) -> timedelta:
        """
        Get total uptime duration since start.

        Returns:
            Timedelta of uptime duration
        """
        try:
            client = await self._get_redis_client()

            start_time_str = await client.get(self._key("start_time"))
            if start_time_str:
                start_time = datetime.fromisoformat(start_time_str)
                return datetime.now(UTC) - start_time

        except Exception as e:
            logger.warning("uptime_duration_failed", error=type(e).__name__)

        # Fallback to local start time
        return datetime.now(UTC) - self._start_time

    async def get_last_ping(self) -> datetime | None:
        """Get timestamp of last successful ping."""
        try:
            client = await self._get_redis_client()

            last_ping_str = await client.get(self._key("last_ping"))
            if last_ping_str:
                return datetime.fromisoformat(last_ping_str)

        except Exception as e:
            logger.warning("uptime_last_ping_failed", error=type(e).__name__)

        return None

    async def get_recent_incidents(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get recent downtime incidents.

        Args:
            limit: Maximum number of incidents to return (1-1000)

        Returns:
            List of incident dictionaries
        """
        limit = max(1, min(limit, 1000))
        try:
            client = await self._get_redis_client()

            incidents = await client.lrange(
                self._key("incidents"),
                0,
                limit - 1,
            )

            return [json.loads(incident) for incident in incidents]

        except Exception as e:
            logger.warning("uptime_recent_incidents_failed", error=type(e).__name__)
            return []

    async def get_stats(self) -> dict[str, Any]:
        """
        Get comprehensive uptime statistics.

        Returns:
            Dictionary with all uptime stats
        """
        uptime_pct = await self.get_uptime_percentage()
        duration = await self.get_uptime_duration()
        last_ping = await self.get_last_ping()
        incidents = await self.get_recent_incidents(5)

        return {
            "uptime_percentage": uptime_pct,
            "uptime_duration_seconds": int(duration.total_seconds()),
            "uptime_duration_human": str(duration),
            "last_ping": last_ping.isoformat() if last_ping else None,
            "recent_incidents": incidents,
            "total_checks": self._local_check_count,
        }


def get_uptime_tracker() -> UptimeTracker:
    """
    Get UptimeTracker singleton.

    Uses singleton pattern to ensure consistent tracking.
    """
    global _uptime_tracker

    if _uptime_tracker is None:
        _uptime_tracker = UptimeTracker()

    return _uptime_tracker
