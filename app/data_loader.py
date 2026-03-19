"""Load and clean CSV data once at startup."""

from datetime import date
from pathlib import Path
import pandas as pd

_DATA_DIR = Path(__file__).parent.parent / "data"

# Valid US state/territory 2-letter codes
VALID_US_STATES = frozenset({
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC", "PR", "GU", "VI", "AS", "MP",
})


def _load_q1() -> pd.DataFrame:
    df = pd.read_csv(_DATA_DIR / "q1_funnel_kpis.csv")
    # Replace empty student_type with "Unknown"
    df["student_type"] = df["student_type"].fillna("Unknown").replace("", "Unknown")
    # Ensure is_international is bool (pandas may auto-parse "false"/"true")
    df["is_international"] = df["is_international"].astype(bool)
    # Drop rows where term_year or term_semester is missing (5 rows, all zeros)
    df = df.dropna(subset=["term_year", "term_semester"])
    df["term_year"] = df["term_year"].astype(int)
    return df.reset_index(drop=True)


def _load_q2() -> pd.DataFrame:
    df = pd.read_csv(_DATA_DIR / "q2_campaign_cost.csv")
    df["term_year"] = df["term_year"].astype(int)
    # Strip whitespace from string columns
    for col in ["institution_name", "lead_source", "campaign_service",
                "campaign_funnel_target"]:
        df[col] = df[col].str.strip()
    return df


def _load_q3() -> pd.DataFrame:
    df = pd.read_csv(_DATA_DIR / "q3_geography.csv")
    # Clean student_state
    df["student_state"] = df["student_state"].fillna("").str.strip()
    df.loc[df["student_state"] == "", "student_state"] = "Unknown"
    # Mark non-US states as "International"
    mask = ~df["student_state"].isin(VALID_US_STATES | {"Unknown"})
    df.loc[mask, "student_state"] = "International"
    # Clean student_city
    df["student_city"] = df["student_city"].fillna("").str.strip().str.title()
    df.loc[df["student_city"] == "", "student_city"] = "Unknown"
    df["term_year"] = df["term_year"].astype(int)
    return df.reset_index(drop=True)


def _load_q4() -> pd.DataFrame:
    """Load monthly trending data (q4_monthly_trending.csv)."""
    df = pd.read_csv(_DATA_DIR / "q4_monthly_trending.csv")
    df["student_type"] = df["student_type"].fillna("Unknown").replace("", "Unknown")
    df["is_international"] = df["is_international"].astype(bool)
    df["term_year"] = df["term_year"].astype(int)
    df["event_year"] = df["event_year"].astype(int)
    df["event_month"] = df["event_month"].astype(int)

    # Create event_date for filtering future months
    df["event_date"] = pd.to_datetime(
        df["event_year"].astype(str) + "-" + df["event_month"].astype(str).str.zfill(2) + "-01"
    )
    # Remove future months
    today_first = pd.Timestamp(date.today().replace(day=1))
    df = df[df["event_date"] <= today_first]

    # Academic cycle position: Jul=1 ... Jun=12
    acad_order = {7: 1, 8: 2, 9: 3, 10: 4, 11: 5, 12: 6,
                  1: 7, 2: 8, 3: 9, 4: 10, 5: 11, 6: 12}
    df["acad_pos"] = df["event_month"].map(acad_order)

    # Month label for x-axis
    month_labels = {1: "Jul", 2: "Aug", 3: "Sep", 4: "Oct", 5: "Nov", 6: "Dec",
                    7: "Jan", 8: "Feb", 9: "Mar", 10: "Apr", 11: "May", 12: "Jun"}
    df["month_label"] = df["acad_pos"].map(month_labels)

    return df.reset_index(drop=True)


# Load once at import time
Q1 = _load_q1()
Q2 = _load_q2()
Q3 = _load_q3()
Q4 = _load_q4()


def get_institutions() -> list[str]:
    return sorted(Q1["institution_name"].unique().tolist())


def get_term_years() -> list[str]:
    """Return sorted unique term years across all datasets, as strings."""
    years = set(Q1["term_year"].unique()) | set(Q2["term_year"].unique()) | set(Q3["term_year"].unique())
    return [str(y) for y in sorted(years)]


def get_term_semesters() -> list[str]:
    return sorted(Q1["term_semester"].unique().tolist())


def get_student_types() -> list[str]:
    types = Q1["student_type"].unique().tolist()
    # Put common types first, Unknown last
    priority = ["First Year", "Transfer", "Graduate", "Adult", "Readmit", "Unknown"]
    return [t for t in priority if t in types]
