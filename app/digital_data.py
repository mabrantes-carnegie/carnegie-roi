"""Load and clean digital performance CSV data once at startup."""

from pathlib import Path
import re
import pandas as pd

_DATA_DIR = Path(__file__).parent.parent / "data"

# ── Region sanitizer — maps messy Q10 region field to US state abbreviations ──

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

# Known international regions
_INTERNATIONAL_PATTERNS = [
    "british columbia", "santo domingo", "dominican republic",
    "province", "ontario", "quebec",
]

# Special mappings for non-standard entries and truncated DMA names
_SPECIAL_MAP = {
    "san francisco bay area": "CA",
    "silicon valley": "CA",
    "washington dc (hagerstown md)": "DC",
    # Truncated DMA names
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

# Regex for "US:xx" format
_US_COLON_RE = re.compile(r"^US:([a-zA-Z]{2})$", re.IGNORECASE)
# Regex for "US:StateName"
_US_STATE_RE = re.compile(r"^US:(.+)$", re.IGNORECASE)
# Regex for "(State)" suffix
_STATE_SUFFIX_RE = re.compile(r"^(.+)\s*\(State\)$", re.IGNORECASE)
# Regex for DMA with trailing state code like "Seattle-Tacoma WA"
_DMA_STATE_RE = re.compile(r"\b([A-Z]{2})(?:\s*$|-)")


def _sanitize_region(region: str) -> str:
    """Map a raw Q10 region value to a US state abbreviation, 'International', or 'Unknown'."""
    if not region or region.strip() == "":
        return "Unknown"

    r = region.strip()
    r_lower = r.lower()

    # Special map (exact match, case-insensitive) — also try with trailing space stripped
    if r_lower in _SPECIAL_MAP:
        return _SPECIAL_MAP[r_lower]
    if r_lower.rstrip() in _SPECIAL_MAP:
        return _SPECIAL_MAP[r_lower.rstrip()]

    # "Unknown" already
    if r_lower == "unknown":
        return "Unknown"

    # "(State)" suffix — e.g. "California (State)"
    m = _STATE_SUFFIX_RE.match(r)
    if m:
        name = m.group(1).strip().lower()
        if name in _STATE_NAME_TO_ABBR:
            return _STATE_NAME_TO_ABBR[name]

    # Bare state name — e.g. "California"
    if r_lower in _STATE_NAME_TO_ABBR:
        return _STATE_NAME_TO_ABBR[r_lower]

    # 2-letter code — e.g. "wa", "CA"
    if len(r) == 2 and r.upper() in _VALID_ABBR:
        return r.upper()

    # "US:xx" format — e.g. "US:wa", "US:California", "US:US-FL"
    m = _US_COLON_RE.match(r)
    if m:
        code = m.group(1).upper()
        if code in _VALID_ABBR:
            return code
        return "Unknown"

    m = _US_STATE_RE.match(r)
    if m:
        val = m.group(1).strip()
        val_lower = val.lower()
        if val_lower in _STATE_NAME_TO_ABBR:
            return _STATE_NAME_TO_ABBR[val_lower]
        # Handle "US:US-FL" style
        if val.startswith("US-") and len(val) == 5:
            code = val[3:].upper()
            if code in _VALID_ABBR:
                return code
        # US:null, US:NA, US:?, US:US, US:ON → Unknown
        return "Unknown"

    # International entries
    for pat in _INTERNATIONAL_PATTERNS:
        if pat in r_lower:
            return "International"

    # DMA regions — extract last 2-letter state code
    # e.g. "Seattle-Tacoma WA", "Boston MA-Manchester NH", "Tri-Cities TN-VA"
    # Find all 2-letter state codes in the string
    all_codes = re.findall(r"\b([A-Z]{2})\b", r)
    valid_codes = [c for c in all_codes if c in _VALID_ABBR]
    if valid_codes:
        # Use the first valid state code found
        return valid_codes[0]

    # Entries with comma-separated location info
    if "," in r:
        parts = r.split(",")
        for part in parts:
            part_clean = part.strip().lower()
            if part_clean in _STATE_NAME_TO_ABBR:
                return _STATE_NAME_TO_ABBR[part_clean]

    return "Unknown"


def _sanitize_q10_regions(df: pd.DataFrame) -> pd.DataFrame:
    """Sanitize Q10 region field and save validation CSV."""
    df = df.copy()
    df["region_original"] = df["region"]
    df["region"] = df["region_original"].apply(_sanitize_region)

    # Build validation CSV: per-state mapping results
    validation = df.groupby(["region", "region_original"]).agg(
        rows=("impressions", "size"),
        impressions=("impressions", "sum"),
    ).reset_index()

    total_impr = df["impressions"].sum()
    state_summary = df.groupby("region").agg(
        rows=("impressions", "size"),
        impressions=("impressions", "sum"),
    ).reset_index()
    state_summary["pct_impressions"] = (state_summary["impressions"] / total_impr * 100).round(2)
    state_summary = state_summary.sort_values("impressions", ascending=False)

    # Save detailed mapping
    validation.to_csv(_DATA_DIR / "q10_region_mapping_detail.csv", index=False)
    # Save state-level summary
    state_summary.to_csv(_DATA_DIR / "q10_region_sanitization_summary.csv", index=False)

    df = df.drop(columns=["region_original"])
    return df


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
Q10 = _sanitize_q10_regions(_load_q10())
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
