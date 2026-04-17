"""
Resolve a MyCarnegie sage_id to an institution name via BigQuery.

Usage:
    from client_resolver import resolve_institution, DEFAULT_SAGE_ID

    institution_name = resolve_institution("CentralWA11686")
    # → "Central Washington University"

For local testing without a real sage_id, set the env var:
    SAGE_ID=CentralWA11686
or rely on DEFAULT_SAGE_ID below.
"""

import os
from functools import lru_cache
from google.cloud import bigquery

# ── Config ────────────────────────────────────────────────────────────────────

BQ_PROJECT = "unified-data-platform-prod"
INSTITUTION_TABLE = f"`{BQ_PROJECT}.udp_udl.institution`"

# Fallback sage_id for local dev when no URL param is present.
# Change this to test a different client without touching the code.
DEFAULT_SAGE_ID = os.environ.get("SAGE_ID", "CentralWA11686")

_client = bigquery.Client(project=BQ_PROJECT)


# ── Lookup ────────────────────────────────────────────────────────────────────

@lru_cache(maxsize=64)
def resolve_institution(sage_id: str) -> str | None:
    """
    Look up institution name from sage_id.

    Args:
        sage_id: The `id` value from udp_udl.institution
                 (e.g. 'CentralWA11686'), as sent by MyCarnegie.

    Returns:
        The institution `name` (e.g. 'Central Washington University'),
        or None if the sage_id is not found.
    """
    query = f"""
        SELECT name
        FROM {INSTITUTION_TABLE}
        WHERE id = @sage_id
        LIMIT 1
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("sage_id", "STRING", sage_id)
        ]
    )
    rows = list(_client.query(query, job_config=job_config).result())
    return rows[0]["name"] if rows else None


def list_known_institutions(limit: int = 20) -> list[dict]:
    """
    Return a sample of known sage_id → name mappings.
    Useful for local discovery during development.
    """
    query = f"""
        SELECT id AS sage_id, name
        FROM {INSTITUTION_TABLE}
        WHERE name IS NOT NULL AND name != 'None'
        ORDER BY name
        LIMIT {limit}
    """
    rows = list(_client.query(query).result())
    return [{"sage_id": r["sage_id"], "name": r["name"]} for r in rows]
