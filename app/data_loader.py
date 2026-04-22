"""Legacy loader module.

Unparameterized startup data loading is disabled for the multi-client
dashboard. Use data_loader_param.py and pass the resolved institution_name
explicitly from the signed session.
"""

import re
from datetime import date
from pathlib import Path
import pandas as pd

_QUERY_DIR = Path(__file__).parent.parent / "data" / "queries"
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

# Academic month ordering (Jul=1 ... Jun=12)
ACAD_ORDER = {7: 1, 8: 2, 9: 3, 10: 4, 11: 5, 12: 6,
              1: 7, 2: 8, 3: 9, 4: 10, 5: 11, 6: 12}
MONTH_LABELS = {1: "Jul", 2: "Aug", 3: "Sep", 4: "Oct", 5: "Nov", 6: "Dec",
                7: "Jan", 8: "Feb", 9: "Mar", 10: "Apr", 11: "May", 12: "Jun"}


def _run_query(sql_file: str) -> pd.DataFrame:
    raise RuntimeError(
        "Unparameterized data loading is disabled. "
        "Use data_loader_param.py with an explicit institution_name."
    )


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
    """Legacy local goals loading is disabled for multi-client safety."""
    return {}


def _load_program_goals() -> pd.DataFrame:
    """Legacy local program goals loading is disabled for multi-client safety."""
    empty_cols = [
        "program", "goal_inquiries", "goal_app_starts", "goal_app_submits",
        "goal_admits", "goal_deposits", "goal_net_deposits", "program_lower",
    ]
    return pd.DataFrame(columns=empty_cols)


# Client data placeholders; no import-time loading.
Q6 = pd.DataFrame()
Q2 = pd.DataFrame()
Q3 = pd.DataFrame()
GOALS = {}
PROGRAM_GOALS = pd.DataFrame(
    columns=[
        "program", "goal_inquiries", "goal_app_starts", "goal_app_submits",
        "goal_admits", "goal_deposits", "goal_net_deposits", "program_lower",
    ]
)


def get_institutions() -> list[str]:
    return []


def get_term_years() -> list[str]:
    return []


def get_term_semesters() -> list[str]:
    return []


def get_student_types() -> list[str]:
    return []


def get_programs_date_range() -> tuple:
    """Return min/max event_date from Q6."""
    return pd.NaT, pd.NaT
