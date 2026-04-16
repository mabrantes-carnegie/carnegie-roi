import os
import jwt
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.requests import Request
from starlette.responses import HTMLResponse, Response
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

JWT_PUBLIC_KEY = os.environ.get("JWT_PUBLIC_KEY", "")
COOKIE_SECRET = os.environ.get("COOKIE_SECRET", "")
COOKIE_NAME = "roi_session"
COOKIE_MAX_AGE = 60 * 60  # 1 hour

_signer = URLSafeTimedSerializer(COOKIE_SECRET)


def _valid_session(scope: Scope) -> bool:
    headers = dict(scope.get("headers", []))
    cookie_header = headers.get(b"cookie", b"").decode("utf-8")
    cookies = {}
    for part in cookie_header.split(";"):
        if "=" in part:
            k, v = part.strip().split("=", 1)
            cookies[k.strip()] = v.strip()
    raw = cookies.get(COOKIE_NAME)
    if not raw:
        return False
    try:
        _signer.loads(raw, max_age=COOKIE_MAX_AGE)
        return True
    except (BadSignature, SignatureExpired):
        return False


class JWTAuthMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("websocket", "lifespan"):
            await self.app(scope, receive, send)
            return

        if scope["type"] == "http":
            request = Request(scope, receive)
            token = request.query_params.get("token", "")

            if token:
                if not JWT_PUBLIC_KEY:
                    response = HTMLResponse("JWT_PUBLIC_KEY not configured.", status_code=500)
                    await response(scope, receive, send)
                    return
                try:
                    jwt.decode(
                        token,
                        JWT_PUBLIC_KEY,
                        algorithms=["RS256"],
                        options={"require": ["exp"]},
                    )
                except jwt.ExpiredSignatureError:
                    response = HTMLResponse("Link expired. Please request a new one.", status_code=401)
                    await response(scope, receive, send)
                    return
                except jwt.InvalidTokenError:
                    response = HTMLResponse("Invalid link.", status_code=401)
                    await response(scope, receive, send)
                    return

                cookie_sender = _CookieSender(send, "authenticated")
                await self.app(scope, receive, cookie_sender.send)
                return

            if not _valid_session(scope):
                response = HTMLResponse(
                    "<h2>Access denied.</h2>"
                    "<p>Please use your portal link to access this dashboard.</p>",
                    status_code=403,
                )
                await response(scope, receive, send)
                return

            await self.app(scope, receive, send)


class _CookieSender:
    """Injects a Set-Cookie header into the first http.response.start message."""

    def __init__(self, send: Send, identity: str) -> None:
        self._send = send
        self._identity = identity
        self._cookie_injected = False

    async def send(self, message: dict) -> None:
        if message["type"] == "http.response.start" and not self._cookie_injected:
            self._cookie_injected = True
            value = _signer.dumps({"id": self._identity})
            cookie = (
                f"{COOKIE_NAME}={value}; Max-Age={COOKIE_MAX_AGE}; "
                f"Path=/; HttpOnly; Secure; SameSite=None"
            )
            headers = list(message.get("headers", []))
            headers.append((b"set-cookie", cookie.encode("utf-8")))
            message = {**message, "headers": headers}
        await self._send(message)
