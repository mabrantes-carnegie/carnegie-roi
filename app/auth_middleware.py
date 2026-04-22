"""No-op auth middleware for localhost testing."""

from starlette.types import ASGIApp, Receive, Scope, Send


class JWTAuthMiddleware:
    """Pass requests straight through without JWT validation in local mode."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await self.app(scope, receive, send)
