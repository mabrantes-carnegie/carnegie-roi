import os
import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, HTMLResponse
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

JWT_PUBLIC_KEY = os.environ.get("JWT_PUBLIC_KEY", "")
COOKIE_SECRET = os.environ.get("COOKIE_SECRET", "")
COOKIE_NAME = "roi_session"
COOKIE_MAX_AGE = 60 * 60 * 8  # 8 hours

_signer = URLSafeTimedSerializer(COOKIE_SECRET)


def _set_session_cookie(response: Response, identity: str) -> None:
    value = _signer.dumps({"id": identity})
    response.set_cookie(
        COOKIE_NAME,
        value,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="none",
        secure=True,
    )


def _valid_session(request: Request) -> bool:
    raw = request.cookies.get(COOKIE_NAME)
    if not raw:
        return False
    try:
        _signer.loads(raw, max_age=COOKIE_MAX_AGE)
        return True
    except (BadSignature, SignatureExpired):
        return False


class JWTAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Token present — validate and set session cookie
        token = request.query_params.get("token", "")
        if token:
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
                return HTMLResponse("Link expired.", status_code=401)
            except jwt.InvalidTokenError:
                return HTMLResponse("Invalid link.", status_code=401)

            response = await call_next(request)
            _set_session_cookie(response, "authenticated")
            return response

        # All routes — require valid session cookie
        if not _valid_session(request):
            return HTMLResponse(
                "<h2>Access denied.</h2>"
                "<p>Please use your portal link to access this dashboard.</p>",
                status_code=403,
            )

        return await call_next(request)
