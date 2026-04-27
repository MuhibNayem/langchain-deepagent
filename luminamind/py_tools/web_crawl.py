"""Production-grade web_crawl tool.

Fetches URLs and extracts readable text content, stripping scripts, styles,
and other non-content elements. Supports max_chars truncation.
"""
from __future__ import annotations

import requests
from bs4 import BeautifulSoup
from langchain.tools import tool

from ..observability.metrics import monitor_tool
from ..utils.http_client import DEFAULT_TIMEOUT_SECONDS


def _extract_text(html: str) -> str:
    """Extract readable text from HTML, stripping scripts, styles, and whitespace.

    Args:
        html: Raw HTML string

    Returns:
        Cleaned text content with scripts/styles removed, HTML entities decoded
    """
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")

    # Remove script and style elements
    for tag in soup(["script", "style", "noscript", "iframe", "object", "embed"]):
        tag.decompose()

    # Get text content
    text = soup.get_text(separator="\n", strip=True)

    # Normalize whitespace
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return "\n".join(lines)


@tool("web_crawl")
@monitor_tool
def web_crawl(url: str, max_chars: int | None = None) -> dict:
    """Fetch a URL and extract readable text content.

    Args:
        url: The URL to crawl
        max_chars: Maximum characters to return (truncates excerpt if set)

    Returns:
        dict with error status, url, excerpt (cleaned text), content_length
    """
    try:
        response = requests.get(url, timeout=DEFAULT_TIMEOUT_SECONDS, allow_redirects=True)
        response.raise_for_status()
    except requests.HTTPError as exc:
        status_code = getattr(getattr(exc, "response", None), "status_code", None) or getattr(response, "status_code", "unknown")
        return {"error": True, "url": url, "message": f"HTTP {status_code}"}
    except requests.RequestException as exc:
        return {"error": True, "url": url, "message": str(exc)}

    excerpt_full = _extract_text(response.text)
    content_length = len(excerpt_full)
    excerpt = excerpt_full

    if max_chars is not None and len(excerpt) > max_chars:
        excerpt = excerpt[:max_chars]

    return {
        "error": False,
        "url": url,
        "excerpt": excerpt,
        "content_length": content_length,
    }


__all__ = ["web_crawl", "_extract_text"]
