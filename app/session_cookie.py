"""Shared helpers for the JWT-signed roi_session cookie.

Both the JWT auth middleware (which signs and sets the cookie) and the Shiny
server logic (which reads it to scope data per client) must use the exact
same signer, cookie name, and max-age — otherwise the app trusts a value
the middleware never issued. This module is the single source of truth.
"""

import os

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

COOKIE_NAME = "roi_session"
COOKIE_MAX_AGE = 60 * 60 * 8  # 8 hours

_COOKIE_SECRET = os.environ.get("COOKIE_SECRET", "")
signer = URLSafeTimedSerializer(_COOKIE_SECRET)


def _parse_cookie_header(cookie_header: str) -> dict[str, str]:
    cookies: dict[str, str] = {}
    if not cookie_header:
        return cookies
    for part in cookie_header.split(";"):
        if "=" in part:
            k, v = part.strip().split("=", 1)
            cookies[k.strip()] = v.strip()
    return cookies


def read_sage_id(cookie_header: str) -> str | None:
    """Extract and verify sage_id from a raw Cookie header.

    Returns None if the cookie is absent, malformed, tampered with, or expired.
    """
    cookies = _parse_cookie_header(cookie_header)
    raw = cookies.get(COOKIE_NAME)
    if not raw:
        return None
    try:
        data = signer.loads(raw, max_age=COOKIE_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None
    sid = data.get("id", "")
    return sid or None


def sign_sage_id(sage_id: str) -> str:
    """Produce the signed cookie value for a sage_id."""
    return signer.dumps({"id": sage_id})


def build_cookie(sage_id: str) -> str:
    """Return a Set-Cookie header value carrying the signed sage_id."""
    value = sign_sage_id(sage_id)
    return (
        f"{COOKIE_NAME}={value}; Max-Age={COOKIE_MAX_AGE}; "
        f"Path=/; HttpOnly; Secure; SameSite=None; Partitioned"
    )
