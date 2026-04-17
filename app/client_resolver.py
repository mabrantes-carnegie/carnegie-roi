"""
Resolve a MyCarnegie sage_id to an institution name via BigQuery.

sage_id is the trusted identity sent by MyCarnegie inside the signed JWT and
then stored by auth_middleware in the `roi_session` cookie. There is no
default fallback: if sage_id is missing or unknown, callers must handle the
None return and show an access-denied UI rather than silently picking a
client.
"""

from functools import lru_cache

from google.cloud import bigquery

BQ_PROJECT = "unified-data-platform-prod"
INSTITUTION_TABLE = f"`{BQ_PROJECT}.udp_udl.institution`"

_client = bigquery.Client(project=BQ_PROJECT)


@lru_cache(maxsize=64)
def _lookup(sage_id: str) -> str | None:
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


def resolve_institution(sage_id: str | None) -> str | None:
    """Look up the institution name for a sage_id.

    Returns None when sage_id is missing, empty, or not present in
    `udp_udl.institution`. Callers must block access in that case.
    """
    if not sage_id:
        return None
    return _lookup(sage_id)


def list_known_institutions(limit: int = 20) -> list[dict]:
    """Return a sample of known sage_id → name mappings (dev helper)."""
    query = f"""
        SELECT id AS sage_id, name
        FROM {INSTITUTION_TABLE}
        WHERE name IS NOT NULL AND name != 'None'
        ORDER BY name
        LIMIT {limit}
    """
    rows = list(_client.query(query).result())
    return [{"sage_id": r["sage_id"], "name": r["name"]} for r in rows]
