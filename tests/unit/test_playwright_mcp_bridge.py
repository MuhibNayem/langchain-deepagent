"""Unit tests for Playwright MCP Bridge."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestPlaywrightMCPBridge:
    """Tests for PlaywrightMCPBridge."""
    
    @pytest.fixture
    def bridge(self):
        """Create bridge instance for testing."""
        from luminamind.evaluator.playwright_mcp_bridge import PlaywrightMCPBridge
        return PlaywrightMCPBridge(headless=True)
    
    @pytest.mark.asyncio
    async def test_connect_creates_browser(self, bridge):
        """Test that connect() initializes browser."""
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        
        mock_pw_instance = MagicMock()
        mock_pw_instance.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_pw_instance.start = MagicMock(return_value=None)
        
        # async_playwright() returns an async context manager
        mock_async_pw = AsyncMock()
        mock_async_pw.__aenter__ = AsyncMock(return_value=mock_pw_instance)
        mock_async_pw.__aexit__ = AsyncMock(return_value=None)
        
        with patch("luminamind.evaluator.playwright_mcp_bridge.async_playwright", return_value=mock_async_pw):
            await bridge.connect()
            
            assert bridge._browser is not None
            assert bridge._context is not None
            assert bridge._page is not None
    
    @pytest.mark.asyncio
    async def test_disconnect_cleanup(self, bridge):
        """Test that disconnect() cleans up all resources."""
        bridge._browser = AsyncMock()
        bridge._context = AsyncMock()
        bridge._page = AsyncMock()
        bridge._playwright = AsyncMock()
        
        page_close_mock = bridge._page.close
        context_close_mock = bridge._context.close
        browser_close_mock = bridge._browser.close
        
        await bridge.disconnect()
        
        page_close_mock.assert_called_once()
        context_close_mock.assert_called_once()
        browser_close_mock.assert_called_once()
        assert bridge._browser is None
    
    @pytest.mark.asyncio
    async def test_screenshot_returns_bytes(self, bridge):
        """Test that screenshot() returns PNG bytes."""
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.screenshot = AsyncMock(return_value=b"fake-png-bytes")
        bridge._page = mock_page
        
        result = await bridge.screenshot("https://example.com")
        
        assert result == b"fake-png-bytes"
        mock_page.goto.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_user_flow(self, bridge):
        """Test user flow execution."""
        mock_page = AsyncMock()
        mock_page.click = AsyncMock()
        mock_page.fill = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.content = AsyncMock(return_value="<html>test</html>")
        bridge._page = mock_page
        
        flow = [
            {"action": "navigate", "selector": None, "value": "https://example.com"},
            {"action": "click", "selector": "#button", "value": None},
            {"action": "type", "selector": "#input", "value": "hello"},
        ]
        
        result = await bridge.execute_user_flow(flow)
        
        assert "steps" in result
        assert "dom_snapshot" in result
        assert len(result["steps"]) == 3
        assert all(step["status"] == "success" for step in result["steps"])
    
    @pytest.mark.asyncio
    async def test_screenshot_raises_if_not_connected(self, bridge):
        """Test that screenshot() raises RuntimeError if not connected."""
        bridge._page = None
        
        with pytest.raises(RuntimeError, match="Not connected"):
            await bridge.screenshot("https://example.com")
    
    @pytest.mark.asyncio
    async def test_user_flow_handles_errors(self, bridge):
        """Test that user flow continues on action error."""
        mock_page = AsyncMock()
        mock_page.click = AsyncMock(side_effect=Exception("Element not found"))
        mock_page.content = AsyncMock(return_value="<html>test</html>")
        bridge._page = mock_page
        
        flow = [
            {"action": "click", "selector": "#nonexistent", "value": None},
        ]
        
        result = await bridge.execute_user_flow(flow)
        
        assert len(result["steps"]) == 1
        assert result["steps"][0]["status"] == "error"
        assert "Element not found" in result["steps"][0]["error"]


class TestBrowserSessionManager:
    """Tests for BrowserSessionManager."""
    
    @pytest.fixture
    def manager(self):
        """Create manager for testing."""
        from luminamind.evaluator.session_manager import BrowserSessionManager
        return BrowserSessionManager(ttl_seconds=60.0, max_sessions=3)
    
    @pytest.mark.asyncio
    async def test_acquire_creates_new_session(self, manager):
        """Test that acquire() creates a new session."""
        with patch("luminamind.evaluator.session_manager.PlaywrightMCPBridge") as MockBridge:
            mock_bridge = AsyncMock()
            mock_bridge.connect = AsyncMock()
            MockBridge.return_value = mock_bridge
            
            async with manager.acquire("test-session") as session:
                assert session is not None
                assert session.bridge is mock_bridge
    
    @pytest.mark.asyncio
    async def test_session_reuse_within_ttl(self, manager):
        """Test that session is reused within TTL."""
        with patch("luminamind.evaluator.session_manager.PlaywrightMCPBridge") as MockBridge:
            mock_bridge = AsyncMock()
            mock_bridge.connect = AsyncMock()
            MockBridge.return_value = mock_bridge
            
            # First acquire
            async with manager.acquire("reuse-session") as session1:
                pass
            
            # Second acquire same ID - should reuse
            async with manager.acquire("reuse-session") as session2:
                assert session1 is session2  # Same object
    
    @pytest.mark.asyncio
    async def test_max_sessions_eviction(self, manager):
        """Test that exceeding max_sessions evicts oldest."""
        with patch("luminamind.evaluator.session_manager.PlaywrightMCPBridge") as MockBridge:
            mock_bridge = AsyncMock()
            mock_bridge.connect = AsyncMock()
            mock_bridge.disconnect = AsyncMock()
            MockBridge.return_value = mock_bridge
            
            # Create max_sessions sessions
            for i in range(3):
                async with manager.acquire(f"session-{i}") as session:
                    pass
            
            # Next session should evict oldest
            async with manager.acquire("session-3") as session:
                assert len(manager._sessions) == 3
    
    @pytest.mark.asyncio
    async def test_acquire_without_id_creates_new_session(self, manager):
        """Test that acquire() without session_id creates new session with auto-generated ID."""
        with patch("luminamind.evaluator.session_manager.PlaywrightMCPBridge") as MockBridge:
            mock_bridge = AsyncMock()
            mock_bridge.connect = AsyncMock()
            MockBridge.return_value = mock_bridge
            
            async with manager.acquire() as session:
                assert session is not None
                assert session.bridge is mock_bridge
