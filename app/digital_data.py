"""Load and clean digital performance data from BigQuery once at startup."""

from pathlib import Path
import re
import pandas as pd
from google.cloud import bigquery

_QUERY_DIR = Path(__file__).parent.parent / "data" / "queries"
_DATA_DIR = Path(__file__).parent.parent / "data"

# Use unified-data-platform-prod as billing project (jobs.create permission).
# Queries reference carnegie-dartlet tables by full path — no change needed.
_BQ_DIGITAL = bigquery.Client(project="unified-data-platform-prod")

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

_US_COLON_RE = re.compile(r"^US:([a-zA-Z]{2})$", re.IGNORECASE)
_US_STATE_RE = re.compile(r"^US:(.+)$", re.IGNORECASE)
_STATE_SUFFIX_RE = re.compile(r"^(.+)\s*\(State\)$", re.IGNORECASE)
_DMA_STATE_RE = re.compile(r"\b([A-Z]{2})(?:\s*$|-)")


def _sanitize_region(region: str) -> str:
    if not region or region.strip() == "":
        return "Unknown"
    r = region.strip()
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
        if code in _VALID_ABBR:
            return code
        return "Unknown"
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
        parts = r.split(",")
        for part in parts:
            part_clean = part.strip().lower()
            if part_clean in _STATE_NAME_TO_ABBR:
                return _STATE_NAME_TO_ABBR[part_clean]
    return "Unknown"


def _sanitize_q10_regions(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["region_original"] = df["region"]
    df["region"] = df["region_original"].apply(_sanitize_region)

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

    validation.to_csv(_DATA_DIR / "q10_region_mapping_detail.csv", index=False)
    state_summary.to_csv(_DATA_DIR / "q10_region_sanitization_summary.csv", index=False)

    df = df.drop(columns=["region_original"])
    return df


def _extract_query(sql: str, export_label: str) -> str:
    """Extract a single query block from the combined SQL file by its export label.

    The file alternates: header_block (with 'Export as:') | sql_block | header_block | ...
    so we find the header index and return the next block's SQL.
    """
    blocks = re.split(r"\n--\s*={10,}", sql)
    for i, block in enumerate(blocks):
        if f"Export as: {export_label}" in block:
            # The actual SQL is in the next block
            sql_block = blocks[i + 1] if i + 1 < len(blocks) else ""
            m = re.search(r"((?:WITH\b|SELECT\b).*)", sql_block, re.DOTALL | re.IGNORECASE)
            if m:
                return m.group(1).strip()
    raise ValueError(f"Query block for '{export_label}' not found in SQL file")


def _run_digital(export_label: str) -> pd.DataFrame:
    sql_full = (_QUERY_DIR / "ROI_All_Digital.sql").read_text(encoding="utf-8", errors="replace")
    sql = _extract_query(sql_full, export_label)
    return _BQ_DIGITAL.query(sql).to_dataframe()


def _load_q8() -> pd.DataFrame:
    """Q8 — Digital overview (daily grain)."""
    df = _run_digital("q8_digital_overview.csv")
    df["day"] = pd.to_datetime(df["day"])
    for col in ["group_name", "subgroup_name", "product_name", "campaign_name"]:
        df[col] = df[col].fillna("").str.strip()
    for col in ["impressions", "clicks", "direct_conversions",
                "view_through_conversions", "total_interactions",
                "in_platform_leads", "cost", "budget",
                "followers", "likes", "shares", "comments"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def _load_q9() -> pd.DataFrame:
    """Q9 — Digital interactions (daily grain with interaction categories)."""
    df = _run_digital("q9_digital_interactions.csv")
    df["day"] = pd.to_datetime(df["day"])
    for col in ["group_name", "subgroup_name", "product_name",
                "campaign_name", "conversion_name", "interaction_category"]:
        df[col] = df[col].fillna("").str.strip()
    for col in ["direct_conversions", "view_through_conversions",
                "in_platform_leads", "total_interactions", "cost", "budget"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["interaction_category"] = df["interaction_category"].replace("Campus Visit", "Visit/Event")
    return df


def _load_q10() -> pd.DataFrame:
    """Q10 — Digital geography (monthly grain by region)."""
    df = _run_digital("q10_digital_geo.csv")
    for col in ["group_name", "subgroup_name", "product_name", "region"]:
        df[col] = df[col].fillna("").str.strip()
    for col in ["impressions", "clicks", "direct_conversions",
                "view_through_conversions", "in_platform_leads",
                "total_conversions", "cost", "budget"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def _load_q11_creative() -> pd.DataFrame:
    """Q11a — Digital creative (ALL platforms, excludes YouTube)."""
    df = _run_digital("q11_digital_creative.csv")
    # Exclude YouTube rows — served from Q11c instead
    df = df[~df["product_name"].str.strip().isin({"YouTube", "Youtube"})]
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
    return df


def _load_q11_youtube() -> pd.DataFrame:
    """Q11c — YouTube creative (daily grain for correct video_avg)."""
    df = _run_digital("q11_youtube_creative.csv")
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
    return df


def _load_q11_keywords() -> pd.DataFrame:
    """Q11b — PPC keyword performance (monthly grain)."""
    df = _run_digital("q11_digital_keywords.csv")
    for col in ["platform_campaign_name", "campaign_name",
                "product_name", "keyword", "match_type"]:
        df[col] = df[col].fillna("").str.strip()
    for col in ["impressions", "clicks", "direct_conversions", "cost", "budget"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def _load_q12() -> pd.DataFrame:
    """Q12 — Digital notes / insights."""
    df = _run_digital("q12_digital_notes.csv")
    df["day"] = pd.to_datetime(df["day"], errors="coerce")
    for col in ["group_name", "subgroup_name", "product_name",
                "strategy", "campaign_name", "note_type",
                "is_milestone", "notes", "created_by"]:
        if col in df.columns:
            df[col] = df[col].fillna("").str.strip()
    df = df.drop_duplicates(subset=["day", "note_type", "notes"])
    return df


# Load once at import time
Q8 = _load_q8()
Q9 = _load_q9()
Q10 = _sanitize_q10_regions(_load_q10())
Q11_CREATIVE = _load_q11_creative()
Q11_KEYWORDS = _load_q11_keywords()
Q11_YOUTUBE = _load_q11_youtube()
Q12 = _load_q12()


def get_digital_date_range() -> tuple:
    return Q8["day"].min(), Q8["day"].max()


def get_digital_groups() -> list[str]:
    return sorted([g for g in Q8["group_name"].unique() if g])


def get_digital_subgroups() -> list[str]:
    return sorted([s for s in Q8["subgroup_name"].unique() if s])


def get_digital_products() -> list[str]:
    return sorted([p for p in Q8["product_name"].unique() if p])


def get_digital_campaigns() -> list[str]:
    return sorted([c for c in Q8["campaign_name"].unique() if c])
