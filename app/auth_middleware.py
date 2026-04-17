import os
import re

import jwt
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from error_pages import render_error_response
from session_cookie import build_cookie, read_sage_id

JWT_PUBLIC_KEY = os.environ.get("JWT_PUBLIC_KEY", "")

# Public framework assets — no tenant data, so no auth.
# Needed because Safari drops third-party cookies on iframe subresources.
_PUBLIC_PATH_PREFIXES = (
    "/lib/",
    "/shared/",
    "/static/",
    "/www/",
    "/favicon",
)
_PUBLIC_PATH_SUFFIXES = (
    ".css",
    ".js",
    ".map",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
    ".eot",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
)


_SESSION_ASSET_RE = re.compile(r"^/session/[^/]+/(shared|lib)/")


def _is_public_asset(path: str) -> bool:
    if any(path.startswith(p) for p in _PUBLIC_PATH_PREFIXES):
        return True
    if _SESSION_ASSET_RE.match(path):
        return True
    if path.endswith(_PUBLIC_PATH_SUFFIXES):
        return True
    return False


def _cookie_header(scope: Scope) -> str:
    headers = dict(scope.get("headers", []))
    return headers.get(b"cookie", b"").decode("utf-8")


class JWTAuthMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("websocket", "lifespan"):
            await self.app(scope, receive, send)
            return

        if scope["type"] == "http":
            request = Request(scope, receive)

            if _is_public_asset(request.url.path):
                await self.app(scope, receive, send)
                return

            token = request.query_params.get("token", "")

            if token:
                if not JWT_PUBLIC_KEY:
                    response = HTMLResponse(
                        "JWT_PUBLIC_KEY not configured.", status_code=500
                    )
                    await response(scope, receive, send)
                    return
                try:
                    payload = jwt.decode(
                        token,
                        JWT_PUBLIC_KEY,
                        algorithms=["RS256"],
                        options={"require": ["exp", "sage_id"]},
                    )
                except jwt.ExpiredSignatureError:
                    response = render_error_response(
                        headline="Your session has expired",
                        message="Please return to the Carnegie portal and click the dashboard link again.",
                        status_code=401,
                    )
                    await response(scope, receive, send)
                    return
                except jwt.InvalidTokenError:
                    response = render_error_response(
                        headline="Invalid link",
                        message="Please return to the Carnegie portal and click the dashboard link again.",
                        status_code=401,
                    )
                    await response(scope, receive, send)
                    return

                sage_id = payload.get("sage_id", "")
                url_sage_id = request.query_params.get("sage_id", "")
                if url_sage_id and url_sage_id != sage_id:
                    response = render_error_response(
                        headline="Access denied",
                        message="Please use your portal link to access this dashboard.",
                        status_code=403,
                    )
                    await response(scope, receive, send)
                    return

                cookie_sender = _CookieSetter(send, sage_id)
                await self.app(scope, receive, cookie_sender.send)
                return

            session_sage_id = read_sage_id(_cookie_header(scope))
            if not session_sage_id:
                response = render_error_response(
                    headline="Access denied",
                    message="Please use your portal link to access this dashboard.",
                    status_code=403,
                )
                await response(scope, receive, send)
                return

            url_sage_id = request.query_params.get("sage_id", "")
            if url_sage_id and url_sage_id != session_sage_id:
                response = render_error_response(
                    headline="Access denied",
                    message="Please use your portal link to access this dashboard.",
                    status_code=403,
                )
                await response(scope, receive, send)
                return

            await self.app(scope, receive, send)


class _CookieSetter:
    """Injects a Set-Cookie header into the first http.response.start message."""

    def __init__(self, send: Send, identity: str) -> None:
        self._send = send
        self._identity = identity
        self._cookie_injected = False

    async def send(self, message: dict) -> None:
        if message["type"] == "http.response.start" and not self._cookie_injected:
            self._cookie_injected = True
            cookie = build_cookie(self._identity)
            headers = list(message.get("headers", []))
            headers.append((b"set-cookie", cookie.encode("utf-8")))
            message = {**message, "headers": headers}
        await self._send(message)
