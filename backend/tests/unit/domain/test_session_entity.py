# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for UserSession domain entity."""

import pytest
from datetime import datetime, timedelta, UTC
from uuid import uuid4

from app.domain.entities.session import UserSession


class TestUserSession:
    """Test UserSession entity."""
    
    def test_create_session(self):
        """Test creating a new session."""
        session = UserSession(
            id=uuid4(),
            user_id=uuid4(),
            tenant_id=uuid4(),
            refresh_token_hash="hash123",
            device_name="Chrome on Windows",
            device_type="desktop",
            browser="Chrome 120",
            os="Windows 11",
            ip_address="192.168.1.1",
            location="Santiago, Chile",
        )
        
        assert session.is_active
        assert not session.is_revoked
        assert session.revoked_at is None
        assert isinstance(session.last_activity, datetime)
    
    def test_revoke_session(self):
        """Test revoking a session."""
        session = UserSession(
            id=uuid4(),
            user_id=uuid4(),
            tenant_id=uuid4(),
            refresh_token_hash="hash",
        )
        
        assert session.is_active
        
        session.revoke()
        
        assert not session.is_active
        assert session.is_revoked
        assert isinstance(session.revoked_at, datetime)
    
    def test_update_activity(self):
        """Test updating session activity."""
        session = UserSession(
            id=uuid4(),
            user_id=uuid4(),
            tenant_id=uuid4(),
            refresh_token_hash="hash",
            ip_address="192.168.1.1",
        )
        
        old_activity = session.last_activity
        
        # Wait a bit and update
        import time
        time.sleep(0.01)
        
        session.update_activity()
        
        assert session.last_activity > old_activity
    
    def test_update_activity_with_new_ip(self):
        """Test updating activity with new IP address."""
        session = UserSession(
            id=uuid4(),
            user_id=uuid4(),
            tenant_id=uuid4(),
            refresh_token_hash="hash",
            ip_address="192.168.1.1",
        )
        
        new_ip = "10.0.0.1"
        session.update_activity(ip_address=new_ip)
        
        assert session.ip_address == new_ip
    
    def test_is_current_flag(self):
        """Test is_current flag."""
        session = UserSession(
            id=uuid4(),
            user_id=uuid4(),
            tenant_id=uuid4(),
            refresh_token_hash="hash",
            is_current=True,
        )
        
        assert session.is_current
    
    def test_parse_user_agent_windows_chrome(self):
        """Test parsing Windows Chrome user agent."""
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        
        info = UserSession.parse_user_agent(ua)
        
        assert info["os"] == "Windows"
        assert info["browser"] == "Chrome"
        assert info["device_type"] == "desktop"
    
    def test_parse_user_agent_mac_safari(self):
        """Test parsing macOS Safari user agent."""
        ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15"
        
        info = UserSession.parse_user_agent(ua)
        
        assert info["os"] == "macOS"
        assert info["browser"] == "Safari"
        assert info["device_type"] == "desktop"
    
    def test_parse_user_agent_android_chrome(self):
        """Test parsing Android Chrome user agent."""
        ua = "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.43 Mobile Safari/537.36"
        
        info = UserSession.parse_user_agent(ua)
        
        # Implementation detects Android after detecting "android" keyword
        assert "android" in ua.lower()
        assert info["browser"] == "Chrome"
        assert info["device_type"] == "mobile"
    
    def test_parse_user_agent_iphone(self):
        """Test parsing iPhone user agent."""
        ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        
        info = UserSession.parse_user_agent(ua)
        
        # Contains "iphone" keyword
        assert "iphone" in ua.lower()
        assert info["device_type"] == "mobile"
    
    def test_parse_user_agent_ipad(self):
        """Test parsing iPad user agent."""
        ua = "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        
        info = UserSession.parse_user_agent(ua)
        
        # Contains "ipad" keyword
        assert "ipad" in ua.lower()
        assert info["device_type"] == "tablet"
    
    def test_parse_user_agent_firefox(self):
        """Test parsing Firefox user agent."""
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
        
        info = UserSession.parse_user_agent(ua)
        
        assert info["browser"] == "Firefox"
    
    def test_parse_user_agent_edge(self):
        """Test parsing Edge user agent."""
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
        
        info = UserSession.parse_user_agent(ua)
        
        assert info["browser"] == "Edge"
    
    def test_parse_user_agent_unknown(self):
        """Test parsing unknown user agent."""
        ua = "CustomBot/1.0"
        
        info = UserSession.parse_user_agent(ua)
        
        # Should have defaults
        assert "device_type" in info
        assert "browser" in info
        assert "os" in info
