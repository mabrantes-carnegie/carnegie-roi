"""
Materialized-table data loader (TESTING ONLY).

Reads from the pre-materialized tables in
unified-data-platform-459720.dbt_mlima.roi_*, filtering by institution_id
(= sage_id) at query time. Same public API as data_loader_param.py so it can
be used as a drop-in replacement via the USE_MATERIALIZED env var.

NOT for production — these tables are not on a refresh schedule.
"""

from datetime import date
from pathlib import Path
import pandas as pd
from google.cloud import bigquery

BQ_BILLING_PROJECT = "carnegie-roi-reports"
BQ_SOURCE_PROJECT = "unified-data-platform-prod"  # for institution_name → id lookup
MLIMA_DATASET = "unified-data-platform-459720.dbt_mlima"

_client = bigquery.Client(project=BQ_BILLING_PROJECT)

VALID_US_STATES = frozenset({
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC", "PR", "GU", "VI", "AS", "MP",
})

ACAD_ORDER = {7: 1, 8: 2, 9: 3, 10: 4, 11: 5, 12: 6,
              1: 7, 2: 8, 3: 9, 4: 10, 5: 11, 6: 12}
MONTH_LABELS = {1: "Jul", 2: "Aug", 3: "Sep", 4: "Oct", 5: "Nov", 6: "Dec",
                7: "Jan", 8: "Feb", 9: "Mar", 10: "Apr", 11: "May", 12: "Jun"}


def _resolve_institution_id(institution_name: str) -> str:
    sql = f"""
        SELECT id
        FROM `{BQ_SOURCE_PROJECT}.udp_udl.institution`
        WHERE name = @institution_name
        LIMIT 1
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("institution_name", "STRING", institution_name)
        ]
    )
    df = _client.query(sql, job_config=job_config).to_dataframe()
    if df.empty:
        raise ValueError(f"No institution found for name: {institution_name!r}")
    return str(df.iloc[0]["id"])


def _query_by_institution_id(table: str, institution_id: str) -> pd.DataFrame:
    sql = f"""
        SELECT *
        FROM `{MLIMA_DATASET}.{table}`
        WHERE institution_id = @institution_id
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("institution_id", "STRING", institution_id)
        ]
    )
    return _client.query(sql, job_config=job_config).to_dataframe()


# ── Public loaders (same signatures as data_loader_param.py) ──────────────────

def load_q6(institution_name: str) -> pd.DataFrame:
    """Q6 — Principal funnel data (monthly grain)."""
    institution_id = _resolve_institution_id(institution_name)
    df = _query_by_institution_id("roi_principal", institution_id)
    df["student_type"] = df["student_type"].fillna("Unknown").replace("", "Unknown")
    df["is_international"] = df["is_international"].astype(bool)
    df["term_year"] = df["term_year"].astype(int)
    df["event_year"] = df["event_year"].astype(int)
    df["event_month"] = df["event_month"].astype(int)
    df["origin_source_first"] = df["origin_source_first"].fillna("Unknown").replace("", "Unknown")
    df["student_state"] = df["student_state"].fillna("").str.strip()
    df.loc[df["student_state"] == "", "student_state"] = "Unknown"
    mask = ~df["student_state"].isin(VALID_US_STATES | {"Unknown"})
    df.loc[mask, "student_state"] = "International"
    df["location_type"] = df["student_state"].apply(
        lambda s: "US" if s in VALID_US_STATES else s
    )
    df["acad_pos"] = df["event_month"].map(ACAD_ORDER)
    df["month_label"] = df["acad_pos"].map(MONTH_LABELS)
    df["event_date"] = pd.to_datetime(
        df["event_year"].astype(str) + "-" + df["event_month"].astype(str).str.zfill(2) + "-01"
    )
    today_first = pd.Timestamp(date.today().replace(day=1))
    df = df[df["event_date"] <= today_first]
    return df.reset_index(drop=True)


def load_q2(institution_name: str) -> pd.DataFrame:
    """Q2 — Campaign cost + lead source."""
    institution_id = _resolve_institution_id(institution_name)
    df = _query_by_institution_id("roi_campaign_cost", institution_id)
    df["term_year"] = df["term_year"].astype(int)
    for col in ["institution_name", "lead_source", "campaign_service", "campaign_funnel_target"]:
        if col in df.columns:
            df[col] = df[col].str.strip()
    return df


def load_q3(institution_name: str) -> pd.DataFrame:
    """Q3 — City-level geography detail."""
    institution_id = _resolve_institution_id(institution_name)
    df = _query_by_institution_id("roi_geography", institution_id)
    df["student_state"] = df["student_state"].fillna("").str.strip()
    df.loc[df["student_state"] == "", "student_state"] = "Unknown"
    mask = ~df["student_state"].isin(VALID_US_STATES | {"Unknown"})
    df.loc[mask, "student_state"] = "International"
    df["location_type"] = df["student_state"].apply(
        lambda s: "US" if s in VALID_US_STATES else s
    )
    df["student_city"] = df["student_city"].fillna("").str.strip()
    df.loc[df["student_city"] == "", "student_city"] = "Unknown"
    df["term_year"] = df["term_year"].astype(int)
    return df.reset_index(drop=True)
