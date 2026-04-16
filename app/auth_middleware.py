import os
import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse

JWT_PUBLIC_KEY = os.environ.get("JWT_PUBLIC_KEY", "")


class JWTAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        token = request.query_params.get("token", "")

        if not token:
            return HTMLResponse(
                "<h2>Access denied.</h2>"
                "<p>Please use your portal link to access this dashboard.</p>",
                status_code=403,
            )

        if not JWT_PUBLIC_KEY:
            return HTMLResponse("JWT_PUBLIC_KEY not configured.", status_code=500)

        try:
            jwt.decode(
                token,
                JWT_PUBLIC_KEY,
                algorithms=["RS256"],
                options={"require": ["exp"]},
            )
        except jwt.ExpiredSignatureError:
            return HTMLResponse("Link expired. Please request a new one.", status_code=401)
        except jwt.InvalidTokenError:
            return HTMLResponse("Invalid link.", status_code=401)

        return await call_next(request)
