"""
Materialized-table digital data loader (TESTING ONLY).

Reads from unified-data-platform-459720.dbt_mlima.roi_digital_*, filtering
by client_name (= institution_name) at query time. Same public API as
digital_data_param.py.
"""

import pandas as pd
from google.cloud import bigquery

from digital_data_param import _sanitize_q10_regions  # reuse region sanitizer

BQ_BILLING_PROJECT = "carnegie-roi-reports"
MLIMA_DATASET = "unified-data-platform-459720.dbt_mlima"

_client = bigquery.Client(project=BQ_BILLING_PROJECT)


def _query_by_client(table: str, client_name: str) -> pd.DataFrame:
    sql = f"""
        SELECT *
        FROM `{MLIMA_DATASET}.{table}`
        WHERE client_name = @client_name
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("client_name", "STRING", client_name)
        ]
    )
    return _client.query(sql, job_config=job_config).to_dataframe()


# ── Public loaders (same signatures as digital_data_param.py) ─────────────────

def load_q8(client_name: str) -> pd.DataFrame:
    df = _query_by_client("roi_digital_overview", client_name)
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


def load_q9(client_name: str) -> pd.DataFrame:
    df = _query_by_client("roi_digital_interactions", client_name)
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


def load_q10(client_name: str) -> pd.DataFrame:
    df = _query_by_client("roi_digital_geo", client_name)
    for col in ["group_name", "subgroup_name", "product_name", "region"]:
        df[col] = df[col].fillna("").str.strip()
    for col in ["impressions", "clicks", "direct_conversions",
                "view_through_conversions", "in_platform_leads",
                "total_conversions", "cost", "budget"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return _sanitize_q10_regions(df)


def load_q11_creative(client_name: str) -> pd.DataFrame:
    df = _query_by_client("roi_digital_creative", client_name)
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


def load_q11_youtube(client_name: str) -> pd.DataFrame:
    df = _query_by_client("roi_youtube_creative", client_name)
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


def load_q11_keywords(client_name: str) -> pd.DataFrame:
    df = _query_by_client("roi_digital_keywords", client_name)
    for col in ["platform_campaign_name", "campaign_name",
                "product_name", "keyword", "match_type"]:
        df[col] = df[col].fillna("").str.strip()
    for col in ["impressions", "clicks", "direct_conversions", "cost", "budget"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def load_q12(client_name: str) -> pd.DataFrame:
    df = _query_by_client("roi_digital_notes", client_name)
    df["day"] = pd.to_datetime(df["day"], errors="coerce")
    for col in ["group_name", "subgroup_name", "product_name",
                "strategy", "campaign_name", "note_type",
                "is_milestone", "notes", "created_by"]:
        if col in df.columns:
            df[col] = df[col].fillna("").str.strip()
    df = df.drop_duplicates(subset=["day", "note_type", "notes"])
    return df
