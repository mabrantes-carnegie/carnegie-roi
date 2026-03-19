"""All calculated metrics for the ROI dashboard. Pure functions, no reactivity."""

import pandas as pd


# Column names for funnel volume metrics
FUNNEL_COLS = [
    "total_inquiries", "total_app_starts", "total_app_submits",
    "total_admits", "total_deposits", "total_net_deposits", "total_enrolled",
]

# Cost-per metric definitions: (display_name, cost_col_name, volume_col)
COST_PER_DEFS = [
    ("Cost per Inquiry", "cost_per_inquiry", "total_inquiries"),
    ("Cost per App Start", "cost_per_app_start", "total_app_starts"),
    ("Cost per App Submit", "cost_per_app_submit", "total_app_submits"),
    ("Cost per Admit", "cost_per_admit", "total_admits"),
    ("Cost per Deposit", "cost_per_deposit", "total_deposits"),
    ("Cost per Net Deposit", "cost_per_net_deposit", "total_net_deposits"),
    ("Cost per Enrolled", "cost_per_enrolled", "total_enrolled"),
]


def _safe_div(a, b):
    """Divide a by b, returning None if b is 0 or either is None."""
    if b is None or b == 0 or a is None:
        return None
    return a / b


def compute_funnel_kpis(df: pd.DataFrame) -> dict:
    """Compute KPI values from a filtered q1 DataFrame.

    Returns dict with keys: total_inquiries, total_app_starts, ...,
    admitted_rate, yield_rate.
    """
    if df.empty:
        result = {col: 0 for col in FUNNEL_COLS}
        result["admitted_rate"] = None
        result["yield_rate"] = None
        return result

    sums = {col: int(df[col].sum()) for col in FUNNEL_COLS}
    sums["admitted_rate"] = _safe_div(sums["total_admits"], sums["total_app_submits"])
    sums["yield_rate"] = _safe_div(sums["total_deposits"], sums["total_admits"])
    # Convert rates to percentages
    if sums["admitted_rate"] is not None:
        sums["admitted_rate"] *= 100
    if sums["yield_rate"] is not None:
        sums["yield_rate"] *= 100
    return sums


def compute_yoy_change(current: dict, prior: dict) -> dict:
    """Compute YoY percentage change for each metric.

    Returns dict of float or None for each key.
    """
    result = {}
    for key in current:
        curr_val = current[key]
        prior_val = prior.get(key)
        if prior_val is None or prior_val == 0 or curr_val is None:
            result[key] = None
        else:
            result[key] = ((curr_val - prior_val) / abs(prior_val)) * 100
    return result


def compute_cost_summary(df: pd.DataFrame) -> dict:
    """Compute aggregate cost-per-stage metrics from q2 data.

    Returns dict with total_cost and cost_per_* keys.
    """
    if df.empty:
        result = {"total_cost": 0}
        for _, col_name, _ in COST_PER_DEFS:
            result[col_name] = None
        return result

    total_cost = df["total_cost"].sum()
    result = {"total_cost": total_cost}
    for _, col_name, vol_col in COST_PER_DEFS:
        vol = df[vol_col].sum()
        result[col_name] = _safe_div(total_cost, vol)
    return result


def compute_campaign_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """Group q2 by lead_source and compute cost-per metrics per group.

    Returns DataFrame with columns: lead_source, total_cost, volume cols,
    and cost_per_* cols.
    """
    if df.empty:
        cols = ["lead_source", "total_cost"] + FUNNEL_COLS + [d[1] for d in COST_PER_DEFS]
        return pd.DataFrame(columns=cols)

    agg_cols = {"total_cost": "sum"}
    for col in FUNNEL_COLS:
        agg_cols[col] = "sum"

    grouped = df.groupby("lead_source", as_index=False).agg(agg_cols)

    for _, col_name, vol_col in COST_PER_DEFS:
        grouped[col_name] = grouped.apply(
            lambda row, vc=vol_col: _safe_div(row["total_cost"], row[vc]),
            axis=1,
        )
    return grouped


def compute_geo_state_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate q3 by student_state."""
    if df.empty:
        return pd.DataFrame(columns=["student_state"] + FUNNEL_COLS)

    return df.groupby("student_state", as_index=False)[FUNNEL_COLS].sum()


def compute_geo_detail(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate q3 by student_state + student_city."""
    if df.empty:
        return pd.DataFrame(columns=["student_state", "student_city"] + FUNNEL_COLS)

    result = df.groupby(
        ["student_state", "student_city"], as_index=False
    )[FUNNEL_COLS].sum()
    return result.sort_values("total_inquiries", ascending=False).reset_index(drop=True)
