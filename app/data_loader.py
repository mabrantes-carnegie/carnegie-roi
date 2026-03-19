"""Load and clean CSV data once at startup."""

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


# Load once at import time
Q1 = _load_q1()
Q2 = _load_q2()
Q3 = _load_q3()


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
