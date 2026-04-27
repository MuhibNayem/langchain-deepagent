from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from typing import Optional

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


class APIKeyAuth:
    def __init__(self, api_keys: list[str], required: bool | None = None):
        self.api_keys = set(api_keys)
        self.required = bool(self.api_keys) if required is None else required

    async def __call__(self, api_key: str | None = Security(API_KEY_HEADER)):
        if not self.required:
            return api_key or ""
        if api_key not in self.api_keys:
            raise HTTPException(status_code=401, detail="Invalid API key")
        return api_key


def create_api_key_auth() -> APIKeyAuth:
    # Load from environment
    import os
    keys = os.environ.get("LUMINAMIND_API_KEYS", "").split(",")
    configured_keys = [k.strip() for k in keys if k.strip()]
    return APIKeyAuth(configured_keys)


async def verify_api_key(api_key: str = Security(API_KEY_HEADER)) -> str:
    """Dependency for verifying API key authentication.

    This function is intended to be overridden in app.py with the actual
    APIKeyAuth instance that validates against configured keys.
    """
    # Default implementation rejects all requests unless overridden
    raise HTTPException(status_code=401, detail="Authentication not configured")
