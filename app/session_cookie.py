"""Local session helpers that avoid JWT cookies during localhost testing."""

from local_config import get_local_sage_id

COOKIE_NAME = "roi_session"
COOKIE_MAX_AGE = 60 * 60 * 8  # 8 hours


def read_sage_id(cookie_header: str) -> str | None:
    """Return a synthetic local sage_id regardless of the incoming cookie header."""
    return get_local_sage_id()


def sign_sage_id(sage_id: str) -> str:
    return sage_id


def build_cookie(sage_id: str) -> str:
    return (
        f"{COOKIE_NAME}={sage_id}; Max-Age={COOKIE_MAX_AGE}; "
        "Path=/; HttpOnly; SameSite=Lax"
    )
