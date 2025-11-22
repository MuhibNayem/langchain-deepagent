from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Tuple
import ollama

import requests
from langchain.tools import tool

from ..config.env import load_project_env

load_project_env()

DEFAULT_LIMIT = 3

AGENT_UA = "langgraph-agent/1.0"
SERPER_API_KEY = os.environ.get("SERPER_API_KEY")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_SEARCH_API_KEY")
GOOGLE_CSE_ID = (
    os.environ.get("GOOGLE_CSE_ID")
    or os.environ.get("GOOGLE_CX")
    or os.environ.get("GOOGLE_CUSTOM_SEARCH_ID")
)
GOOGLE_REFERER = os.environ.get("GOOGLE_REFERER") or os.environ.get("GOOGLE_REFERRER")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST")
DEBUG = os.environ.get("DEBUG_WEB_SEARCH") == "1"


def _debug(message: str, payload: Optional[Any] = None) -> None:
    if not DEBUG:
        return
    print(f"[web_search] {message}")
    if payload is not None:
        print(payload)


def _prune_results(results: List[Dict[str, Any]], limit: Optional[int]) -> List[Dict[str, Any]]:
    capped = limit if (limit and limit > 0) else DEFAULT_LIMIT
    return results[: min(capped, 10)]


def _normalize_results(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized = []
    for item in items:
        title = item.get("title") or item.get("link") or item.get("url") or "(untitled)"
        url = item.get("link") or item.get("url")
        snippet = item.get("snippet") or item.get("text") or ""
        if url:
            normalized.append({"title": title, "url": url, "snippet": snippet})
    return normalized


def _search_google_cse(query: str, limit: Optional[int]) -> Dict[str, Any]:
    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        return {"skipped": True, "message": "GOOGLE_API_KEY/GOOGLE_CSE_ID not set"}

    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CSE_ID,
        "q": query,
        "c2coff": "1",
        "safe": "off",
    }
    if limit:
        params["num"] = str(min(limit, 3))

    headers = {"User-Agent": AGENT_UA}
    if GOOGLE_REFERER:
        headers["Referer"] = GOOGLE_REFERER

    url = "https://customsearch.googleapis.com/customsearch/v1"
    _debug("google_cse request", {"url": url, "params": params})
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.HTTPError:
        try:
            detail = response.json()
            _debug("google_cse error body", detail)
            extra = detail.get("error", {}).get("message")
        except Exception:
            extra = None
        suffix = f": {extra}" if extra else ""
        return {"error": True, "message": f"google_cse HTTP {response.status_code}{suffix}"}
    except requests.RequestException as exc:
        return {"error": True, "message": f"google_cse {exc}"}

    payload = response.json()
    items = payload.get("items") or []
    _debug("google_cse response count", len(items) if isinstance(items, list) else 0)
    results = _normalize_results(items)
    return {"error": False, "engine": "google_cse", "results": _prune_results(results, limit)}


def _search_serper(query: str, limit: Optional[int]) -> Dict[str, Any]:
    if not SERPER_API_KEY:
        return {"skipped": True, "message": "SERPER_API_KEY not set"}

    body = {"q": query, "num": limit or DEFAULT_LIMIT or 3}
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json",
        "User-Agent": AGENT_UA,
    }

    try:
        response = requests.post(
            "https://google.serper.dev/search",
            json=body,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
    except requests.HTTPError:
        try:
            detail = response.json()
            _debug("serper error body", detail)
        except Exception:
            pass
        return {"error": True, "message": f"serper HTTP {response.status_code}"}
    except requests.RequestException as exc:
        return {"error": True, "message": f"serper {exc}"}

    payload = response.json()
    organic = payload.get("organic") or []
    _debug("serper organic count", len(organic) if isinstance(organic, list) else 0)
    results = _normalize_results(organic)
    return {"error": False, "engine": "serper", "results": _prune_results(results, limit)}


def search_ollama(query: str, limit: Optional[int] = None) -> Dict[str, Any]:
    try:
        res = ollama.web_search( 
            query=query,
            max_results=limit or DEFAULT_LIMIT,
        )

        results = getattr(res, "results", None) or res.get("results") or []
        if not results:
            return {"error": True, "engine": "ollama_web_search", "message": "ollama returned no results"}

        return {"error": False, "engine": "ollama_web_search", "results": results}

    except Exception as exc:
        return {"error": True, "engine": "ollama_web_search", "message": f"web_search failed: {exc}"}

def _run_fallback_search(query: str, limit: Optional[int]) -> Dict[str, Any]:
    attempts: List[str] = []
    providers: List[Tuple[str, Any]] = [
        ("google_cse", _search_google_cse),
        ("serper", _search_serper),
        ("ollama_search", search_ollama),
    ]

    for name, fn in providers:
        try:
            result = fn(query, limit)
        except Exception as exc:  # pragma: no cover - defensive log
            attempts.append(f"{name}: {exc}")
            continue

        if result.get("skipped"):
            attempts.append(f"{name}: {result['message']}")
            continue

        if not result.get("error") and result.get("results"):
            result["attempts"] = attempts
            return result

        attempts.append(f"{name}: {result.get('message', 'no results returned')}")

    message = (
        f"All providers failed. {' | '.join(attempts)}"
        if attempts
        else "No search providers are configured."
    )
    return {"error": True, "message": message, "attempts": attempts}


@tool("web_search")
def web_search(query: str, limit: Optional[int] = None) -> dict:
    """Search the web (Google Custom Search -> Serper -> Ollama)."""
    capped_limit = min(limit or DEFAULT_LIMIT, 10)
    result = _run_fallback_search(query, capped_limit)
    if result.get("error"):
        return result
    return {
        "error": False,
        "engine": result.get("engine"),
        "query": query,
        "attempts": result.get("attempts", []),
        "results": result.get("results", []),
    }


__all__ = ["web_search"]
