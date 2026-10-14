from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.config import settings


class RateLimitMiddleware:
    """Small-process limiter for abuse-prone endpoints.

    Production deployments should also enforce a shared limit at the edge or
    API gateway. This middleware still protects a single worker and local
    deployments without adding a new infrastructure dependency.
    """

    def __init__(self, app):
        self.app = app
        self._events: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = Lock()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not settings.RATE_LIMIT_ENABLED:
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        path = request.url.path
        rule = self._rule_for(path)
        if rule is None:
            await self.app(scope, receive, send)
            return

        limit, window = rule
        client = request.client.host if request.client else "unknown"
        key = (client, path)
        now = monotonic()
        with self._lock:
            events = self._events[key]
            while events and events[0] <= now - window:
                events.popleft()
            if len(events) >= limit:
                response = JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please try again later."},
                    headers={"Retry-After": str(window)},
                )
                await response(scope, receive, send)
                return
            events.append(now)

        await self.app(scope, receive, send)

    @staticmethod
    def _rule_for(path: str) -> tuple[int, int] | None:
        if path.endswith("/auth/login"):
            return settings.RATE_LIMIT_LOGIN_MAX_REQUESTS, settings.RATE_LIMIT_WINDOW_SECONDS
        if path.endswith("/auth/register"):
            return settings.RATE_LIMIT_REGISTER_MAX_REQUESTS, 3600
        if any(path.endswith(suffix) for suffix in ("/auth/forgot-password", "/auth/reset-password", "/auth/refresh")):
            return 10, settings.RATE_LIMIT_WINDOW_SECONDS
        if path.endswith("/documents") or path.endswith("/image"):
            return settings.RATE_LIMIT_UPLOAD_MAX_REQUESTS, settings.RATE_LIMIT_WINDOW_SECONDS
        if path.endswith("/qr/verify"):
            return settings.RATE_LIMIT_QR_MAX_REQUESTS, settings.RATE_LIMIT_WINDOW_SECONDS
        return None
