from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEFAULT_TIMEOUT_SECONDS = 30
_SESSION: requests.Session | None = None


def create_secure_session(timeout: int = DEFAULT_TIMEOUT_SECONDS) -> requests.Session:
    """Create an HTTP session with TLS verification and basic retries."""
    session = requests.Session()
    session.verify = True

    retry_strategy = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS", "TRACE"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    # Store a default timeout for consumers to reference.
    session.request_timeout = timeout  # type: ignore[attr-defined]
    return session


def get_secure_session() -> requests.Session:
    """Return a shared secure session."""
    global _SESSION
    if _SESSION is None:
        _SESSION = create_secure_session()
    return _SESSION


__all__ = ["create_secure_session", "get_secure_session", "DEFAULT_TIMEOUT_SECONDS"]
