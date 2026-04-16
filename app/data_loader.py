"""Load and clean data from BigQuery once at startup."""

import re
from datetime import date
from pathlib import Path
import pandas as pd
from google.cloud import bigquery

_QUERY_DIR = Path(__file__).parent.parent / "data" / "queries"
_DATA_DIR = Path(__file__).parent.parent / "data"

_BQ_ROI = bigquery.Client(project="unified-data-platform-prod")

# Valid US state/territory 2-letter codes
VALID_US_STATES = frozenset({
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC", "PR", "GU", "VI", "AS", "MP",
})

# Academic month ordering (Jul=1 ... Jun=12)
ACAD_ORDER = {7: 1, 8: 2, 9: 3, 10: 4, 11: 5, 12: 6,
              1: 7, 2: 8, 3: 9, 4: 10, 5: 11, 6: 12}
MONTH_LABELS = {1: "Jul", 2: "Aug", 3: "Sep", 4: "Oct", 5: "Nov", 6: "Dec",
                7: "Jan", 8: "Feb", 9: "Mar", 10: "Apr", 11: "May", 12: "Jun"}


def _run_query(sql_file: str) -> pd.DataFrame:
    sql = (_QUERY_DIR / sql_file).read_text()
    return _BQ_ROI.query(sql).to_dataframe()


def _load_q6() -> pd.DataFrame:
    """Load Q6 Source of Truth (funnel_benchmark_current monthly)."""
    df = _run_query("ROI_Principal.sql")
    df["student_type"] = df["student_type"].fillna("Unknown").replace("", "Unknown")
    df["is_international"] = df["is_international"].astype(bool)
    df["term_year"] = df["term_year"].astype(int)
    df["event_year"] = df["event_year"].astype(int)
    df["event_month"] = df["event_month"].astype(int)
    df["origin_source_first"] = df["origin_source_first"].fillna("Unknown").replace("", "Unknown")
    df["student_state"] = df["student_state"].fillna("").str.strip()
    df.loc[df["student_state"] == "", "student_state"] = "Unknown"
    # Mark non-US states as International
    mask = ~df["student_state"].isin(VALID_US_STATES | {"Unknown"})
    df.loc[mask, "student_state"] = "International"
    # Location type for easy filtering
    df["location_type"] = df["student_state"].apply(
        lambda s: "US" if s in VALID_US_STATES else s
    )
    # Academic month position and label
    df["acad_pos"] = df["event_month"].map(ACAD_ORDER)
    df["month_label"] = df["acad_pos"].map(MONTH_LABELS)
    # Event date for filtering future months
    df["event_date"] = pd.to_datetime(
        df["event_year"].astype(str) + "-" + df["event_month"].astype(str).str.zfill(2) + "-01"
    )
    today_first = pd.Timestamp(date.today().replace(day=1))
    df = df[df["event_date"] <= today_first]
    return df.reset_index(drop=True)


def _load_q2() -> pd.DataFrame:
    df = _run_query("ROI_Campaign_Cost.sql")
    df["term_year"] = df["term_year"].astype(int)
    for col in ["institution_name", "lead_source", "campaign_service",
                "campaign_funnel_target"]:
        df[col] = df[col].str.strip()
    return df


def _clean_city(city: str, state: str) -> str:
    """Clean city name: remove trailing state abbreviation, title case."""
    if not city or city == "Unknown":
        return city
    if state and state in VALID_US_STATES:
        city = re.sub(r"\s+" + re.escape(state) + r"$", "", city, flags=re.IGNORECASE)
    result = city.strip()
    return result.title() if result else "Unknown"


def _load_q3() -> pd.DataFrame:
    """Load city-level geography detail."""
    df = _run_query("ROI_Geography.sql")
    df["student_state"] = df["student_state"].fillna("").str.strip()
    df.loc[df["student_state"] == "", "student_state"] = "Unknown"
    mask = ~df["student_state"].isin(VALID_US_STATES | {"Unknown"})
    df.loc[mask, "student_state"] = "International"
    df["location_type"] = df["student_state"].apply(
        lambda s: "US" if s in VALID_US_STATES else s
    )
    df["student_city"] = df["student_city"].fillna("").str.strip()
    df.loc[df["student_city"] == "", "student_city"] = "Unknown"
    df["student_city"] = df.apply(
        lambda r: _clean_city(r["student_city"], r["student_state"]), axis=1
    )
    df["term_year"] = df["term_year"].astype(int)
    return df.reset_index(drop=True)


def _load_goals() -> dict:
    """Load roi_goals.csv and aggregate to institution-level goals."""
    df = pd.read_csv(_DATA_DIR / "roi_goals.csv")
    return {
        "total_inquiries": int(df["Inquiry Goal"].sum()),
        "total_app_starts": int(df["App Starts Goal"].sum()),
        "total_app_submits": int(df["App Submit Goal"].sum()),
        "total_admits": int(df["Admit Goal"].sum()),
        "total_deposits": int(df["Deposit Goal"].sum()),
        "total_net_deposits": int(df["Net Deposit Goal"].sum()),
    }


def _load_program_goals() -> pd.DataFrame:
    """Load roi_goals.csv as a DataFrame with program-level goals."""
    df = pd.read_csv(_DATA_DIR / "roi_goals.csv")
    df = df.rename(columns={
        "Program": "program",
        "Inquiry Goal": "goal_inquiries",
        "App Starts Goal": "goal_app_starts",
        "App Submit Goal": "goal_app_submits",
        "Admit Goal": "goal_admits",
        "Deposit Goal": "goal_deposits",
        "Net Deposit Goal": "goal_net_deposits",
    })
    # Normalize program names to lowercase for matching
    df["program_lower"] = df["program"].str.strip().str.lower()
    return df


# Load once at import time
Q6 = _load_q6()  # PRIMARY — KPIs, trending, source trend, state geo
Q2 = _load_q2()  # Cost and campaign lead source data
Q3 = _load_q3()  # City-level geography detail only
GOALS = _load_goals()
PROGRAM_GOALS = _load_program_goals()


def get_institutions() -> list[str]:
    return sorted(Q6["institution_name"].unique().tolist())


def get_term_years() -> list[str]:
    years = set(Q6["term_year"].unique()) | set(Q2["term_year"].unique())
    return [str(y) for y in sorted(years)]


def get_term_semesters() -> list[str]:
    return sorted(Q6["term_semester"].unique().tolist())


def get_student_types() -> list[str]:
    types = Q6["student_type"].unique().tolist()
    priority = ["First Year", "Transfer", "Graduate", "Adult", "Readmit", "Other", "Unknown"]
    return [t for t in priority if t in types]


def get_programs_date_range() -> tuple:
    """Return min/max event_date from Q6."""
    return Q6["event_date"].min(), Q6["event_date"].max()
