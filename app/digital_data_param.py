"""CSV-backed digital data loaders for local client-specific testing."""

from __future__ import annotations

import re

import pandas as pd

from local_config import get_data_dir


_DATA_DIR = get_data_dir()

_STATE_NAME_TO_ABBR = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "district of columbia": "DC", "florida": "FL", "georgia": "GA", "hawaii": "HI",
    "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY", "puerto rico": "PR",
}

_VALID_ABBR = set(_STATE_NAME_TO_ABBR.values())
_INTERNATIONAL_PATTERNS = [
    "british columbia", "santo domingo", "dominican republic",
    "province", "ontario", "quebec",
]
_SPECIAL_MAP = {
    "san francisco bay area": "CA",
    "silicon valley": "CA",
    "washington dc (hagerstown md)": "DC",
    "san francisco-oakland-san jose c": "CA",
    "yakima-pasco-richland-kennewick": "WA",
    "yakima-pasco-richland-kennewick ": "WA",
    "tampa-st. petersburg (sarasota)": "FL",
    "tampa-st. petersburg (sarasota) ": "FL",
    "orlando-daytona beach-melbourne": "FL",
    "orlando-daytona beach-melbourne ": "FL",
    "harrisburg-lancaster-lebanon-yor": "PA",
    "grand rapids-kalamazoo-battle cr": "MI",
    "greensboro-high point-winston sa": "NC",
    "norfolk-portsmouth-newport news": "VA",
    "norfolk-portsmouth-newport news ": "VA",
    "cedar rapids-waterloo-iowa city": "IA",
    "cedar rapids-waterloo-iowa city ": "IA",
    "champaign & springfield-decatur": "IL",
    "champaign & springfield-decatur ": "IL",
    "santa barbara-santa maria-san lu": "CA",
    "minot-bismarck-dickinson(willist": "ND",
    "ft. smith-fayetteville-springdal": "AR",
    "tyler-longview(lufkin & nacogdoc": "TX",
    "greenville-new bern-washington n": "NC",
    "harlingen-weslaco-brownsville-mc": "TX",
    "san francisco-oakland-san jose ca": "CA",
    "davenport ia-rock island-moline": "IA",
    "davenport ia-rock island-moline ": "IA",
    "ft. smith-fayetteville-springdale": "AR",
    "rochester mn-mason city ia-austi": "MN",
    "paducah ky-cape girardeau mo-har": "KY",
}
_STATE_SUFFIX_RE = re.compile(r"^(.+)\s*\(State\)$", re.IGNORECASE)
_US_COLON_RE = re.compile(r"^US:([a-zA-Z]{2})$", re.IGNORECASE)
_US_STATE_RE = re.compile(r"^US:(.+)$", re.IGNORECASE)


def _read_csv(csv_name: str, **kwargs) -> pd.DataFrame:
    path = _DATA_DIR / csv_name
    if not path.exists():
        raise FileNotFoundError(f"Local CSV not found: {path}")
    return pd.read_csv(path, **kwargs)


def _filter_client(df: pd.DataFrame, client_name: str) -> pd.DataFrame:
    if "client_name" in df.columns:
        df["client_name"] = df["client_name"].fillna("").astype(str).str.strip()
        return df[df["client_name"] == client_name]
    return df


def _sanitize_region(region: str) -> str:
    if not region or str(region).strip() == "":
        return "Unknown"
    r = str(region).strip()
    r_lower = r.lower()
    if r_lower in _SPECIAL_MAP:
        return _SPECIAL_MAP[r_lower]
    if r_lower.rstrip() in _SPECIAL_MAP:
        return _SPECIAL_MAP[r_lower.rstrip()]
    if r_lower == "unknown":
        return "Unknown"
    m = _STATE_SUFFIX_RE.match(r)
    if m:
        name = m.group(1).strip().lower()
        if name in _STATE_NAME_TO_ABBR:
            return _STATE_NAME_TO_ABBR[name]
    if r_lower in _STATE_NAME_TO_ABBR:
        return _STATE_NAME_TO_ABBR[r_lower]
    if len(r) == 2 and r.upper() in _VALID_ABBR:
        return r.upper()
    m = _US_COLON_RE.match(r)
    if m:
        code = m.group(1).upper()
        return code if code in _VALID_ABBR else "Unknown"
    m = _US_STATE_RE.match(r)
    if m:
        val = m.group(1).strip()
        val_lower = val.lower()
        if val_lower in _STATE_NAME_TO_ABBR:
            return _STATE_NAME_TO_ABBR[val_lower]
        if val.startswith("US-") and len(val) == 5:
            code = val[3:].upper()
            if code in _VALID_ABBR:
                return code
        return "Unknown"
    for pat in _INTERNATIONAL_PATTERNS:
        if pat in r_lower:
            return "International"
    all_codes = re.findall(r"\b([A-Z]{2})\b", r)
    valid_codes = [c for c in all_codes if c in _VALID_ABBR]
    if valid_codes:
        return valid_codes[0]
    if "," in r:
        for part in r.split(","):
            part_clean = part.strip().lower()
            if part_clean in _STATE_NAME_TO_ABBR:
                return _STATE_NAME_TO_ABBR[part_clean]
    return "Unknown"


def _sanitize_q10_regions(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["region"] = df["region"].apply(_sanitize_region)
    return df


def load_q8(client_name: str) -> pd.DataFrame:
    """Q8 - Digital overview (daily grain)."""
    df = _filter_client(_read_csv("q8_digital_overview.csv"), client_name)
    df["day"] = pd.to_datetime(df["day"], errors="coerce")
    for col in ["group_name", "subgroup_name", "product_name", "campaign_name"]:
        if col in df.columns:
            df[col] = df[col].fillna("").str.strip()
    for col in ["impressions", "clicks", "direct_conversions",
                "view_through_conversions", "total_interactions",
                "in_platform_leads", "cost", "budget",
                "followers", "likes", "shares", "comments"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df.reset_index(drop=True)


def load_q9(client_name: str) -> pd.DataFrame:
    """Q9 - Digital interactions (daily grain with interaction categories)."""
    df = _filter_client(_read_csv("q9_digital_interactions.csv"), client_name)
    df["day"] = pd.to_datetime(df["day"], errors="coerce")
    for col in ["group_name", "subgroup_name", "product_name",
                "campaign_name", "conversion_name", "interaction_category"]:
        if col in df.columns:
            df[col] = df[col].fillna("").str.strip()
    for col in ["direct_conversions", "view_through_conversions",
                "in_platform_leads", "total_interactions", "cost", "budget"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    if "interaction_category" in df.columns:
        df["interaction_category"] = df["interaction_category"].replace("Campus Visit", "Visit/Event")
    return df.reset_index(drop=True)


def load_q10(client_name: str) -> pd.DataFrame:
    """Q10 - Digital geography with daily rows by region."""
    df = _filter_client(_read_csv("q10_digital_geo.csv"), client_name)
    if "day" in df.columns:
        df["day"] = pd.to_datetime(df["day"], errors="coerce")
    for col in ["group_name", "subgroup_name", "product_name", "region"]:
        if col in df.columns:
            df[col] = df[col].fillna("").str.strip()
    for col in ["impressions", "clicks", "direct_conversions",
                "view_through_conversions", "in_platform_leads",
                "total_conversions", "cost", "budget"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return _sanitize_q10_regions(df).reset_index(drop=True)


def load_q11_creative(client_name: str) -> pd.DataFrame:
    """Q11a - Digital creative with daily rows (excludes YouTube)."""
    df = _filter_client(_read_csv("q11_digital_creative.csv"), client_name)
    if "day" in df.columns:
        df["day"] = pd.to_datetime(df["day"], errors="coerce")
    if "product_name" in df.columns:
        df = df[~df["product_name"].fillna("").str.strip().isin({"YouTube", "Youtube"})]
    for col in ["group_name", "subgroup_name", "product_name",
                "campaign_name", "platform_campaign_name",
                "creative", "ad_description", "ad_url",
                "image_url", "preview_url", "ad_group"]:
        if col in df.columns:
            df[col] = df[col].fillna("").str.strip()
    for col in ["impressions", "clicks", "direct_conversions",
                "view_through_conversions", "in_platform_leads",
                "total_conversions", "cost", "budget",
                "followers", "likes", "shares", "comments", "visits",
                "video_starts", "video_completions"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df.reset_index(drop=True)


def load_q11_youtube(client_name: str) -> pd.DataFrame:
    """Q11c - YouTube creative (daily grain for correct video_avg)."""
    df = _filter_client(_read_csv("q11_youtube_creative.csv"), client_name)
    df["day"] = pd.to_datetime(df["day"], errors="coerce")
    for col in ["group_name", "subgroup_name", "product_name",
                "campaign_name", "platform_campaign_name",
                "creative", "ad_description", "ad_url",
                "image_url", "preview_url", "ad_group"]:
        if col in df.columns:
            df[col] = df[col].fillna("").str.strip()
    for col in ["impressions", "clicks", "direct_conversions",
                "view_through_conversions", "in_platform_leads",
                "total_conversions", "cost", "budget",
                "video_starts", "video_completions"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    if "video_avg" in df.columns:
        df["video_avg"] = pd.to_numeric(df["video_avg"], errors="coerce")
    return df.reset_index(drop=True)


def load_q11_keywords(client_name: str) -> pd.DataFrame:
    """Q11b - PPC keyword performance with daily rows."""
    df = _filter_client(_read_csv("q11_digital_keywords.csv"), client_name)
    if "day" in df.columns:
        df["day"] = pd.to_datetime(df["day"], errors="coerce")
    for col in ["platform_campaign_name", "campaign_name",
                "product_name", "keyword", "match_type"]:
        if col in df.columns:
            df[col] = df[col].fillna("").str.strip()
    for col in ["impressions", "clicks", "direct_conversions", "cost", "budget"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df.reset_index(drop=True)


def load_q12(client_name: str) -> pd.DataFrame:
    """Q12 - Digital notes / insights."""
    df = _filter_client(_read_csv("q12_digital_notes.csv"), client_name)
    df["day"] = pd.to_datetime(df["day"], errors="coerce")
    for col in ["group_name", "subgroup_name", "product_name",
                "strategy", "campaign_name", "note_type",
                "is_milestone", "notes", "created_by"]:
        if col in df.columns:
            df[col] = df[col].fillna("").str.strip()
    if {"day", "note_type", "notes"}.issubset(df.columns):
        df = df.drop_duplicates(subset=["day", "note_type", "notes"])
    return df.reset_index(drop=True)
