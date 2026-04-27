"""Playwright MCP Bridge for browser automation and UI verification."""
import asyncio
import base64
from dataclasses import dataclass, field
from typing import Any, Protocol
from pathlib import Path

import aiohttp
from playwright.async_api import async_playwright, Browser, Page, BrowserContext


class PlaywrightMCPBridge:
    """Bridge to Playwright MCP for browser automation.
    
    Connects to Playwright MCP server via HTTP/WebSocket to enable:
    - Screenshot capture
    - User flow simulation
    - DOM inspection
    """
    
    def __init__(
        self,
        mcp_server_url: str = "http://localhost:9222",
        headless: bool = True,
        viewport: tuple[int, int] = (1280, 720),
    ):
        self.mcp_server_url = mcp_server_url
        self.headless = headless
        self.viewport = viewport
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._playwright = None
    
    async def connect(self) -> None:
        """Connect to browser via Playwright."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        self._context = await self._browser.new_context(
            viewport={"width": self.viewport[0], "height": self.viewport[1]},
        )
        self._page = await self._context.new_page()
    
    async def disconnect(self) -> None:
        """Disconnect and cleanup browser."""
        if self._page:
            await self._page.close()
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._browser = None
        self._context = None
        self._page = None
        self._playwright = None
    
    async def screenshot(self, url: str, full_page: bool = False) -> bytes:
        """Capture screenshot of URL.
        
        Args:
            url: Target URL to navigate and screenshot
            full_page: If True, capture entire scrollable page
            
        Returns:
            PNG image bytes
        """
        if not self._page:
            raise RuntimeError("Not connected. Call connect() first.")
        
        await self._page.goto(url, wait_until="networkidle")
        await asyncio.sleep(0.5)  # Allow dynamic content to render
        
        screenshot_bytes = await self._page.screenshot(full_page=full_page)
        return screenshot_bytes
    
    async def execute_user_flow(self, flow: list[dict[str, Any]]) -> dict[str, Any]:
        """Execute a user flow simulation.
        
        Args:
            flow: List of actions [{"action": "click", "selector": "...", "value": "..."}]
            
        Returns:
            Dict with results for each action and final DOM snapshot
        """
        if not self._page:
            raise RuntimeError("Not connected. Call connect() first.")
        
        results = []
        for step in flow:
            action = step.get("action")
            selector = step.get("selector")
            value = step.get("value")
            
            try:
                if action == "click":
                    await self._page.click(selector)
                elif action == "type":
                    await self._page.fill(selector, str(value))
                elif action == "navigate":
                    await self._page.goto(value, wait_until="networkidle")
                elif action == "hover":
                    await self._page.hover(selector)
                elif action == "wait":
                    await asyncio.sleep(float(value or 0.5))
                
                results.append({"action": action, "selector": selector, "status": "success"})
            except Exception as e:
                results.append({"action": action, "selector": selector, "status": "error", "error": str(e)})
        
        # Get final DOM snapshot
        dom_snapshot = await self._page.content()
        return {"steps": results, "dom_snapshot": dom_snapshot}
    
    async def get_dom_state(self, selector: str | None = None) -> str:
        """Get current DOM state.
        
        Args:
            selector: Optional CSS selector to scope the snapshot
            
        Returns:
            HTML string of current page state
        """
        if not self._page:
            raise RuntimeError("Not connected. Call connect() first.")
        
        if selector:
            element = await self._page.query_selector(selector)
            if element:
                return await element.inner_html()
        
        return await self._page.content()


# Export for sandbox integration
__all__ = ["PlaywrightMCPBridge"]
