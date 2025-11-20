from __future__ import annotations

from typing import Optional

import requests
from bs4 import BeautifulSoup
from langchain.tools import tool

AGENT_UA = "langgraph-agent/1.0"
DEFAULT_MAX_CHARS = 2000


def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator=" ", strip=True)


@tool("web_crawl")
def web_crawl(url: str, max_chars: Optional[int] = None) -> dict:
    """Fetch a URL and return a trimmed readable excerpt."""
    headers = {"User-Agent": AGENT_UA}
    try:
        response = requests.get(str(url), headers=headers, timeout=60)
        response.raise_for_status()
    except requests.HTTPError:
        return {"error": True, "message": f"HTTP {response.status_code}"}
    except requests.RequestException as exc:
        return {"error": True, "message": str(exc)}

    text = _extract_text(response.text)
    limit = max_chars or DEFAULT_MAX_CHARS
    return {
        "error": False,
        "url": str(url),
        "content_length": len(text),
        "excerpt": text[:limit],
    }


__all__ = ["web_crawl"]
