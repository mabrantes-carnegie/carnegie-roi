"""
Resolve a MyCarnegie sage_id to an institution name via BigQuery.

Usage:
    from client_resolver import resolve_institution

    institution_name = resolve_institution("<sage_id>")

For local testing, pass a sage_id through the test app URL.
"""

from functools import lru_cache
from google.cloud import bigquery

# Config

BQ_PROJECT = "unified-data-platform-prod"
INSTITUTION_TABLE = f"`{BQ_PROJECT}.udp_udl.institution`"

_client = bigquery.Client(project=BQ_PROJECT)


# Lookup

@lru_cache(maxsize=64)
def resolve_institution(sage_id: str | None) -> str | None:
    """
    Look up institution name from sage_id.

    Args:
        sage_id: The `id` value from udp_udl.institution, as sent by MyCarnegie.

    Returns:
        The institution `name`, or None if the sage_id is missing or not found.
    """
    if not sage_id:
        return None

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
    Return a sample of known sage_id to name mappings.
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
