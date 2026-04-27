import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next):
        client = request.client.host
        now = time.time()

        if client not in self._requests:
            self._requests[client] = []

        # Clean old requests
        self._requests[client] = [t for t in self._requests[client] if now - t < self.window_seconds]

        if len(self._requests[client]) >= self.max_requests:
            return Response(content="Rate limit exceeded", status_code=429)

        self._requests[client].append(now)
        return await call_next(request)
