"""CSV-backed data loaders for local client-specific testing."""

from __future__ import annotations

from datetime import date

import pandas as pd

from local_config import get_data_dir


_DATA_DIR = get_data_dir()

# Valid US state/territory 2-letter codes
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


def _read_csv(csv_name: str, **kwargs) -> pd.DataFrame:
    path = _DATA_DIR / csv_name
    if not path.exists():
        raise FileNotFoundError(f"Local CSV not found: {path}")
    return pd.read_csv(path, **kwargs)


def load_q6(institution_name: str) -> pd.DataFrame:
    """Q6 - Principal funnel data with daily rows and month helper columns."""
    df = _read_csv("q6_fbc_monthly.csv")
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
        df["event_year"].astype(str) + "-" + df["event_month"].astype(str).str.zfill(2) + "-01",
        errors="coerce",
    )
    today_first = pd.Timestamp(date.today().replace(day=1))
    df = df[df["event_date"] <= today_first]
    if "institution_name" in df.columns:
        df = df[df["institution_name"] == institution_name]
    return df.reset_index(drop=True)


def load_q2(institution_name: str) -> pd.DataFrame:
    """Q2 - Campaign cost + lead source with daily rows."""
    df = _read_csv("q2_campaign_cost.csv")
    if "day" in df.columns:
        df["day"] = pd.to_datetime(df["day"], errors="coerce")
    df["term_year"] = df["term_year"].astype(int)
    for col in ["institution_name", "lead_source", "campaign_service", "campaign_funnel_target"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()
    if "institution_name" in df.columns:
        df = df[df["institution_name"] == institution_name]
    return df.reset_index(drop=True)


def load_q3(institution_name: str) -> pd.DataFrame:
    """Q3 - City-level geography detail with daily rows."""
    df = _read_csv("q3_geography.csv")
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
    if "institution_name" in df.columns:
        df = df[df["institution_name"] == institution_name]
    return df.reset_index(drop=True)
