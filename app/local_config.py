"""Shared local-dev configuration for the CSV-backed dashboard."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd


_DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_INSTITUTION_SOURCES = [
    ("q6_fbc_monthly.csv", "institution_name"),
    ("q2_campaign_cost.csv", "institution_name"),
    ("q3_geography.csv", "institution_name"),
    ("q8_digital_overview.csv", "client_name"),
    ("q9_digital_interactions.csv", "client_name"),
    ("q10_digital_geo.csv", "client_name"),
    ("q11_digital_creative.csv", "client_name"),
    ("q11_digital_keywords.csv", "client_name"),
    ("q11_youtube_creative.csv", "client_name"),
    ("q12_digital_notes.csv", "client_name"),
]


def get_data_dir() -> Path:
    """Return the folder that contains the CSV exports used by the local app."""
    raw = os.environ.get("ROI_LOCAL_DATA_DIR", "").strip()
    return Path(raw).expanduser().resolve() if raw else _DEFAULT_DATA_DIR


def get_local_sage_id() -> str:
    """Return the synthetic sage_id used by the local app."""
    return os.environ.get("LOCAL_SAGE_ID", "local-dev").strip() or "local-dev"


def _read_unique_values(csv_name: str, column: str) -> list[str]:
    path = get_data_dir() / csv_name
    if not path.exists():
        return []

    try:
        df = pd.read_csv(path, usecols=[column])
    except Exception:
        return []

    values = (
        df[column]
        .dropna()
        .astype(str)
        .str.strip()
    )
    return sorted(v for v in values.unique().tolist() if v)


def list_available_institutions() -> list[str]:
    """Collect institution/client names available in the local CSV exports."""
    names: set[str] = set()
    for csv_name, column in _INSTITUTION_SOURCES:
        names.update(_read_unique_values(csv_name, column))
    return sorted(names)


def detect_institution_name() -> str | None:
    """Choose the institution to use for local testing."""
    explicit = os.environ.get("LOCAL_INSTITUTION_NAME", "").strip()
    if explicit:
        return explicit

    names = list_available_institutions()
    if len(names) == 1:
        return names[0]
    if len(names) > 1:
        return names[0]
    return None
