"""
Parameterized data loader for client-specific BigQuery queries.

All functions accept institution_name as an explicit argument.
No data is loaded at module import time — loading is triggered
per session after sage_id resolution.

This is the target pattern for the production multi-client app.
The current app/data_loader.py (CWU-hardcoded) is not modified here.
"""

import re
from datetime import date
from pathlib import Path
import pandas as pd
from google.cloud import bigquery

_QUERY_DIR = Path(__file__).parent.parent / "data" / "queries"

BQ_PROJECT = "unified-data-platform-prod"
_client = bigquery.Client(project=BQ_PROJECT)

# Valid US state/territory 2-letter codes (copied from data_loader.py)
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


def _parameterize(sql: str, institution_name: str) -> tuple[str, bigquery.QueryJobConfig]:
    """
    Replace the hardcoded institution name filter in a SQL query with a
    BigQuery named parameter (@institution_name), and return the modified
    SQL together with the job config carrying the parameter value.

    Handles both forms present in the queries:
      WHERE i.name = 'Central Washington University'
      WHERE institution_name = 'Central Washington University'
      AND   institution_name = 'Central Washington University'
    """
    # Replace any quoted string assigned to institution name comparisons
    parameterized = re.sub(
        r"((?:WHERE|AND)\s+(?:i\.name|institution_name)\s*=\s*)'[^']*'",
        r"\1@institution_name",
        sql,
        flags=re.IGNORECASE,
    )
    # Also replace the hardcoded string literal used in SELECT for geo query
    # e.g. 'Central Washington University' AS institution_name
    parameterized = re.sub(
        r"'Central Washington University'\s+AS\s+institution_name",
        "@institution_name AS institution_name",
        parameterized,
        flags=re.IGNORECASE,
    )
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("institution_name", "STRING", institution_name)
        ]
    )
    return parameterized, job_config


def _run(sql_file: str, institution_name: str) -> pd.DataFrame:
    sql = (_QUERY_DIR / sql_file).read_text(encoding="utf-8", errors="replace")
    parameterized_sql, job_config = _parameterize(sql, institution_name)
    return _client.query(parameterized_sql, job_config=job_config).to_dataframe()


# ── Public loaders ─────────────────────────────────────────────────────────────

def load_q6(institution_name: str) -> pd.DataFrame:
    """Q6 — Principal funnel data with daily rows and month helper columns."""
    df = _run("ROI_Principal.sql", institution_name)
    if "day" in df.columns:
        df["day"] = pd.to_datetime(df["day"], errors="coerce")
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
    """Q2 — Campaign cost + lead source with daily rows."""
    df = _run("ROI_Campaign_Cost.sql", institution_name)
    if "day" in df.columns:
        df["day"] = pd.to_datetime(df["day"], errors="coerce")
    df["term_year"] = df["term_year"].astype(int)
    for col in ["institution_name", "lead_source", "campaign_service", "campaign_funnel_target"]:
        if col in df.columns:
            df[col] = df[col].str.strip()
    return df


def load_q3(institution_name: str) -> pd.DataFrame:
    """Q3 — City-level geography detail with daily rows."""
    df = _run("ROI_Geography.sql", institution_name)
    if "day" in df.columns:
        df["day"] = pd.to_datetime(df["day"], errors="coerce")
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
