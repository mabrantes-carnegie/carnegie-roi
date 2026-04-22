"""Resolve the local institution name from CSV files or environment variables."""

from functools import lru_cache

from local_config import detect_institution_name, get_local_sage_id, list_available_institutions


DEFAULT_SAGE_ID = get_local_sage_id()


@lru_cache(maxsize=1)
def _resolved_name() -> str | None:
    return detect_institution_name()


def resolve_institution(sage_id: str | None) -> str | None:
    """Return the local institution name, ignoring the provided sage_id value."""
    if not sage_id:
        return None
    return _resolved_name()


def list_known_institutions(limit: int = 20) -> list[dict]:
    """Expose the institutions discovered from the local CSV files."""
    return [
        {"sage_id": DEFAULT_SAGE_ID, "name": name}
        for name in list_available_institutions()[:limit]
    ]
