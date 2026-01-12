# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""User session domain entity."""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from uuid import UUID

from app.domain.entities.base import TenantEntity


@dataclass
class UserSession(TenantEntity):
    """
    User session domain entity.
    
    Represents an active user session for session management.
    Allows users to view and revoke their active sessions.
    """
    
    user_id: UUID = field(default_factory=lambda: UUID(int=0))
    
    # Session identification
    refresh_token_hash: str = ""  # Hashed refresh token for identification
    
    # Device information
    device_name: str = ""  # e.g., "Chrome on Windows"
    device_type: str = ""  # e.g., "desktop", "mobile", "tablet"
    browser: str = ""      # e.g., "Chrome 120"
    os: str = ""           # e.g., "Windows 11"
    
    # Location information
    ip_address: str = ""
    location: str = ""     # e.g., "Santiago, Chile" (from IP geolocation)
    
    # Activity tracking
    last_activity: datetime = field(default_factory=lambda: datetime.now(UTC))
    
    # Session status
    is_current: bool = False  # True if this is the session making the request
    is_revoked: bool = False
    revoked_at: datetime | None = None
    
    def revoke(self) -> None:
        """Revoke this session."""
        self.is_revoked = True
        self.revoked_at = datetime.now(UTC)
    
    def update_activity(self, ip_address: str | None = None) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now(UTC)
        if ip_address:
            self.ip_address = ip_address
    
    @property
    def is_active(self) -> bool:
        """Check if session is still active (not revoked)."""
        return not self.is_revoked
    
    @classmethod
    def parse_user_agent(cls, user_agent: str) -> dict:
        """
        Parse user agent string to extract device info.
        
        Returns dict with device_name, device_type, browser, os.
        """
        # Simple parsing - in production use a library like user-agents
        device_type = "desktop"
        browser = "Unknown"
        os = "Unknown"
        
        user_agent_lower = user_agent.lower()
        
        # Detect OS
        if "windows" in user_agent_lower:
            os = "Windows"
        elif "mac os" in user_agent_lower or "macos" in user_agent_lower:
            os = "macOS"
        elif "linux" in user_agent_lower:
            os = "Linux"
        elif "android" in user_agent_lower:
            os = "Android"
            device_type = "mobile"
        elif "iphone" in user_agent_lower:
            os = "iOS"
            device_type = "mobile"
        elif "ipad" in user_agent_lower:
            os = "iOS"
            device_type = "tablet"
        
        # Detect Browser
        if "edg/" in user_agent_lower:
            browser = "Edge"
        elif "chrome" in user_agent_lower:
            browser = "Chrome"
        elif "firefox" in user_agent_lower:
            browser = "Firefox"
        elif "safari" in user_agent_lower:
            browser = "Safari"
        
        device_name = f"{browser} on {os}"
        
        return {
            "device_name": device_name,
            "device_type": device_type,
            "browser": browser,
            "os": os,
        }
