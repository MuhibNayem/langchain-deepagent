from __future__ import annotations

import os
from typing import Optional

import requests
from langchain.tools import tool

API_BASE = "https://api.weatherapi.com/v1"


def _fetch_weather(query: str) -> dict:
    api_key = os.environ.get("WEATHER_API_KEY")
    if not api_key:
        return {"error": True, "message": "WEATHER_API_KEY is not set"}

    url = f"{API_BASE}/current.json"
    params = {"key": api_key, "q": query, "aqi": "no"}
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
    except requests.HTTPError:
        try:
            detail = response.json()
            extra = detail.get("error", {}).get("message")
        except Exception:  # pragma: no cover - best effort parsing
            extra = None
        suffix = f": {extra}" if extra else ""
        return {"error": True, "message": f"HTTP {response.status_code}{suffix}"}
    except requests.RequestException as exc:
        return {"error": True, "message": str(exc)}

    data = response.json()
    current = data.get("current") or {}
    if not current:
        return {"error": True, "message": "No current weather data returned"}

    location = data.get("location") or {}
    return {
        "error": False,
        "location": location.get("name") or query,
        "country": location.get("country") or "",
        "condition": (current.get("condition") or {}).get("text") or "Unknown",
        "temp_c": current.get("temp_c"),
        "temp_f": current.get("temp_f"),
        "feelslike_c": current.get("feelslike_c"),
        "feelslike_f": current.get("feelslike_f"),
        "humidity": current.get("humidity"),
        "wind_kph": current.get("wind_kph"),
        "wind_dir": current.get("wind_dir"),
        "cloud": current.get("cloud"),
        "updated_at": current.get("last_updated"),
        "raw": data,
    }


@tool("get_weather")
def get_weather(city: Optional[str] = None, location: Optional[str] = None, query: Optional[str] = None) -> dict:
    """Get real-time weather using WeatherAPI (requires WEATHER_API_KEY)."""
    search = city or location or query
    if not search:
        return {"error": True, "message": "Provide city, location, or query"}
    return _fetch_weather(search)


__all__ = ["get_weather"]
