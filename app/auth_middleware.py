import os
import jwt
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.requests import Request
from starlette.responses import HTMLResponse

JWT_PUBLIC_KEY = os.environ.get("JWT_PUBLIC_KEY", "")


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

            if not token:
                response = HTMLResponse(
                    "<h2>Access denied.</h2>"
                    "<p>Please use your portal link to access this dashboard.</p>",
                    status_code=403,
                )
                await response(scope, receive, send)
                return

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

            await self.app(scope, receive, send)
