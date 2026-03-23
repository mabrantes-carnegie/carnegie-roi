"""Load and clean digital performance CSV data once at startup."""

from pathlib import Path
import pandas as pd

_DATA_DIR = Path(__file__).parent.parent / "data"


def _load_q8() -> pd.DataFrame:
    """Q8 — Digital overview (daily grain)."""
    df = pd.read_csv(_DATA_DIR / "q8_digital_overview.csv")
    df["day"] = pd.to_datetime(df["day"])
    for col in ["group_name", "subgroup_name", "product_name", "campaign_name"]:
        df[col] = df[col].fillna("").str.strip()
    # Ensure numeric cols
    for col in ["impressions", "clicks", "direct_conversions",
                "view_through_conversions", "total_interactions",
                "in_platform_leads", "cost", "budget",
                "followers", "likes", "shares", "comments"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def _load_q9() -> pd.DataFrame:
    """Q9 — Digital interactions (daily grain with interaction categories)."""
    df = pd.read_csv(_DATA_DIR / "q9_digital_interactions.csv")
    df["day"] = pd.to_datetime(df["day"])
    for col in ["group_name", "subgroup_name", "product_name",
                "campaign_name", "conversion_name", "interaction_category"]:
        df[col] = df[col].fillna("").str.strip()
    for col in ["direct_conversions", "view_through_conversions",
                "in_platform_leads", "total_interactions", "cost", "budget"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def _load_q10() -> pd.DataFrame:
    """Q10 — Digital geography (monthly grain by region)."""
    df = pd.read_csv(_DATA_DIR / "q10_digital_geo.csv")
    for col in ["group_name", "subgroup_name", "product_name", "region"]:
        df[col] = df[col].fillna("").str.strip()
    for col in ["impressions", "clicks", "direct_conversions",
                "view_through_conversions", "in_platform_leads",
                "total_conversions", "cost", "budget"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def _load_q11_creative() -> pd.DataFrame:
    """Q11 — Digital creative (monthly grain by creative)."""
    df = pd.read_csv(_DATA_DIR / "q11_digital_creative.csv")
    for col in ["group_name", "subgroup_name", "product_name",
                "campaign_name", "platform_campaign_name",
                "creative", "ad_description", "ad_url",
                "image_url", "preview_url", "ad_group"]:
        if col in df.columns:
            df[col] = df[col].fillna("").str.strip()
    for col in ["impressions", "clicks", "direct_conversions",
                "view_through_conversions", "in_platform_leads",
                "total_conversions", "cost", "budget",
                "followers", "likes", "shares", "comments",
                "video_starts", "video_completions"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def _load_q11_keywords() -> pd.DataFrame:
    """Q11 — PPC keyword performance (monthly grain)."""
    df = pd.read_csv(_DATA_DIR / "q11_digital_keywords.csv")
    for col in ["platform_campaign_name", "campaign_name",
                "product_name", "keyword", "match_type"]:
        df[col] = df[col].fillna("").str.strip()
    for col in ["impressions", "clicks", "direct_conversions", "cost", "budget"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def _load_q12() -> pd.DataFrame:
    """Q12 — Digital notes / insights."""
    df = pd.read_csv(_DATA_DIR / "q12_digital_notes.csv")
    df["day"] = pd.to_datetime(df["day"], errors="coerce")
    for col in ["group_name", "subgroup_name", "product_name",
                "strategy", "campaign_name", "note_type",
                "is_milestone", "notes", "created_by"]:
        if col in df.columns:
            df[col] = df[col].fillna("").str.strip()
    return df


# Load once at import time
Q8 = _load_q8()
Q9 = _load_q9()
Q10 = _load_q10()
Q11_CREATIVE = _load_q11_creative()
Q11_KEYWORDS = _load_q11_keywords()
Q12 = _load_q12()


def get_digital_date_range() -> tuple:
    """Return min/max date across Q8."""
    return Q8["day"].min(), Q8["day"].max()


def get_digital_groups() -> list[str]:
    return sorted([g for g in Q8["group_name"].unique() if g])


def get_digital_subgroups() -> list[str]:
    return sorted([s for s in Q8["subgroup_name"].unique() if s])


def get_digital_products() -> list[str]:
    return sorted([p for p in Q8["product_name"].unique() if p])


def get_digital_campaigns() -> list[str]:
    return sorted([c for c in Q8["campaign_name"].unique() if c])
