import os
import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, RedirectResponse, HTMLResponse
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

JWT_SECRET = os.environ.get("JWT_SECRET", "")
COOKIE_SECRET = os.environ.get("COOKIE_SECRET", JWT_SECRET)
COOKIE_NAME = "roi_session"
COOKIE_MAX_AGE = 60 * 60 * 8  # 8 hours

_signer = URLSafeTimedSerializer(COOKIE_SECRET)


def _set_session_cookie(response: Response, email: str) -> None:
    value = _signer.dumps({"email": email})
    response.set_cookie(
        COOKIE_NAME,
        value,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
    )


def _get_session_email(request: Request) -> str | None:
    raw = request.cookies.get(COOKIE_NAME)
    if not raw:
        return None
    try:
        data = _signer.loads(raw, max_age=COOKIE_MAX_AGE)
        return data.get("email")
    except (BadSignature, SignatureExpired):
        return None


class JWTAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Health check — always allow (Cloud Run uses this)
        if path == "/health":
            return await call_next(request)

        # /auth?token=<jwt> — validate token, set session cookie, redirect to /
        if path == "/auth":
            if not JWT_SECRET:
                return HTMLResponse("JWT_SECRET not configured.", status_code=500)
            token = request.query_params.get("token", "")
            try:
                payload = jwt.decode(
                    token,
                    JWT_SECRET,
                    algorithms=["HS256"],
                    options={"require": ["email", "exp"]},
                )
            except jwt.ExpiredSignatureError:
                return HTMLResponse("Link expired. Please request a new one.", status_code=401)
            except jwt.InvalidTokenError:
                return HTMLResponse("Invalid link.", status_code=401)

            client = request.query_params.get("client", "")
            redirect_url = f"/?client={client}" if client else "/"
            response = RedirectResponse(url=redirect_url, status_code=302)
            _set_session_cookie(response, payload["email"])
            return response

        # All other routes — require a valid session cookie
        if not _get_session_email(request):
            return HTMLResponse(
                "<h2>Access denied.</h2>"
                "<p>Please use your portal link to access this dashboard.</p>",
                status_code=403,
            )

        return await call_next(request)
