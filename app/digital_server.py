"""Digital Performance page — reactive server logic (all 5 sub-tabs)."""

import pandas as pd
from shiny import render, reactive, ui, req
import plotly.graph_objects as go

from digital_data import Q8, Q9, Q10, Q11_CREATIVE, Q11_KEYWORDS, Q12
from formatters import fmt_number, fmt_currency

# ── Carnegie brand colors ────────────────────────────────────
CARNEGIE_NAVY = "#021326"
CARNEGIE_GRAY_TEXT = "#6b7280"
CARNEGIE_GRAY_BORDER = "#e5e1dc"
CARNEGIE_BG = "#f8f4f0"
CARNEGIE_WHITE = "#ffffff"

# Chart data palette — red is NEVER used for data series
CHART_COLORS = [
    "#021326",  # Carnegie Blue dark — primary
    "#A4B9D3",  # Carnegie Blue light — secondary
    "#C99D44",  # Carnegie Gold
    "#6B8F71",  # Muted green
    "#8B7355",  # Warm brown
    "#5B7C99",  # Steel blue
    "#9B8EC0",  # Muted purple
    "#D4A574",  # Sand/tan
]
STRATEGY_COLORS = CHART_COLORS


_HEATMAP_COLOR = "#C99D44"


def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _parse_num_for_total(v):
    """Parse a formatted cell value to float for totalling; returns None if not numeric."""
    if isinstance(v, (int, float)):
        return float(v)
    try:
        s = str(v).replace(",", "").replace("%", "").replace("+", "").strip()
        if s in ("", "—", "N/A"):
            return None
        return float(s)
    except Exception:
        return None


def _build_total_row(df: "pd.DataFrame", td_first: str, td_base: str) -> str:
    """Return a <tr> HTML string with column sums; non-numeric columns show '—'."""
    cells = []
    for ci, col in enumerate(df.columns):
        style = (td_first if ci == 0 else td_base) + "font-weight:700;border-top:2px solid #e5e1dc;"
        if ci == 0:
            cells.append(f'<td style="{style}">Total</td>')
        else:
            nums = [_parse_num_for_total(v) for v in df[col]]
            nums = [n for n in nums if n is not None]
            if nums:
                import math
                valid = [n for n in nums if not math.isnan(n)]
                if not valid:
                    cells.append(f'<td style="{style}">—</td>')
                    continue
                total = sum(valid)
                # Percentage columns show '—' in total (summing rates is meaningless)
                pct_count = sum(1 for v in df[col] if isinstance(v, str) and "%" in v)
                if pct_count > len(df) * 0.5:
                    cells.append(f'<td style="{style}">—</td>')
                else:
                    cells.append(f'<td style="{style}">{round(total):,}</td>')
            else:
                cells.append(f'<td style="{style}">—</td>')
    return "<tr>" + "".join(cells) + "</tr>"


def _yoy_delta_table(
    rows: list,          # list of dicts: {label, metrics: {col: (value_str, delta_str)}}
    label_col: str,      # header for the first column
    metric_cols: list,   # ordered list of metric names
) -> "ui.HTML":
    """
    Render a YoY comparison table: for each metric column show the value then
    a narrow Δ% column with a green/red/grey badge.
    rows: list of dicts with keys 'label' and 'metrics' (dict col -> (val, delta)).
    """
    import math

    th = (
        "padding:8px 10px;font-family:Manrope,sans-serif;font-size:11px;"
        "font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:0.04em;"
        "border-bottom:1px solid #e5e1dc;text-align:right;white-space:nowrap;cursor:pointer;"
    )
    th_first = th.replace("text-align:right;", "text-align:left;")
    th_delta = th + "padding-left:2px;padding-right:10px;"
    td = (
        "padding:7px 10px;font-family:Manrope,sans-serif;font-size:13px;"
        "color:#021326;border-bottom:1px solid #f0eeea;text-align:right;"
    )
    td_first = td.replace("text-align:right;", "text-align:left;")
    td_delta = td + "padding-left:2px;padding-right:10px;"

    def _delta_badge(d):
        if not d or d in ("N/A", "—", ""):
            return f'<span style="font-size:11px;color:#9B9893;">—</span>'
        try:
            num = float(d.replace("%", "").replace("+", ""))
        except Exception:
            return f'<span style="font-size:11px;color:#9B9893;">{d}</span>'
        if math.isnan(num):
            return f'<span style="font-size:11px;color:#9B9893;">—</span>'
        color = "#1a7a4a" if num > 0 else ("#b91c1c" if num < 0 else "#57595B")
        bg    = "#e6f4ed" if num > 0 else ("#fde8e8" if num < 0 else "#f3f3f3")
        sign  = "+" if num > 0 else ""
        return (
            f'<span style="font-size:11px;font-family:Manrope,sans-serif;font-weight:600;'
            f'color:{color};background:{bg};border-radius:4px;padding:2px 5px;">'
            f'{sign}{num:.1f}%</span>'
        )

    # Pre-compute per-column min/max for heatmap scaling (value cells only)
    hr, hg, hb = _hex_to_rgb(_HEATMAP_COLOR)

    def _to_num(v):
        if isinstance(v, (int, float)):
            return float(v)
        try:
            return float(str(v).replace(",", "").replace("%", "").strip())
        except Exception:
            return None

    col_ranges = {}
    for col in metric_cols:
        nums = [_to_num(r["metrics"].get(col, ("—", ""))[0]) for r in rows]
        nums = [n for n in nums if n is not None]
        col_ranges[col] = (min(nums), max(nums)) if len(nums) > 1 else (0, 1)

    # Headers
    header_cells = [f'<th style="{th_first}">{label_col}</th>']
    for col in metric_cols:
        header_cells.append(f'<th style="{th}">{col}</th>')
        header_cells.append(f'<th style="{th_delta}">Δ%</th>')

    # Data rows
    rows_html = []
    for r in rows:
        cells = [f'<td style="{td_first}">{r["label"]}</td>']
        for col in metric_cols:
            val, delta = r["metrics"].get(col, ("—", ""))
            # Apply heatmap background to value cell
            cell_style = td
            num = _to_num(val)
            if num is not None and col in col_ranges:
                lo, hi = col_ranges[col]
                ratio = (num - lo) / (hi - lo) if hi > lo else 0
                alpha = round(0.08 + ratio * 0.62, 3)
                cell_style += f"background:rgba({hr},{hg},{hb},{alpha});"
            cells.append(f'<td style="{cell_style}">{val}</td>')
            cells.append(f'<td style="{td_delta}">{_delta_badge(delta)}</td>')
        rows_html.append("<tr>" + "".join(cells) + "</tr>")

    # Total row — sum value cols, skip delta cols
    total_cells = [f'<td style="{td_first}font-weight:700;border-top:2px solid #e5e1dc;">Total</td>']
    for col in metric_cols:
        vals = [r["metrics"].get(col, ("—", ""))[0] for r in rows]
        nums = []
        is_pct = False
        for v in vals:
            s = str(v).replace(",", "").replace("%", "").replace("+", "").strip()
            if "%" in str(v):
                is_pct = True
            try:
                nums.append(float(s))
            except Exception:
                pass
        bold = "font-weight:700;border-top:2px solid #e5e1dc;"
        if is_pct or not nums:
            total_cells.append(f'<td style="{td}{bold}">—</td>')
        else:
            total_cells.append(f'<td style="{td}{bold}">{round(sum(nums)):,}</td>')
        total_cells.append(f'<td style="{td_delta}{bold}">—</td>')
    rows_html_total = "<tr>" + "".join(total_cells) + "</tr>"

    html = (
        '<div style="overflow-x:auto;">'
        '<table class="sortable-table" style="width:100%;border-collapse:collapse;">'
        "<thead><tr>" + "".join(header_cells) + "</tr></thead>"
        "<tbody>" + "".join(rows_html) + "</tbody>"
        "<tfoot>" + rows_html_total + "</tfoot>"
        "</table></div>"
    )
    return ui.HTML(html)


def _plain_table(df: "pd.DataFrame") -> "ui.HTML":
    """Render a DataFrame as a plain sortable HTML table (no heatmap)."""
    th_style = (
        "padding:8px 12px;font-family:Manrope,sans-serif;font-size:11px;"
        "font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:0.04em;"
        "border-bottom:1px solid #e5e1dc;text-align:right;white-space:nowrap;cursor:pointer;"
    )
    th_first_style = th_style.replace("text-align:right;", "text-align:left;")
    td_base = (
        "padding:7px 12px;font-family:Manrope,sans-serif;font-size:13px;"
        "color:#021326;border-bottom:1px solid #f0eeea;text-align:right;"
    )
    td_first = td_base.replace("text-align:right;", "text-align:left;")

    headers = []
    for ci, col in enumerate(df.columns):
        s = th_first_style if ci == 0 else th_style
        headers.append(f'<th style="{s}">{col}</th>')

    rows_html = []
    for _, row in df.iterrows():
        cells = []
        for ci, col in enumerate(df.columns):
            style = td_first if ci == 0 else td_base
            cells.append(f'<td style="{style}">{row[col]}</td>')
        rows_html.append("<tr>" + "".join(cells) + "</tr>")

    total_row = _build_total_row(df, td_first, td_base)
    html = (
        '<div style="overflow-x:auto;">'
        '<table class="sortable-table" style="width:100%;border-collapse:collapse;">'
        "<thead><tr>" + "".join(headers) + "</tr></thead>"
        "<tbody>" + "".join(rows_html) + "</tbody>"
        "<tfoot>" + total_row + "</tfoot>"
        "</table></div>"
    )
    return ui.HTML(html)


def _heatmap_table(df: "pd.DataFrame", heatmap_cols: list) -> "ui.HTML":
    """Render a DataFrame as an HTML table with gold heatmap on specified columns."""
    r, g, b = _hex_to_rgb(_HEATMAP_COLOR)

    # Pre-compute per-column min/max for numeric scaling
    col_ranges = {}
    for col in heatmap_cols:
        if col not in df.columns:
            continue
        # Values may be formatted strings — parse back to float for scaling
        def _to_num(v):
            if isinstance(v, (int, float)):
                return float(v)
            try:
                return float(str(v).replace(",", "").replace("%", ""))
            except Exception:
                return None
        nums = [_to_num(v) for v in df[col] if _to_num(v) is not None]
        col_ranges[col] = (min(nums), max(nums)) if nums else (0, 1)

    # Build HTML
    th_style = (
        "padding:8px 12px;font-family:Manrope,sans-serif;font-size:11px;"
        "font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:0.04em;"
        "border-bottom:1px solid #e5e1dc;text-align:right;white-space:nowrap;cursor:pointer;"
    )
    th_first_style = th_style.replace("text-align:right;", "text-align:left;")
    td_base = (
        "padding:7px 12px;font-family:Manrope,sans-serif;font-size:13px;"
        "color:#021326;border-bottom:1px solid #f0eeea;text-align:right;"
    )
    td_first = td_base.replace("text-align:right;", "text-align:left;")

    rows_html = []
    for _, row in df.iterrows():
        cells = []
        for ci, col in enumerate(df.columns):
            val = row[col]
            style = td_first if ci == 0 else td_base
            if col in col_ranges:
                def _to_num(v):
                    if isinstance(v, (int, float)):
                        return float(v)
                    try:
                        return float(str(v).replace(",", "").replace("%", ""))
                    except Exception:
                        return None
                num = _to_num(val)
                if num is not None:
                    lo, hi = col_ranges[col]
                    ratio = (num - lo) / (hi - lo) if hi > lo else 0
                    alpha = round(0.08 + ratio * 0.62, 3)
                    style += f"background:rgba({r},{g},{b},{alpha});"
            cells.append(f'<td style="{style}">{val}</td>')
        rows_html.append("<tr>" + "".join(cells) + "</tr>")

    headers = []
    for ci, col in enumerate(df.columns):
        s = th_first_style if ci == 0 else th_style
        headers.append(f'<th style="{s}">{col}</th>')

    total_row = _build_total_row(df, td_first, td_base)
    html = (
        '<div style="overflow-x:auto;">'
        '<table class="sortable-table" style="width:100%;border-collapse:collapse;">'
        "<thead><tr>" + "".join(headers) + "</tr></thead>"
        "<tbody>" + "".join(rows_html) + "</tbody>"
        "<tfoot>" + total_row + "</tfoot>"
        "</table></div>"
    )
    return ui.HTML(html)


def _plotly_html(fig, no_toolbar=True):
    config = {"displayModeBar": False} if no_toolbar else {}
    return ui.HTML(fig.to_html(full_html=False, include_plotlyjs=False, config=config))


def _base_layout(height=360):
    return dict(
        font=dict(family="Manrope, sans-serif", color=CARNEGIE_NAVY, size=10.5),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=48, r=16, t=8, b=40), height=height,
        xaxis=dict(
            tickfont=dict(family="Manrope, sans-serif", size=10.5, color="#9B9893"),
            showgrid=False, title="",
        ),
        yaxis=dict(
            tickfont=dict(family="Manrope, sans-serif", size=10.5, color="#9B9893"),
            gridcolor="#F0EEEA", gridwidth=0.8, showline=False, nticks=5, title="",
        ),
        legend=dict(
            orientation="h", yanchor="top", y=-0.18, xanchor="center", x=0.5,
            font=dict(family="Manrope, sans-serif", size=10.5),
        ),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor=CARNEGIE_WHITE, bordercolor=CARNEGIE_GRAY_BORDER,
            font=dict(family="Inter, sans-serif", size=13, color=CARNEGIE_NAVY),
        ),
    )


def _safe_div(num, denom):
    """Safe division returning None on zero denominator."""
    return (num / denom) if denom and denom > 0 else None


def _fmt_delta(curr, prev, invert=False):
    """Build a YoY/MoM delta badge. invert=True means down is good (cost)."""
    if prev is None or prev == 0 or curr is None:
        return ui.tags.span("N/A", class_="kpi-badge kpi-badge--na")
    pct = (curr - prev) / abs(prev) * 100
    rounded = round(pct, 1)
    if rounded > 0:
        arrow, sentiment = "\u25b2", ("negative" if invert else "positive")
    elif rounded < 0:
        arrow, sentiment = "\u25bc", ("positive" if invert else "negative")
    else:
        arrow, sentiment = "", "neutral"
    return ui.tags.span(
        f"{arrow} {abs(rounded):.1f}% vs. PY",
        class_=f"kpi-badge kpi-badge--{sentiment}",
    )


def digital_server(input, output, session):
    """Register all digital performance outputs."""

    # ══════════════════════════════════════════════════════════
    # SHARED FILTERS
    # ══════════════════════════════════════════════════════════

    def _apply_dig_filters(df, date_col="day"):
        """Apply shared digital filters to a dataframe."""
        period = input.dig_period()
        if period and len(period) == 2 and date_col in df.columns:
            start, end = pd.Timestamp(period[0]), pd.Timestamp(period[1])
            df = df[(df[date_col] >= start) & (df[date_col] <= end)]

        grp = input.dig_group()
        if grp and len(grp) > 0 and "group_name" in df.columns:
            df = df[df["group_name"].isin(grp)]

        sub = input.dig_subgroup()
        if sub and len(sub) > 0 and "subgroup_name" in df.columns:
            df = df[df["subgroup_name"].isin(sub)]

        prod = input.dig_product()
        if prod and len(prod) > 0 and "product_name" in df.columns:
            df = df[df["product_name"].isin(prod)]

        camp = input.dig_campaign()
        if camp and len(camp) > 0 and "campaign_name" in df.columns:
            df = df[df["campaign_name"].isin(camp)]

        return df

    def _apply_dig_filters_monthly(df):
        """Apply filters to monthly-grain data (no day column)."""
        period = input.dig_period()
        if period and len(period) == 2:
            start, end = pd.Timestamp(period[0]), pd.Timestamp(period[1])
            # Build month start from event_year/event_month
            df = df.copy()
            df["_month_start"] = pd.to_datetime(
                df["event_year"].astype(str) + "-" + df["event_month"].astype(str).str.zfill(2) + "-01"
            )
            df = df[(df["_month_start"] >= start.replace(day=1)) &
                    (df["_month_start"] <= end)]
            df = df.drop(columns=["_month_start"])

        grp = input.dig_group()
        if grp and len(grp) > 0 and "group_name" in df.columns:
            df = df[df["group_name"].isin(grp)]
        sub = input.dig_subgroup()
        if sub and len(sub) > 0 and "subgroup_name" in df.columns:
            df = df[df["subgroup_name"].isin(sub)]
        prod = input.dig_product()
        if prod and len(prod) > 0 and "product_name" in df.columns:
            df = df[df["product_name"].isin(prod)]
        camp = input.dig_campaign()
        if camp and len(camp) > 0 and "campaign_name" in df.columns:
            df = df[df["campaign_name"].isin(camp)]
        return df

    @reactive.calc
    def _dig_q8():
        return _apply_dig_filters(Q8.copy())

    @reactive.calc
    def _dig_q8_prior():
        """Prior period for Q8 — shift date range back by same duration."""
        df = Q8.copy()
        period = input.dig_period()
        if period and len(period) == 2:
            start, end = pd.Timestamp(period[0]), pd.Timestamp(period[1])
            duration = end - start
            prior_end = start - pd.Timedelta(days=1)
            prior_start = prior_end - duration
            df = df[(df["day"] >= prior_start) & (df["day"] <= prior_end)]
        else:
            df = df.iloc[0:0]  # empty

        grp = input.dig_group()
        if grp and len(grp) > 0:
            df = df[df["group_name"].isin(grp)]
        sub = input.dig_subgroup()
        if sub and len(sub) > 0:
            df = df[df["subgroup_name"].isin(sub)]
        prod = input.dig_product()
        if prod and len(prod) > 0:
            df = df[df["product_name"].isin(prod)]
        camp = input.dig_campaign()
        if camp and len(camp) > 0:
            df = df[df["campaign_name"].isin(camp)]
        return df

    @reactive.calc
    def _dig_q9():
        return _apply_dig_filters(Q9.copy())

    @reactive.calc
    def _dig_q9_prior():
        df = Q9.copy()
        period = input.dig_period()
        if period and len(period) == 2:
            start, end = pd.Timestamp(period[0]), pd.Timestamp(period[1])
            duration = end - start
            prior_end = start - pd.Timedelta(days=1)
            prior_start = prior_end - duration
            df = df[(df["day"] >= prior_start) & (df["day"] <= prior_end)]
        else:
            df = df.iloc[0:0]

        grp = input.dig_group()
        if grp and len(grp) > 0:
            df = df[df["group_name"].isin(grp)]
        sub = input.dig_subgroup()
        if sub and len(sub) > 0:
            df = df[df["subgroup_name"].isin(sub)]
        prod = input.dig_product()
        if prod and len(prod) > 0:
            df = df[df["product_name"].isin(prod)]
        camp = input.dig_campaign()
        if camp and len(camp) > 0:
            df = df[df["campaign_name"].isin(camp)]
        return df

    @reactive.calc
    def _dig_q8_yoy():
        """Same months as selected period but one year prior (Year-over-Year)."""
        df = Q8.copy()
        period = input.dig_period()
        if period and len(period) == 2:
            start, end = pd.Timestamp(period[0]), pd.Timestamp(period[1])
            yoy_start = start.replace(year=start.year - 1)
            yoy_end   = end.replace(year=end.year - 1)
            df = df[(df["day"] >= yoy_start) & (df["day"] <= yoy_end)]
        else:
            df = df.iloc[0:0]
        grp = input.dig_group()
        if grp and len(grp) > 0:
            df = df[df["group_name"].isin(grp)]
        sub = input.dig_subgroup()
        if sub and len(sub) > 0:
            df = df[df["subgroup_name"].isin(sub)]
        prod = input.dig_product()
        if prod and len(prod) > 0:
            df = df[df["product_name"].isin(prod)]
        camp = input.dig_campaign()
        if camp and len(camp) > 0:
            df = df[df["campaign_name"].isin(camp)]
        return df

    @reactive.calc
    def _dig_q9_yoy():
        """Same months as selected period but one year prior (YoY) for Q9."""
        df = Q9.copy()
        period = input.dig_period()
        if period and len(period) == 2:
            start, end = pd.Timestamp(period[0]), pd.Timestamp(period[1])
            yoy_start = start.replace(year=start.year - 1)
            yoy_end   = end.replace(year=end.year - 1)
            df = df[(df["day"] >= yoy_start) & (df["day"] <= yoy_end)]
        else:
            df = df.iloc[0:0]
        grp = input.dig_group()
        if grp and len(grp) > 0:
            df = df[df["group_name"].isin(grp)]
        sub = input.dig_subgroup()
        if sub and len(sub) > 0:
            df = df[df["subgroup_name"].isin(sub)]
        prod = input.dig_product()
        if prod and len(prod) > 0:
            df = df[df["product_name"].isin(prod)]
        camp = input.dig_campaign()
        if camp and len(camp) > 0:
            df = df[df["campaign_name"].isin(camp)]
        return df

    # ══════════════════════════════════════════════════════════
    # TAB 1: OVERVIEW
    # ══════════════════════════════════════════════════════════

    # --- KPI Cards ---

    @render.text
    def dig_key_interactions():
        v = _dig_q8()["total_interactions"].sum()
        return f"{v:,.1f}"

    @render.ui
    def dig_key_interactions_delta():
        curr = _dig_q8()["total_interactions"].sum()
        prev = _dig_q8_prior()["total_interactions"].sum()
        return _fmt_delta(curr, prev)

    @render.text
    def dig_cpi():
        df = _dig_q8()
        return fmt_currency(_safe_div(df["budget"].sum(), df["total_interactions"].sum()))

    @render.ui
    def dig_cpi_delta():
        df_c, df_p = _dig_q8(), _dig_q8_prior()
        curr = _safe_div(df_c["budget"].sum(), df_c["total_interactions"].sum())
        prev = _safe_div(df_p["budget"].sum(), df_p["total_interactions"].sum())
        return _fmt_delta(curr, prev, invert=True)

    @render.text
    def dig_inquiry_int():
        v = _dig_q9()[_dig_q9()["interaction_category"] == "RFI/Lead Gen"]["total_interactions"].sum()
        return f"{v:,.1f}"

    @render.ui
    def dig_inquiry_int_delta():
        curr = _dig_q9()[_dig_q9()["interaction_category"] == "RFI/Lead Gen"]["total_interactions"].sum()
        prev = _dig_q9_prior()
        prev_v = prev[prev["interaction_category"] == "RFI/Lead Gen"]["total_interactions"].sum() if not prev.empty else 0
        return _fmt_delta(curr, prev_v)

    @render.text
    def dig_visit_int():
        v = _dig_q9()[_dig_q9()["interaction_category"] == "Visit/Event"]["total_interactions"].sum()
        return f"{v:,.1f}"

    @render.ui
    def dig_visit_int_delta():
        curr = _dig_q9()[_dig_q9()["interaction_category"] == "Visit/Event"]["total_interactions"].sum()
        prev = _dig_q9_prior()
        prev_v = prev[prev["interaction_category"] == "Visit/Event"]["total_interactions"].sum() if not prev.empty else 0
        return _fmt_delta(curr, prev_v)

    @render.text
    def dig_apply_int():
        v = _dig_q9()[_dig_q9()["interaction_category"] == "Apply"]["total_interactions"].sum()
        return f"{v:,.1f}"

    @render.ui
    def dig_apply_int_delta():
        curr = _dig_q9()[_dig_q9()["interaction_category"] == "Apply"]["total_interactions"].sum()
        prev = _dig_q9_prior()
        prev_v = prev[prev["interaction_category"] == "Apply"]["total_interactions"].sum() if not prev.empty else 0
        return _fmt_delta(curr, prev_v)

    # --- Engagement & Spend metrics ---

    @render.text
    def dig_budget():
        return fmt_currency(_dig_q8()["budget"].sum())

    @render.ui
    def dig_budget_delta():
        return _fmt_delta(_dig_q8()["budget"].sum(), _dig_q8_prior()["budget"].sum(), invert=True)

    @render.text
    def dig_cpc():
        df = _dig_q8()
        return fmt_currency(_safe_div(df["budget"].sum(), df["clicks"].sum()))

    @render.ui
    def dig_cpc_delta():
        df_c, df_p = _dig_q8(), _dig_q8_prior()
        return _fmt_delta(
            _safe_div(df_c["budget"].sum(), df_c["clicks"].sum()),
            _safe_div(df_p["budget"].sum(), df_p["clicks"].sum()),
            invert=True,
        )

    @render.text
    def dig_direct_conv():
        return f"{_dig_q8()['direct_conversions'].sum():,.1f}"

    @render.ui
    def dig_direct_conv_delta():
        return _fmt_delta(
            _dig_q8()["direct_conversions"].sum(),
            _dig_q8_prior()["direct_conversions"].sum(),
        )

    @render.text
    def dig_cpdc():
        df = _dig_q8()
        return fmt_currency(_safe_div(df["budget"].sum(), df["direct_conversions"].sum()))

    @render.ui
    def dig_cpdc_delta():
        df_c, df_p = _dig_q8(), _dig_q8_prior()
        return _fmt_delta(
            _safe_div(df_c["budget"].sum(), df_c["direct_conversions"].sum()),
            _safe_div(df_p["budget"].sum(), df_p["direct_conversions"].sum()),
            invert=True,
        )

    @render.text
    def dig_ipl():
        return fmt_number(_dig_q8()["in_platform_leads"].sum())

    @render.ui
    def dig_ipl_delta():
        return _fmt_delta(
            _dig_q8()["in_platform_leads"].sum(),
            _dig_q8_prior()["in_platform_leads"].sum(),
        )

    @render.text
    def dig_cpipl():
        df = _dig_q8()
        return fmt_currency(_safe_div(df["budget"].sum(), df["in_platform_leads"].sum()))

    @render.ui
    def dig_cpipl_delta():
        df_c, df_p = _dig_q8(), _dig_q8_prior()
        return _fmt_delta(
            _safe_div(df_c["budget"].sum(), df_c["in_platform_leads"].sum()),
            _safe_div(df_p["budget"].sum(), df_p["in_platform_leads"].sum()),
            invert=True,
        )

    @render.text
    def dig_vtc():
        return fmt_number(_dig_q8()["view_through_conversions"].sum())

    @render.ui
    def dig_vtc_delta():
        return _fmt_delta(
            _dig_q8()["view_through_conversions"].sum(),
            _dig_q8_prior()["view_through_conversions"].sum(),
        )

    @render.text
    def dig_cptc():
        df = _dig_q8()
        return fmt_currency(_safe_div(df["budget"].sum(), df["total_interactions"].sum()))

    @render.ui
    def dig_cptc_delta():
        df_c, df_p = _dig_q8(), _dig_q8_prior()
        return _fmt_delta(
            _safe_div(df_c["budget"].sum(), df_c["total_interactions"].sum()),
            _safe_div(df_p["budget"].sum(), df_p["total_interactions"].sum()),
            invert=True,
        )

    # --- Trending Chart ---

    @render.ui
    def dig_trending_chart():
        df_curr = _dig_q8()
        df_prior = _dig_q8_prior()
        if df_curr.empty:
            return ui.tags.div("No data available.", class_="empty-state")

        # Daily aggregation — one row per day in the selected period
        curr_daily = (
            df_curr.groupby("day")["total_interactions"].sum()
            .reset_index()
            .sort_values("day")
        )

        # Build full date spine for the selected period so every day shows on x-axis
        period = input.dig_period()
        if period and len(period) == 2:
            start_dt = pd.Timestamp(period[0])
            end_dt   = pd.Timestamp(period[1])
        else:
            start_dt = curr_daily["day"].min()
            end_dt   = curr_daily["day"].max()

        all_days = pd.DataFrame({"day": pd.date_range(start_dt, end_dt, freq="D")})
        curr_daily = all_days.merge(curr_daily, on="day", how="left").fillna(0)

        # x = actual dates so hover fires on every day; tick labels only on odd days
        odd_days = curr_daily[curr_daily["day"].dt.day % 2 == 1]["day"]
        tickvals = odd_days.tolist()
        ticktext = [pd.Timestamp(d).strftime("%b ") + str(pd.Timestamp(d).day) for d in odd_days]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=curr_daily["day"], y=curr_daily["total_interactions"],
            mode="lines+markers", name="Total Conversions",
            line=dict(color="#EA332D", width=2),
            marker=dict(color="#EA332D", size=4),
            hovertemplate="%{x|%b %e}<br>Total Conversions: %{y:,.0f}<extra></extra>",
        ))

        if not df_prior.empty:
            prior_daily = (
                df_prior.groupby("day")["total_interactions"].sum()
                .reset_index()
                .sort_values("day")
            )
            # Align prior days to same day-of-month positions as current period
            prior_daily["day_num"] = prior_daily["day"].dt.day
            curr_daily["day_num"] = curr_daily["day"].dt.day
            merged = curr_daily[["day", "day_num"]].merge(
                prior_daily[["day_num", "total_interactions"]], on="day_num", how="left"
            ).fillna(0)
            fig.add_trace(go.Scatter(
                x=merged["day"], y=merged["total_interactions"],
                mode="lines+markers", name="Total Conversions (previous year)",
                line=dict(color="#C99D44", width=1.8, dash="dash"),
                marker=dict(color="#C99D44", size=3),
                hovertemplate="%{x|%b %e}<br>Total Conversions (prev): %{y:,.0f}<extra></extra>",
            ))

        layout = _base_layout(320)
        layout["xaxis"] = dict(
            tickvals=tickvals, ticktext=ticktext,
            tickfont=dict(family="Manrope, sans-serif", size=10, color="#9B9893"),
            showgrid=False, title="", tickangle=0,
        )
        fig.update_layout(**layout)
        return _plotly_html(fig)

    # --- Key Interaction Categories bar chart ---

    @render.ui
    def dig_key_interaction_categories():
        df = _dig_q9()
        if df.empty:
            return ui.tags.div("No data available.", class_="empty-state")

        cats_order = ["RFI/Lead Gen", "Visit/Event", "Apply", "Enroll/Deposit", "Other"]
        agg = df.groupby("interaction_category")["total_interactions"].sum().reset_index()
        # Keep only known categories, preserve order
        agg = agg[agg["interaction_category"].isin(cats_order)].copy()
        agg["_order"] = agg["interaction_category"].map({c: i for i, c in enumerate(cats_order)})
        agg = agg.sort_values("_order")

        colors = ["#021326", "#A4B9D3", "#C99D44", "#6B8F71", "#8B7355"]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=agg["interaction_category"],
            y=agg["total_interactions"],
            marker_color=[colors[i % len(colors)] for i in range(len(agg))],
            hovertemplate="%{x}<br>Total Conversions: %{y:,.0f}<extra></extra>",
            showlegend=False,
            text=[f"{v:,.0f}" for v in agg["total_interactions"]],
            textposition="inside",
            textfont=dict(family="Manrope, sans-serif", size=11, color="#ffffff"),
        ))
        layout = _base_layout(320)
        layout["margin"] = dict(l=16, r=16, t=8, b=40)
        layout["xaxis"]["tickfont"] = dict(family="Manrope, sans-serif", size=10, color="#9B9893")
        layout["xaxis"]["tickangle"] = 0
        layout["yaxis"]["visible"] = False
        fig.update_layout(**layout)
        return _plotly_html(fig)

    # --- Cost Per Total Conversion line chart ---

    @render.ui
    def dig_cost_per_total_conv():
        df_curr = _dig_q8()
        df_prior = _dig_q8_prior()
        if df_curr.empty:
            return ui.tags.div("No data available.", class_="empty-state")

        # Build full date spine for current period
        period = input.dig_period()
        if period and len(period) == 2:
            start_dt = pd.Timestamp(period[0])
            end_dt   = pd.Timestamp(period[1])
        else:
            start_dt = df_curr["day"].min()
            end_dt   = df_curr["day"].max()

        all_days = pd.DataFrame({"day": pd.date_range(start_dt, end_dt, freq="D")})

        curr_daily = (
            df_curr.groupby("day")[["budget", "total_interactions"]].sum()
            .reset_index().sort_values("day")
        )
        curr_daily = all_days.merge(curr_daily, on="day", how="left").fillna(0)
        curr_daily["cptc"] = curr_daily.apply(
            lambda r: _safe_div(r["budget"], r["total_interactions"]), axis=1
        )

        odd_days = curr_daily[curr_daily["day"].dt.day % 2 == 1]["day"]
        tickvals = odd_days.tolist()
        ticktext = [pd.Timestamp(d).strftime("%b ") + str(pd.Timestamp(d).day) for d in odd_days]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=curr_daily["day"], y=curr_daily["cptc"],
            mode="lines+markers", name="Cost Per Total Conversion",
            line=dict(color="#EA332D", width=2),
            marker=dict(color="#EA332D", size=4),
            hovertemplate="%{x|%b %e}<br>Cost/Conv: $%{y:,.2f}<extra></extra>",
        ))

        if not df_prior.empty:
            prior_daily = (
                df_prior.groupby("day")[["budget", "total_interactions"]].sum()
                .reset_index().sort_values("day")
            )
            prior_daily["cptc"] = prior_daily.apply(
                lambda r: _safe_div(r["budget"], r["total_interactions"]), axis=1
            )
            prior_daily["day_num"] = prior_daily["day"].dt.day
            curr_daily["day_num"] = curr_daily["day"].dt.day
            merged = curr_daily[["day", "day_num"]].merge(
                prior_daily[["day_num", "cptc"]], on="day_num", how="left"
            )
            fig.add_trace(go.Scatter(
                x=merged["day"], y=merged["cptc"],
                mode="lines+markers", name="Cost Per Total Conversion (previous month)",
                line=dict(color="#C99D44", width=1.8, dash="dash"),
                marker=dict(color="#C99D44", size=3),
                hovertemplate="%{x|%b %e}<br>Cost/Conv (prev): $%{y:,.2f}<extra></extra>",
            ))

        layout = _base_layout(320)
        layout["yaxis"]["tickprefix"] = "$"
        layout["xaxis"] = dict(
            tickvals=tickvals, ticktext=ticktext,
            tickfont=dict(family="Manrope, sans-serif", size=10, color="#9B9893"),
            showgrid=False, title="", tickangle=0,
        )
        fig.update_layout(**layout)
        return _plotly_html(fig)

    # ══════════════════════════════════════════════════════════
    # TAB 1b: OVERVIEW YoY  (same outputs, _yoy suffix, compare curr vs prior year)
    # ══════════════════════════════════════════════════════════

    @render.text
    def dig_impressions_yoy():
        return fmt_number(_dig_q8()["impressions"].sum())

    @render.ui
    def dig_impressions_yoy_delta():
        return _fmt_delta(_dig_q8()["impressions"].sum(), _dig_q8_yoy()["impressions"].sum())

    @render.text
    def dig_clicks_yoy():
        return fmt_number(_dig_q8()["clicks"].sum())

    @render.ui
    def dig_clicks_yoy_delta():
        return _fmt_delta(_dig_q8()["clicks"].sum(), _dig_q8_yoy()["clicks"].sum())

    @render.text
    def dig_ctr_yoy():
        df = _dig_q8()
        v = _safe_div(df["clicks"].sum(), df["impressions"].sum())
        return f"{v * 100:.2f}%" if v is not None else "—"

    @render.ui
    def dig_ctr_yoy_delta():
        df_c, df_p = _dig_q8(), _dig_q8_yoy()
        curr = _safe_div(df_c["clicks"].sum(), df_c["impressions"].sum())
        prev = _safe_div(df_p["clicks"].sum(), df_p["impressions"].sum())
        return _fmt_delta(curr, prev)

    @render.text
    def dig_total_conv_yoy():
        df = _dig_q8()
        v = df["direct_conversions"].sum() + df["view_through_conversions"].sum() + df["in_platform_leads"].sum()
        return fmt_number(v)

    @render.ui
    def dig_total_conv_yoy_delta():
        df_c, df_p = _dig_q8(), _dig_q8_yoy()
        curr = df_c["direct_conversions"].sum() + df_c["view_through_conversions"].sum() + df_c["in_platform_leads"].sum()
        prev = df_p["direct_conversions"].sum() + df_p["view_through_conversions"].sum() + df_p["in_platform_leads"].sum()
        return _fmt_delta(curr, prev)

    @render.text
    def dig_conv_rate_yoy():
        df = _dig_q8()
        total_conv = df["direct_conversions"].sum() + df["view_through_conversions"].sum() + df["in_platform_leads"].sum()
        v = _safe_div(total_conv, df["clicks"].sum())
        return f"{v * 100:.2f}%" if v is not None else "—"

    @render.ui
    def dig_conv_rate_yoy_delta():
        df_c, df_p = _dig_q8(), _dig_q8_yoy()
        tc_c = df_c["direct_conversions"].sum() + df_c["view_through_conversions"].sum() + df_c["in_platform_leads"].sum()
        tc_p = df_p["direct_conversions"].sum() + df_p["view_through_conversions"].sum() + df_p["in_platform_leads"].sum()
        curr = _safe_div(tc_c, df_c["clicks"].sum())
        prev = _safe_div(tc_p, df_p["clicks"].sum())
        return _fmt_delta(curr, prev)

    @render.text
    def dig_key_interactions_yoy():
        v = _dig_q8()["total_interactions"].sum()
        return f"{v:,.1f}"

    @render.ui
    def dig_key_interactions_delta_yoy():
        return _fmt_delta(_dig_q8()["total_interactions"].sum(), _dig_q8_yoy()["total_interactions"].sum())

    @render.text
    def dig_cpi_yoy():
        df = _dig_q8()
        return fmt_currency(_safe_div(df["budget"].sum(), df["total_interactions"].sum()))

    @render.ui
    def dig_cpi_delta_yoy():
        df_c, df_p = _dig_q8(), _dig_q8_yoy()
        return _fmt_delta(
            _safe_div(df_c["budget"].sum(), df_c["total_interactions"].sum()),
            _safe_div(df_p["budget"].sum(), df_p["total_interactions"].sum()),
            invert=True,
        )

    @render.text
    def dig_inquiry_int_yoy():
        v = _dig_q9()[_dig_q9()["interaction_category"] == "RFI/Lead Gen"]["total_interactions"].sum()
        return f"{v:,.1f}"

    @render.ui
    def dig_inquiry_int_delta_yoy():
        curr = _dig_q9()[_dig_q9()["interaction_category"] == "RFI/Lead Gen"]["total_interactions"].sum()
        py = _dig_q9_yoy()
        prev_v = py[py["interaction_category"] == "RFI/Lead Gen"]["total_interactions"].sum() if not py.empty else 0
        return _fmt_delta(curr, prev_v)

    @render.text
    def dig_visit_int_yoy():
        v = _dig_q9()[_dig_q9()["interaction_category"] == "Visit/Event"]["total_interactions"].sum()
        return f"{v:,.1f}"

    @render.ui
    def dig_visit_int_delta_yoy():
        curr = _dig_q9()[_dig_q9()["interaction_category"] == "Visit/Event"]["total_interactions"].sum()
        py = _dig_q9_yoy()
        prev_v = py[py["interaction_category"] == "Visit/Event"]["total_interactions"].sum() if not py.empty else 0
        return _fmt_delta(curr, prev_v)

    @render.text
    def dig_apply_int_yoy():
        v = _dig_q9()[_dig_q9()["interaction_category"] == "Apply"]["total_interactions"].sum()
        return f"{v:,.1f}"

    @render.ui
    def dig_apply_int_delta_yoy():
        curr = _dig_q9()[_dig_q9()["interaction_category"] == "Apply"]["total_interactions"].sum()
        py = _dig_q9_yoy()
        prev_v = py[py["interaction_category"] == "Apply"]["total_interactions"].sum() if not py.empty else 0
        return _fmt_delta(curr, prev_v)

    @render.text
    def dig_budget_yoy():
        return fmt_currency(_dig_q8()["budget"].sum())

    @render.ui
    def dig_budget_yoy_delta():
        return _fmt_delta(_dig_q8()["budget"].sum(), _dig_q8_yoy()["budget"].sum(), invert=True)

    @render.text
    def dig_cpc_yoy():
        df = _dig_q8()
        return fmt_currency(_safe_div(df["budget"].sum(), df["clicks"].sum()))

    @render.ui
    def dig_cpc_yoy_delta():
        df_c, df_p = _dig_q8(), _dig_q8_yoy()
        return _fmt_delta(
            _safe_div(df_c["budget"].sum(), df_c["clicks"].sum()),
            _safe_div(df_p["budget"].sum(), df_p["clicks"].sum()),
            invert=True,
        )

    @render.text
    def dig_direct_conv_yoy():
        return f"{_dig_q8()['direct_conversions'].sum():,.1f}"

    @render.ui
    def dig_direct_conv_yoy_delta():
        return _fmt_delta(_dig_q8()["direct_conversions"].sum(), _dig_q8_yoy()["direct_conversions"].sum())

    @render.text
    def dig_cpdc_yoy():
        df = _dig_q8()
        return fmt_currency(_safe_div(df["budget"].sum(), df["direct_conversions"].sum()))

    @render.ui
    def dig_cpdc_yoy_delta():
        df_c, df_p = _dig_q8(), _dig_q8_yoy()
        return _fmt_delta(
            _safe_div(df_c["budget"].sum(), df_c["direct_conversions"].sum()),
            _safe_div(df_p["budget"].sum(), df_p["direct_conversions"].sum()),
            invert=True,
        )

    @render.text
    def dig_ipl_yoy():
        return fmt_number(_dig_q8()["in_platform_leads"].sum())

    @render.ui
    def dig_ipl_yoy_delta():
        return _fmt_delta(_dig_q8()["in_platform_leads"].sum(), _dig_q8_yoy()["in_platform_leads"].sum())

    @render.text
    def dig_cpipl_yoy():
        df = _dig_q8()
        return fmt_currency(_safe_div(df["budget"].sum(), df["in_platform_leads"].sum()))

    @render.ui
    def dig_cpipl_yoy_delta():
        df_c, df_p = _dig_q8(), _dig_q8_yoy()
        return _fmt_delta(
            _safe_div(df_c["budget"].sum(), df_c["in_platform_leads"].sum()),
            _safe_div(df_p["budget"].sum(), df_p["in_platform_leads"].sum()),
            invert=True,
        )

    @render.text
    def dig_vtc_yoy():
        return fmt_number(_dig_q8()["view_through_conversions"].sum())

    @render.ui
    def dig_vtc_yoy_delta():
        return _fmt_delta(_dig_q8()["view_through_conversions"].sum(), _dig_q8_yoy()["view_through_conversions"].sum())

    @render.text
    def dig_cptc_yoy():
        df = _dig_q8()
        return fmt_currency(_safe_div(df["budget"].sum(), df["total_interactions"].sum()))

    @render.ui
    def dig_cptc_yoy_delta():
        df_c, df_p = _dig_q8(), _dig_q8_yoy()
        return _fmt_delta(
            _safe_div(df_c["budget"].sum(), df_c["total_interactions"].sum()),
            _safe_div(df_p["budget"].sum(), df_p["total_interactions"].sum()),
            invert=True,
        )

    @render.ui
    def dig_trending_chart_yoy():
        df_curr = _dig_q8()
        df_prior = _dig_q8_yoy()
        if df_curr.empty:
            return ui.tags.div("No data available.", class_="empty-state")

        # Group current period by month
        df_curr = df_curr.copy()
        df_curr["month"] = df_curr["day"].dt.to_period("M")
        curr_monthly = (
            df_curr.groupby("month")["impressions"].sum()
            .reset_index().sort_values("month")
        )
        curr_monthly["month_dt"] = curr_monthly["month"].dt.to_timestamp()
        curr_monthly["label"] = curr_monthly["month_dt"].dt.strftime("%b %y")
        # month position index (0, 1, 2, …) for aligning prior year
        curr_monthly = curr_monthly.reset_index(drop=True)
        curr_monthly["month_pos"] = curr_monthly.index

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=curr_monthly["month_dt"], y=curr_monthly["impressions"],
            mode="lines+markers", name="Total Impressions",
            line=dict(color="#EA332D", width=2),
            marker=dict(color="#EA332D", size=4),
            hovertemplate="%{x|%b %y}<br>Total Impressions: %{y:,.0f}<extra></extra>",
        ))

        if not df_prior.empty:
            df_prior = df_prior.copy()
            df_prior["month"] = df_prior["day"].dt.to_period("M")
            prior_monthly = (
                df_prior.groupby("month")["impressions"].sum()
                .reset_index().sort_values("month")
            ).reset_index(drop=True)
            prior_monthly["month_pos"] = prior_monthly.index
            # Align prior months to current month positions on x-axis
            prior_monthly["prior_label"] = prior_monthly["month"].dt.strftime("%b %y")
            merged = curr_monthly[["month_dt", "month_pos"]].merge(
                prior_monthly[["month_pos", "impressions", "prior_label"]], on="month_pos", how="left"
            )
            merged["impressions"] = merged["impressions"].fillna(0)
            merged["prior_label"] = merged["prior_label"].fillna("")
            fig.add_trace(go.Scatter(
                x=merged["month_dt"], y=merged["impressions"],
                customdata=merged["prior_label"],
                mode="lines+markers", name="Total Impressions (previous year)",
                line=dict(color="#C99D44", width=1.8, dash="dash"),
                marker=dict(color="#C99D44", size=3),
                hovertemplate="%{customdata}<br>Total Impressions (prev): %{y:,.0f}<extra></extra>",
            ))

        layout = _base_layout(320)
        layout["xaxis"] = dict(
            tickvals=curr_monthly["month_dt"].tolist(),
            ticktext=curr_monthly["label"].tolist(),
            tickfont=dict(family="Manrope, sans-serif", size=10, color="#9B9893"),
            showgrid=False, title="", tickangle=0,
        )
        fig.update_layout(**layout)
        return _plotly_html(fig)

    @render.ui
    def dig_strategy_bar_yoy():
        df = _dig_q8()
        if df.empty:
            return ui.tags.div("No data available.", class_="empty-state")
        strat = df.groupby("product_name")["impressions"].sum().sort_values(ascending=True).reset_index()
        strat = strat[strat["impressions"] > 0]
        if strat.empty:
            return ui.tags.div("No data available.", class_="empty-state")
        total = strat["impressions"].sum()
        strat["pct"] = (strat["impressions"] / total * 100).round(1)
        x_max = strat["impressions"].max() * 1.28
        fig = go.Figure(go.Bar(
            x=strat["impressions"], y=strat["product_name"],
            orientation="h", marker_color=CHART_COLORS[0],
            text=[f"{p:.1f}%" for p in strat["pct"]], textposition="outside",
            textfont=dict(family="Manrope, sans-serif", size=10, color=CARNEGIE_NAVY),
            hovertemplate="<b>%{y}</b><br>Impressions: %{x:,}<extra></extra>",
        ))
        layout = _base_layout(max(260, len(strat) * 28 + 60))
        layout["margin"] = dict(l=8, r=8, t=8, b=24, autoexpand=True)
        layout["xaxis"] = dict(showgrid=True, gridcolor="#F0EEEA", title="", range=[0, x_max])
        layout["yaxis"] = dict(showgrid=False, title="", automargin=True)
        fig.update_layout(**layout)
        return _plotly_html(fig)

    @render.ui
    def dig_strategy_trend_yoy():
        df = _dig_q8()
        if df.empty:
            return ui.tags.div("No data available.", class_="empty-state")
        top5 = df.groupby("product_name")["impressions"].sum().nlargest(5).index.tolist()
        df_top = df[df["product_name"].isin(top5)].copy()

        # Group by month for YoY page
        df_top["month"] = df_top["day"].dt.to_period("M")
        all_months = sorted(df_top["month"].unique())
        all_months_dt = [m.to_timestamp() for m in all_months]
        ticktext = [m.strftime("%b %y") for m in all_months_dt]

        fig = go.Figure()
        for i, prod in enumerate(top5):
            sub = (
                df_top[df_top["product_name"] == prod]
                .groupby("month")["impressions"].sum()
                .reset_index()
            )
            sub["month_dt"] = sub["month"].dt.to_timestamp()
            spine = pd.DataFrame({"month_dt": all_months_dt})
            sub = spine.merge(sub[["month_dt", "impressions"]], on="month_dt", how="left").fillna(0)
            fig.add_trace(go.Scatter(
                x=sub["month_dt"], y=sub["impressions"],
                mode="lines+markers", name=prod,
                line=dict(color=_STRATEGY_TREND_COLORS[i % len(_STRATEGY_TREND_COLORS)], width=2),
                marker=dict(color=_STRATEGY_TREND_COLORS[i % len(_STRATEGY_TREND_COLORS)], size=4),
                hovertemplate=f"<b>{prod}</b><br>%{{x|%b %y}}<br>Impressions: %{{y:,.0f}}<extra></extra>",
            ))

        layout = _base_layout(320)
        layout["xaxis"] = dict(
            tickvals=all_months_dt, ticktext=ticktext,
            tickfont=dict(family="Manrope, sans-serif", size=10, color="#9B9893"),
            showgrid=False, title="", tickangle=0,
        )
        fig.update_layout(**layout)
        return _plotly_html(fig)

    @render.ui
    def dig_subgroup_table_yoy():
        df_c = _dig_q8()
        df_p = _dig_q8_yoy()
        if df_c.empty:
            return ui.tags.div("No data available.", class_="empty-state")
        return _build_yoy_comparison_table(df_c, df_p, group_col="subgroup_name", label_col="Subgroup")

    @render.ui
    def dig_strategy_table_yoy():
        df_c = _dig_q8()
        df_p = _dig_q8_yoy()
        if df_c.empty:
            return ui.tags.div("No data available.", class_="empty-state")
        return _build_yoy_comparison_table(df_c, df_p, group_col="product_name", label_col="Strategy")

    @render.ui
    def dig_interactions_by_month_yoy():
        return ui.tags.div()  # placeholder — same as Overview

    @render.ui
    def dig_interactions_by_strategy_month_yoy():
        return ui.tags.div()  # placeholder — same as Overview

    # --- Strategy bar chart ---

    @render.ui
    def dig_strategy_bar():
        df = _dig_q8()
        if df.empty:
            return ui.tags.div("No data available.", class_="empty-state")

        strat = df.groupby("product_name")["impressions"].sum().sort_values(ascending=True).reset_index()
        strat = strat[strat["impressions"] > 0]
        if strat.empty:
            return ui.tags.div("No data available.", class_="empty-state")

        total = strat["impressions"].sum()
        strat["pct"] = (strat["impressions"] / total * 100).round(1)
        x_max = strat["impressions"].max() * 1.28

        fig = go.Figure(go.Bar(
            x=strat["impressions"], y=strat["product_name"],
            orientation="h", marker_color=CHART_COLORS[0],
            text=[f"{p:.1f}%" for p in strat["pct"]],
            textposition="outside",
            textfont=dict(family="Manrope, sans-serif", size=10, color=CARNEGIE_NAVY),
            hovertemplate="<b>%{y}</b><br>Impressions: %{x:,}<extra></extra>",
        ))
        layout = _base_layout(max(260, len(strat) * 28 + 60))
        layout["margin"] = dict(l=8, r=8, t=8, b=24, autoexpand=True)
        layout["xaxis"] = dict(showgrid=True, gridcolor="#F0EEEA", title="", range=[0, x_max])
        layout["yaxis"] = dict(showgrid=False, title="", automargin=True)
        fig.update_layout(**layout)
        return _plotly_html(fig)

    # --- Strategy trend ---

    _STRATEGY_TREND_COLORS = ["#A4B9D3", "#FBCFB1", "#E9DBF6", "#B3C7BD", "#FFF8B4"]

    @render.ui
    def dig_strategy_trend():
        df = _dig_q8()
        if df.empty:
            return ui.tags.div("No data available.", class_="empty-state")

        top5 = df.groupby("product_name")["impressions"].sum().nlargest(5).index.tolist()
        df_top = df[df["product_name"].isin(top5)].copy()

        period = input.dig_period()
        if period and len(period) == 2:
            start_dt = pd.Timestamp(period[0])
            end_dt   = pd.Timestamp(period[1])
        else:
            start_dt = df_top["day"].min()
            end_dt   = df_top["day"].max()

        all_days = pd.date_range(start_dt, end_dt, freq="D")
        odd_days = [d for d in all_days if d.day % 2 == 1]
        tickvals = odd_days
        ticktext = [d.strftime("%b ") + str(d.day) for d in odd_days]

        fig = go.Figure()
        for i, prod in enumerate(top5):
            sub = df_top[df_top["product_name"] == prod].groupby("day")["impressions"].sum().reset_index()
            spine = pd.DataFrame({"day": all_days})
            sub = spine.merge(sub, on="day", how="left").fillna(0)
            fig.add_trace(go.Scatter(
                x=sub["day"], y=sub["impressions"],
                mode="lines+markers", name=prod,
                line=dict(color=_STRATEGY_TREND_COLORS[i % len(_STRATEGY_TREND_COLORS)], width=2),
                marker=dict(color=_STRATEGY_TREND_COLORS[i % len(_STRATEGY_TREND_COLORS)], size=4),
                hovertemplate=f"<b>{prod}</b><br>%{{x|%b %e}}<br>Impressions: %{{y:,.0f}}<extra></extra>",
            ))

        layout = _base_layout(320)
        layout["xaxis"] = dict(
            tickvals=tickvals, ticktext=ticktext,
            tickfont=dict(family="Manrope, sans-serif", size=10, color="#9B9893"),
            showgrid=False, title="", tickangle=0,
        )
        fig.update_layout(**layout)
        return _plotly_html(fig)

    # --- Subgroup performance table ---

    @render.ui
    def dig_subgroup_table():
        df_c = _dig_q8()
        df_p = _dig_q8_prior()
        if df_c.empty:
            return ui.tags.div("No data available.", class_="empty-state")

        metrics = ["impressions", "clicks", "direct_conversions",
                   "view_through_conversions", "in_platform_leads", "total_interactions"]
        curr = df_c.groupby("subgroup_name")[metrics].sum().reset_index()
        curr["CTR"] = (curr["clicks"] / curr["impressions"].replace(0, float("nan")) * 100).round(2)
        for c in metrics:
            curr[c] = curr[c].round(0).astype(int)
        display = curr.sort_values("impressions", ascending=False).rename(columns={
            "subgroup_name": "Subgroup", "impressions": "Impressions",
            "clicks": "Clicks", "CTR": "CTR %",
            "direct_conversions": "Direct Conv.", "view_through_conversions": "View-through",
            "in_platform_leads": "In-Platform Leads", "total_interactions": "Total Interactions",
        })
        heatmap_cols = ["Impressions", "Clicks", "CTR %", "Direct Conv.",
                        "View-through", "In-Platform Leads", "Total Interactions"]
        show = ["Subgroup", "Impressions", "Clicks", "CTR %", "Direct Conv.",
                "View-through", "In-Platform Leads", "Total Interactions"]
        return _heatmap_table(display[[c for c in show if c in display.columns]], heatmap_cols)

    # --- Strategy performance table ---

    @render.ui
    def dig_strategy_table():
        df_c = _dig_q8()
        if df_c.empty:
            return ui.tags.div("No data available.", class_="empty-state")

        metrics = ["impressions", "clicks", "direct_conversions",
                   "view_through_conversions", "in_platform_leads", "total_interactions"]
        curr = df_c.groupby("product_name")[metrics].sum().reset_index()
        curr["CTR"] = (curr["clicks"] / curr["impressions"].replace(0, float("nan")) * 100).round(2)
        for c in metrics:
            curr[c] = curr[c].round(0).astype(int)
        display = curr.sort_values("impressions", ascending=False).rename(columns={
            "product_name": "Strategy", "impressions": "Impressions",
            "clicks": "Clicks", "CTR": "CTR %",
            "direct_conversions": "Direct Conv.", "view_through_conversions": "View-through",
            "in_platform_leads": "In-Platform Leads", "total_interactions": "Total Interactions",
        })
        heatmap_cols = ["Impressions", "Clicks", "CTR %", "Direct Conv.",
                        "View-through", "In-Platform Leads", "Total Interactions"]
        show = ["Strategy", "Impressions", "Clicks", "CTR %", "Direct Conv.",
                "View-through", "In-Platform Leads", "Total Interactions"]
        return _heatmap_table(display[[c for c in show if c in display.columns]], heatmap_cols)

    # --- Interactions by month & year ---

    @render.ui
    def dig_interactions_by_month():
        # Apply only non-date filters so all years/months are always visible
        df = Q8.copy()
        grp = input.dig_group()
        if grp and len(grp) > 0:
            df = df[df["group_name"].isin(grp)]
        sub = input.dig_subgroup()
        if sub and len(sub) > 0:
            df = df[df["subgroup_name"].isin(sub)]
        prod = input.dig_product()
        if prod and len(prod) > 0:
            df = df[df["product_name"].isin(prod)]
        camp = input.dig_campaign()
        if camp and len(camp) > 0:
            df = df[df["campaign_name"].isin(camp)]

        if df.empty:
            return ui.tags.div("No data available.", class_="empty-state")

        df = df.copy()
        df["year"] = df["day"].dt.year
        df["month_name"] = df["day"].dt.strftime("%b")

        # Keep only the last 3 years available in the data
        all_years = sorted(df["year"].unique())
        years_to_show = all_years[-3:]
        df = df[df["year"].isin(years_to_show)]

        pivot = df.groupby(["year", "month_name"])["total_interactions"].sum().reset_index()
        pivot_wide = pivot.pivot(index="year", columns="month_name", values="total_interactions").fillna(0)

        # Always show all 12 months as columns, even if no data
        month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                       "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        for m in month_order:
            if m not in pivot_wide.columns:
                pivot_wide[m] = 0
        pivot_wide = pivot_wide[month_order]
        pivot_wide["Grand Total"] = pivot_wide.sum(axis=1)
        pivot_wide = pivot_wide.reset_index().rename(columns={"year": "Year"})
        pivot_wide = pivot_wide.sort_values("Year", ascending=False)
        heatmap_cols = month_order + ["Grand Total"]
        for c in heatmap_cols:
            pivot_wide[c] = pivot_wide[c].apply(lambda v: f"{round(v):,}")
        return _heatmap_table(pivot_wide, heatmap_cols)

    # --- Interactions by strategy & month ---

    @render.ui
    def dig_interactions_by_strategy_month():
        # Bypass date filter — always show last 12 months available in data
        df = Q8.copy()
        grp = input.dig_group()
        if grp and len(grp) > 0:
            df = df[df["group_name"].isin(grp)]
        sub = input.dig_subgroup()
        if sub and len(sub) > 0:
            df = df[df["subgroup_name"].isin(sub)]
        prod = input.dig_product()
        if prod and len(prod) > 0:
            df = df[df["product_name"].isin(prod)]
        camp = input.dig_campaign()
        if camp and len(camp) > 0:
            df = df[df["campaign_name"].isin(camp)]
        if df.empty:
            return ui.tags.div("No data available.", class_="empty-state")

        df = df.copy()
        df["ym"] = df["day"].dt.to_period("M")

        # Determine last 12 months present in the data
        all_months = sorted(df["ym"].unique())
        months_to_show = all_months[-12:]

        df = df[df["ym"].isin(months_to_show)]

        # Build display label: "Nov 25", "Jan 26"
        def _label(period):
            return period.strftime("%b %y")  # e.g. "Nov 25"

        df["month_label"] = df["ym"].apply(_label)
        label_order = [_label(m) for m in months_to_show]

        pivot = df.groupby(["product_name", "month_label"])["total_interactions"].sum().reset_index()
        pivot_wide = pivot.pivot(index="product_name", columns="month_label", values="total_interactions").fillna(0)

        # Ensure all 12 months are columns in order
        for lbl in label_order:
            if lbl not in pivot_wide.columns:
                pivot_wide[lbl] = 0
        pivot_wide = pivot_wide[label_order]

        pivot_wide["Grand Total"] = pivot_wide.sum(axis=1)
        pivot_wide = pivot_wide.sort_values("Grand Total", ascending=False).reset_index()
        pivot_wide = pivot_wide.rename(columns={"product_name": "Strategy"})
        heatmap_cols = label_order + ["Grand Total"]
        for c in heatmap_cols:
            pivot_wide[c] = pivot_wide[c].apply(lambda v: f"{round(v):,}" if isinstance(v, (int, float)) else v)
        return _heatmap_table(pivot_wide, heatmap_cols)

    # ══════════════════════════════════════════════════════════
    # TAB 2: INTERACTIONS
    # ══════════════════════════════════════════════════════════

    @reactive.effect
    def _update_interaction_filters():
        df = _dig_q9()
        cats = sorted([c for c in df["interaction_category"].unique() if c])
        ui.update_selectize("dig_interaction_cat", choices=cats, selected=[])
        names = sorted([n for n in df["conversion_name"].unique() if n and n != "Unknown"])
        ui.update_selectize("dig_conversion_name", choices=names, selected=[])

    @reactive.calc
    def _dig_q9_filtered():
        """Q9 with tab-specific filters applied."""
        df = _dig_q9()
        cat = input.dig_interaction_cat()
        if cat and len(cat) > 0:
            df = df[df["interaction_category"].isin(cat)]
        cn = input.dig_conversion_name()
        if cn and len(cn) > 0:
            df = df[df["conversion_name"].isin(cn)]
        return df

    @reactive.calc
    def _dig_q9_filtered_prior():
        df = _dig_q9_prior()
        cat = input.dig_interaction_cat()
        if cat and len(cat) > 0:
            df = df[df["interaction_category"].isin(cat)]
        cn = input.dig_conversion_name()
        if cn and len(cn) > 0:
            df = df[df["conversion_name"].isin(cn)]
        return df

    # Category KPI cards
    # Category KPI cards (explicit definitions for Shiny compatibility)

    @render.text
    def dig_cat_rfi():
        return f"{_dig_q9()[_dig_q9()['interaction_category'] == 'RFI/Lead Gen']['total_interactions'].sum():,.1f}"

    @render.ui
    def dig_cat_rfi_delta():
        c = _dig_q9()[_dig_q9()["interaction_category"] == "RFI/Lead Gen"]["total_interactions"].sum()
        p = _dig_q9_prior()
        pv = p[p["interaction_category"] == "RFI/Lead Gen"]["total_interactions"].sum() if not p.empty else 0
        return _fmt_delta(c, pv)

    @render.text
    def dig_cat_visit():
        return f"{_dig_q9()[_dig_q9()['interaction_category'] == 'Visit/Event']['total_interactions'].sum():,.1f}"

    @render.ui
    def dig_cat_visit_delta():
        c = _dig_q9()[_dig_q9()["interaction_category"] == "Visit/Event"]["total_interactions"].sum()
        p = _dig_q9_prior()
        pv = p[p["interaction_category"] == "Visit/Event"]["total_interactions"].sum() if not p.empty else 0
        return _fmt_delta(c, pv)

    @render.text
    def dig_cat_apply():
        return f"{_dig_q9()[_dig_q9()['interaction_category'] == 'Apply']['total_interactions'].sum():,.1f}"

    @render.ui
    def dig_cat_apply_delta():
        c = _dig_q9()[_dig_q9()["interaction_category"] == "Apply"]["total_interactions"].sum()
        p = _dig_q9_prior()
        pv = p[p["interaction_category"] == "Apply"]["total_interactions"].sum() if not p.empty else 0
        return _fmt_delta(c, pv)

    @render.text
    def dig_cat_enroll():
        return f"{_dig_q9()[_dig_q9()['interaction_category'] == 'Enroll/Deposit']['total_interactions'].sum():,.1f}"

    @render.ui
    def dig_cat_enroll_delta():
        c = _dig_q9()[_dig_q9()["interaction_category"] == "Enroll/Deposit"]["total_interactions"].sum()
        p = _dig_q9_prior()
        pv = p[p["interaction_category"] == "Enroll/Deposit"]["total_interactions"].sum() if not p.empty else 0
        return _fmt_delta(c, pv)

    @render.text
    def dig_cat_other():
        return f"{_dig_q9()[_dig_q9()['interaction_category'] == 'Other']['total_interactions'].sum():,.1f}"

    @render.ui
    def dig_cat_other_delta():
        c = _dig_q9()[_dig_q9()["interaction_category"] == "Other"]["total_interactions"].sum()
        p = _dig_q9_prior()
        pv = p[p["interaction_category"] == "Other"]["total_interactions"].sum() if not p.empty else 0
        return _fmt_delta(c, pv)

    # --- Category trend chart ---

    @render.ui
    def dig_cat_trend_chart():
        df = _dig_q9_filtered()
        if df.empty:
            return ui.tags.div("No data available.", class_="empty-state")

        cats = ["RFI/Lead Gen", "Visit/Event", "Apply", "Enroll/Deposit", "Other"]

        period = input.dig_period()
        if period and len(period) == 2:
            start_dt = pd.Timestamp(period[0])
            end_dt   = pd.Timestamp(period[1])
        else:
            start_dt = df["day"].min()
            end_dt   = df["day"].max()

        all_days = pd.date_range(start_dt, end_dt, freq="D")
        odd_days = [d for d in all_days if d.day % 2 == 1]
        tickvals = odd_days
        ticktext = [d.strftime("%b ") + str(d.day) for d in odd_days]

        fig = go.Figure()
        for i, cat in enumerate(cats):
            sub = (
                df[df["interaction_category"] == cat]
                .groupby("day")["total_interactions"].sum()
                .reset_index()
            )
            spine = pd.DataFrame({"day": all_days})
            sub = spine.merge(sub, on="day", how="left").fillna(0)
            fig.add_trace(go.Scatter(
                x=sub["day"], y=sub["total_interactions"],
                mode="lines+markers", name=cat,
                line=dict(color=STRATEGY_COLORS[i % len(STRATEGY_COLORS)], width=2),
                marker=dict(size=4),
                hovertemplate=f"<b>{cat}</b><br>%{{x|%b %e}}<br>Interactions: %{{y:,.0f}}<extra></extra>",
            ))

        layout = _base_layout(340)
        layout["xaxis"] = dict(
            tickvals=tickvals, ticktext=ticktext,
            tickfont=dict(family="Manrope, sans-serif", size=10, color="#9B9893"),
            showgrid=False, title="", tickangle=0,
        )
        fig.update_layout(**layout)
        return _plotly_html(fig)

    # --- Key Interaction Breakdown bar chart (Interactions page) ---

    @render.ui
    def dig_cat_breakdown_chart():
        df = _dig_q9_filtered()
        if df.empty:
            return ui.tags.div("No data available.", class_="empty-state")

        cats_order = ["RFI/Lead Gen", "Visit/Event", "Apply", "Enroll/Deposit", "Other"]
        agg = df.groupby("interaction_category")["total_interactions"].sum().reset_index()
        agg = agg[agg["interaction_category"].isin(cats_order)].copy()
        agg["_order"] = agg["interaction_category"].map({c: i for i, c in enumerate(cats_order)})
        agg = agg.sort_values("_order")

        colors = ["#021326", "#A4B9D3", "#C99D44", "#6B8F71", "#8B7355"]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=agg["interaction_category"],
            y=agg["total_interactions"],
            marker_color=[colors[i % len(colors)] for i in range(len(agg))],
            hovertemplate="%{x}<br>Total Interactions: %{y:,.0f}<extra></extra>",
            showlegend=False,
            text=[f"{v:,.0f}" for v in agg["total_interactions"]],
            textposition="inside",
            textfont=dict(family="Manrope, sans-serif", size=11, color="#ffffff"),
        ))
        layout = _base_layout(320)
        layout["margin"] = dict(l=16, r=16, t=8, b=40)
        layout["xaxis"]["tickfont"] = dict(family="Manrope, sans-serif", size=10, color="#9B9893")
        layout["xaxis"]["tickangle"] = 0
        layout["yaxis"]["visible"] = False
        fig.update_layout(**layout)
        return _plotly_html(fig)

    # --- Category × Strategy chart ---

    @render.ui
    def dig_cat_strategy_chart():
        df = _dig_q9_filtered()
        if df.empty:
            return ui.tags.div("No data available.", class_="empty-state")

        grouped = df.groupby(["interaction_category", "product_name"])["total_interactions"].sum().reset_index()
        # Use only categories present in the data, matching the trending chart order
        cats_order = ["RFI/Lead Gen", "Visit/Event", "Apply", "Enroll/Deposit", "Other"]
        cats = [c for c in cats_order if c in df["interaction_category"].unique()]
        products = grouped.groupby("product_name")["total_interactions"].sum().nlargest(8).index.tolist()

        fig = go.Figure()
        for i, prod in enumerate(products):
            sub = grouped[grouped["product_name"] == prod]
            sub = sub.set_index("interaction_category").reindex(cats).fillna(0).reset_index()
            fig.add_trace(go.Bar(
                x=sub["interaction_category"], y=sub["total_interactions"],
                name=prod, marker_color=STRATEGY_COLORS[i % len(STRATEGY_COLORS)],
                width=0.45,
                hovertemplate=f"<b>{prod}</b><br>%{{x}}<br>Interactions: %{{y:,.0f}}<extra></extra>",
            ))
        layout = _base_layout(300)
        layout["barmode"] = "stack"
        layout["bargap"] = 0.5
        layout["xaxis"]["tickfont"] = dict(family="Manrope, sans-serif", size=10, color="#9B9893")
        layout["xaxis"]["tickangle"] = 0
        fig.update_layout(**layout)
        return _plotly_html(fig)

    # --- Interaction breakdown table ---

    @render.ui
    def dig_interaction_breakdown_table():
        df_c = _dig_q9_filtered()
        if df_c.empty:
            return ui.tags.div("No data available.", class_="empty-state")
        df_p = _dig_q9_filtered_prior()

        cats_order = ["RFI/Lead Gen", "Visit/Event", "Apply", "Enroll/Deposit", "Other"]

        agg_c = df_c.groupby("interaction_category").agg(
            direct=("direct_conversions", "sum"),
            vt=("view_through_conversions", "sum"),
            total=("total_interactions", "sum"),
        ).reset_index()

        agg_p = df_p.groupby("interaction_category").agg(
            direct=("direct_conversions", "sum"),
            vt=("view_through_conversions", "sum"),
            total=("total_interactions", "sum"),
        ).reset_index() if not df_p.empty else pd.DataFrame(
            columns=["interaction_category", "direct", "vt", "total"]
        )

        merged = agg_c.merge(
            agg_p, on="interaction_category",
            how="left", suffixes=("", "_p")
        ).fillna(0)
        # Order by cats_order, then any remaining
        merged["_order"] = merged["interaction_category"].map(
            {c: i for i, c in enumerate(cats_order)}
        ).fillna(len(cats_order))
        merged = merged.sort_values("_order")

        metric_cols = ["Direct Interaction", "View-through Interaction", "Total Interaction"]
        rows = []
        for _, r in merged.iterrows():
            rows.append({
                "label": r["interaction_category"],
                "metrics": {
                    "Direct Interaction":       (f"{round(r['direct']):,}",  _pct_change(r["direct"],  r.get("direct_p",  0))),
                    "View-through Interaction": (f"{round(r['vt']):,}",      _pct_change(r["vt"],      r.get("vt_p",      0))),
                    "Total Interaction":        (f"{round(r['total']):,}",   _pct_change(r["total"],   r.get("total_p",   0))),
                },
            })
        return _yoy_delta_table(rows, "Category", metric_cols)

    # --- Interactions by campaign name ---

    @render.ui
    def dig_interactions_campaign_table():
        df = _dig_q9_filtered()
        if df.empty:
            return ui.tags.div("No data available.", class_="empty-state")

        pivot = df.groupby(["product_name", "campaign_name", "interaction_category"])["total_interactions"].sum().reset_index()
        wide = pivot.pivot_table(
            index=["product_name", "campaign_name"],
            columns="interaction_category",
            values="total_interactions",
            aggfunc="sum",
            fill_value=0,
        ).reset_index()
        wide.columns.name = None
        wide["Grand Total"] = wide.select_dtypes(include="number").sum(axis=1)
        wide = wide.sort_values("Grand Total", ascending=False)
        wide = wide.rename(columns={"product_name": "Strategy", "campaign_name": "Campaign Name"})
        heatmap_cols = [c for c in wide.columns if c not in ["Strategy", "Campaign Name"]]
        for c in heatmap_cols:
            wide[c] = wide[c].apply(lambda v: f"{round(v):,}" if isinstance(v, (int, float)) else v)
        return _heatmap_table(wide, heatmap_cols)

    # --- Interactions by month pivot ---

    @render.ui
    def dig_interactions_month_table():
        df = _dig_q9_filtered()
        if df.empty:
            return ui.tags.div("No data available.", class_="empty-state")

        df = df.copy()
        df["ym"] = df["day"].dt.strftime("%Y-%m")
        pivot = df.groupby(["interaction_category", "conversion_name", "ym"])["total_interactions"].sum().reset_index()
        wide = pivot.pivot_table(
            index=["interaction_category", "conversion_name"],
            columns="ym", values="total_interactions", aggfunc="sum", fill_value=0,
        ).reset_index()
        wide.columns.name = None
        num_cols = [c for c in wide.columns if c not in ["interaction_category", "conversion_name"]]
        wide["Grand Total"] = wide[num_cols].sum(axis=1)
        wide = wide.sort_values("Grand Total", ascending=False)
        wide = wide.rename(columns={"interaction_category": "Category", "conversion_name": "Conversion Name"})
        heatmap_cols = num_cols + ["Grand Total"]
        for c in heatmap_cols:
            wide[c] = wide[c].apply(lambda v: f"{round(v):,}" if isinstance(v, (int, float)) else v)
        return _heatmap_table(wide, heatmap_cols)

    # --- Interactions detail table ---

    @render.ui
    def dig_interactions_detail_table():
        df = _dig_q9_filtered()
        if df.empty:
            return ui.tags.div("No data available.", class_="empty-state")

        agg = df.groupby(["interaction_category", "conversion_name", "product_name", "campaign_name"]).agg(
            total=("total_interactions", "sum"),
            direct=("direct_conversions", "sum"),
            vt=("view_through_conversions", "sum"),
        ).reset_index().sort_values("total", ascending=False)
        agg = agg.rename(columns={
            "interaction_category": "Category", "conversion_name": "Conversion Name",
            "product_name": "Strategy", "campaign_name": "Campaign Name",
            "total": "Total Conv.", "direct": "Direct Conv.", "vt": "View-through Conv.",
        })
        heatmap_cols = ["Total Conv.", "Direct Conv.", "View-through Conv."]
        for c in heatmap_cols:
            agg[c] = agg[c].apply(lambda v: f"{round(v):,}")
        return _heatmap_table(agg, heatmap_cols)

    # ══════════════════════════════════════════════════════════
    # TAB 3: GEOGRAPHY
    # ══════════════════════════════════════════════════════════

    @render.ui
    def dig_geo_table():
        df = _apply_dig_filters_monthly(Q10.copy())
        if df.empty:
            return ui.tags.div("No data available.", class_="empty-state")

        try:
            metric = input.dig_geo_metric()
        except Exception:
            metric = "impressions"
        metrics = ["impressions", "clicks", "direct_conversions",
                   "view_through_conversions", "total_conversions"]
        agg = df.groupby("region")[metrics].sum().reset_index()
        agg["CTR"] = (agg["clicks"] / agg["impressions"].replace(0, float("nan")) * 100).round(2)
        agg = agg.sort_values(metric, ascending=False)
        for c in metrics:
            agg[c] = agg[c].round(0).astype(int)
        agg = agg.rename(columns={
            "region": "Region", "impressions": "Impressions", "clicks": "Clicks",
            "direct_conversions": "Direct Conv.", "view_through_conversions": "View-through",
            "total_conversions": "Total Conversions",
        })
        show = ["Region", "Impressions", "Clicks", "CTR", "Direct Conv.",
                "View-through", "Total Conversions"]
        return _plain_table(agg[[c for c in show if c in agg.columns]])

    # ══════════════════════════════════════════════════════════
    # TAB 4: CREATIVE
    # ══════════════════════════════════════════════════════════

    @reactive.effect
    def _update_platform_campaign():
        df = _apply_dig_filters_monthly(Q11_CREATIVE.copy())
        pcs = sorted([p for p in df["platform_campaign_name"].unique() if p])
        ui.update_selectize("dig_platform_campaign", choices=pcs, selected=[])

    @render.ui
    def dig_creative_sections():
        df = _apply_dig_filters_monthly(Q11_CREATIVE.copy())
        pc = input.dig_platform_campaign()
        if pc and len(pc) > 0:
            df = df[df["platform_campaign_name"].isin(pc)]
        kw_df = _apply_dig_filters_monthly(Q11_KEYWORDS.copy())

        if df.empty and kw_df.empty:
            return ui.tags.div("No creative data available.", class_="empty-state")

        sections = []

        # Platform sections
        _PLATFORM_CONFIGS = [
            ("Display", lambda p: "Display" in p and "IP" not in p,
             ["campaign_name", "ad_group", "creative", "ad_url", "impressions", "clicks",
              "direct_conversions", "view_through_conversions", "total_conversions"],
             {"campaign_name": "Campaign", "ad_group": "Ad Group", "creative": "Creative",
              "ad_url": "Landing Page", "impressions": "Impressions", "clicks": "Clicks",
              "direct_conversions": "Direct Conv.", "view_through_conversions": "View-through",
              "total_conversions": "Total Conv."}),
            ("Meta", lambda p: p == "Meta",
             ["campaign_name", "creative", "ad_description", "image_url", "ad_url",
              "impressions", "clicks", "direct_conversions", "view_through_conversions",
              "in_platform_leads", "total_conversions"],
             {"campaign_name": "Campaign", "creative": "Ad Name", "ad_description": "Description",
              "image_url": "Image", "ad_url": "Landing Page", "impressions": "Impressions",
              "clicks": "Clicks", "direct_conversions": "Direct Conv.",
              "view_through_conversions": "View-through", "in_platform_leads": "In-Platform Leads",
              "total_conversions": "Total Conv."}),
            ("YouTube", lambda p: p == "YouTube",
             ["campaign_name", "ad_description", "ad_url", "impressions", "clicks",
              "direct_conversions", "view_through_conversions", "total_conversions",
              "video_starts", "video_completions"],
             {"campaign_name": "Campaign", "ad_description": "Description",
              "ad_url": "Landing Page", "impressions": "Impressions", "clicks": "Clicks",
              "direct_conversions": "Direct Conv.", "view_through_conversions": "View-through",
              "total_conversions": "Total Conv.", "video_starts": "Video Starts",
              "video_completions": "Video Completions"}),
            ("Snapchat", lambda p: "Snapchat" in p,
             ["campaign_name", "ad_description", "ad_url", "impressions", "clicks", "total_conversions"],
             {"campaign_name": "Campaign", "ad_description": "Description",
              "ad_url": "Landing Page", "impressions": "Impressions",
              "clicks": "Clicks (Swipe Ups)", "total_conversions": "Total Conv."}),
            ("TikTok", lambda p: p == "TikTok",
             ["campaign_name", "ad_description", "ad_url", "impressions", "clicks",
              "total_conversions", "followers", "likes", "shares", "comments"],
             {"campaign_name": "Campaign", "ad_description": "Description",
              "ad_url": "Landing Page", "impressions": "Impressions", "clicks": "Clicks",
              "total_conversions": "Total Conv.", "followers": "Followers",
              "likes": "Likes", "shares": "Shares", "comments": "Comments"}),
            ("Spotify", lambda p: p == "Spotify",
             ["campaign_name", "ad_description", "ad_url", "impressions", "clicks"],
             {"campaign_name": "Campaign", "ad_description": "Description",
              "ad_url": "Landing Page", "impressions": "Impressions", "clicks": "Clicks"}),
            ("Reddit", lambda p: p == "Reddit",
             ["campaign_name", "ad_description", "ad_url", "impressions", "clicks", "total_conversions"],
             {"campaign_name": "Campaign", "ad_description": "Description",
              "ad_url": "Landing Page", "impressions": "Impressions", "clicks": "Clicks",
              "total_conversions": "Total Conv."}),
            ("IP Targeting", lambda p: "IP" in p,
             ["campaign_name", "creative", "ad_url", "impressions", "clicks",
              "direct_conversions", "view_through_conversions", "total_conversions"],
             {"campaign_name": "Campaign", "creative": "Creative",
              "ad_url": "Landing Page", "impressions": "Impressions", "clicks": "Clicks",
              "direct_conversions": "Direct Conv.", "view_through_conversions": "View-through",
              "total_conversions": "Total Conv."}),
            ("LinkedIn", lambda p: "LinkedIn" in p,
             ["campaign_name", "ad_description", "image_url", "ad_url",
              "impressions", "clicks", "direct_conversions", "view_through_conversions",
              "in_platform_leads", "total_conversions"],
             {"campaign_name": "Campaign", "ad_description": "Description",
              "image_url": "Image", "ad_url": "Landing Page", "impressions": "Impressions",
              "clicks": "Clicks", "direct_conversions": "Direct Conv.",
              "view_through_conversions": "View-through", "in_platform_leads": "In-Platform Leads",
              "total_conversions": "Total Conv."}),
        ]

        for title, filter_fn, cols, renames in _PLATFORM_CONFIGS:
            sub = df[df["product_name"].apply(filter_fn)]
            if sub.empty:
                continue
            available = [c for c in cols if c in sub.columns]
            num_cols = [c for c in available if sub[c].dtype in ["int64", "float64"]]
            str_cols = [c for c in available if c not in num_cols]
            agg_dict = {c: "sum" for c in num_cols}
            for c in str_cols:
                agg_dict[c] = "first"
            grp_cols = [c for c in ["campaign_name", "creative", "ad_group", "ad_description"] if c in available]
            if not grp_cols:
                grp_cols = [available[0]]
            agged = sub.groupby(grp_cols, as_index=False).agg(agg_dict)
            if "impressions" in agged.columns and "clicks" in agged.columns:
                agged["CTR"] = (agged["clicks"] / agged["impressions"].replace(0, float("nan")) * 100).round(2)
                available.append("CTR")
                renames["CTR"] = "CTR %"
            agged = agged.sort_values(num_cols[0] if num_cols else available[0], ascending=False)
            display = agged[[c for c in available if c in agged.columns]].rename(columns=renames)
            html = _df_to_html(display, title)
            sections.append(html)

        # PPC Keywords
        if not kw_df.empty:
            kw_agg = kw_df.groupby(["campaign_name", "keyword", "match_type"]).agg(
                impressions=("impressions", "sum"), clicks=("clicks", "sum"),
                direct_conversions=("direct_conversions", "sum"), budget=("budget", "sum"),
            ).reset_index()
            kw_agg["CTR"] = (kw_agg["clicks"] / kw_agg["impressions"].replace(0, float("nan")) * 100).round(2)
            kw_agg["CPC"] = (kw_agg["budget"] / kw_agg["clicks"].replace(0, float("nan"))).round(2)
            kw_agg["Cost/Conv."] = (kw_agg["budget"] / kw_agg["direct_conversions"].replace(0, float("nan"))).round(2)
            kw_agg = kw_agg.sort_values("impressions", ascending=False)
            display = kw_agg.rename(columns={
                "campaign_name": "Campaign", "keyword": "Keyword", "match_type": "Match Type",
                "impressions": "Impressions", "clicks": "Clicks",
                "direct_conversions": "Direct Conv.", "CTR": "CTR %", "CPC": "CPC",
                "Cost/Conv.": "Cost/Conv.",
            })
            show = ["Campaign", "Keyword", "Match Type", "Impressions", "Clicks",
                    "CTR %", "CPC", "Direct Conv.", "Cost/Conv."]
            html = _df_to_html(display[[c for c in show if c in display.columns]], "PPC Keyword Performance")
            sections.append(html)

        if not sections:
            return ui.tags.div("No creative data available for the selected filters.", class_="empty-state")
        return ui.TagList(*sections)

    # ══════════════════════════════════════════════════════════
    # TAB 5: INSIGHTS
    # ══════════════════════════════════════════════════════════

    @reactive.calc
    def _dig_notes():
        df = Q12.copy()
        # Apply date filter
        period = input.dig_period()
        if period and len(period) == 2:
            start, end = pd.Timestamp(period[0]), pd.Timestamp(period[1])
            df = df[df["day"].notna() & (df["day"] >= start) & (df["day"] <= end)]
        # Milestone filter
        if input.dig_milestone_only():
            df = df[df["is_milestone"].str.lower() == "yes"]
        # Note type filter
        nt = input.dig_note_type()
        if nt and len(nt) > 0:
            df = df[df["note_type"].isin(nt)]
        return df

    @render.ui
    def dig_perf_notes_table():
        df = _dig_notes()
        df = df[df["note_type"].isin(["Performance", "Performance with Recommendation"])]
        if df.empty:
            return ui.tags.div("No data available.", class_="empty-state")
        df = df.sort_values("day", ascending=False).copy()
        df["Date"] = df["day"].dt.strftime("%b %d, %Y")
        display = df[["Date", "notes"]].rename(columns={"notes": "Performance Insight Notes"})
        return _plain_table(display)

    @render.ui
    def dig_optim_table():
        df = _dig_notes()
        df = df[df["note_type"] == "Optimization"]
        if df.empty:
            return ui.tags.div("No data available.", class_="empty-state")
        df = df.sort_values("day", ascending=False).copy()
        df["Date"] = df["day"].dt.strftime("%b %d, %Y")
        display = df[["Date", "campaign_name", "notes"]].rename(columns={
            "campaign_name": "Campaign", "notes": "Optimization Notes",
        })
        return _plain_table(display)


def _pct_change(curr, prev):
    """Format percentage change."""
    if not prev or prev == 0:
        return "N/A"
    pct = (curr - prev) / abs(prev) * 100
    return f"{pct:+.1f}%"


def _build_yoy_comparison_table(df_c, df_p, group_col: str, label_col: str) -> "ui.HTML":
    """
    Build a YoY table with interleaved metric + Δ% columns.
    Columns: Impressions, Clicks, CTR, Direct Conversion, View-through Conversion,
             In-Platform Leads, Total Conversions, Conversion Rate.
    """
    raw_metrics = [
        "impressions", "clicks", "direct_conversions",
        "view_through_conversions", "in_platform_leads", "total_interactions",
    ]
    col_labels = [
        "Impressions", "Clicks", "CTR",
        "Direct Conversion", "View-through Conv.", "In-Platform Leads",
        "Total Conversions", "Conversion Rate",
    ]

    curr = df_c.groupby(group_col)[raw_metrics].sum().reset_index()
    prev_map = {}
    if not df_p.empty:
        prev = df_p.groupby(group_col)[raw_metrics].sum().reset_index()
        prev_map = prev.set_index(group_col).to_dict(orient="index")

    def _fmt_int(v):
        try:
            return f"{round(v):,}"
        except Exception:
            return "—"

    def _fmt_pct(v):
        if v is None or (isinstance(v, float) and (v != v)):
            return "—"
        return f"{v:.2f}%"

    def _safe_div_local(a, b):
        return a / b if b and b != 0 else None

    rows = []
    for _, r in curr.sort_values("impressions", ascending=False).iterrows():
        grp = r[group_col]
        p = prev_map.get(grp, {})

        ctr_curr = _safe_div_local(r["clicks"], r["impressions"])
        ctr_prev = _safe_div_local(p.get("clicks", 0), p.get("impressions", 0)) if p else None
        conv_rate_curr = _safe_div_local(
            r["direct_conversions"] + r["view_through_conversions"] + r["in_platform_leads"],
            r["clicks"],
        )
        conv_rate_prev = _safe_div_local(
            p.get("direct_conversions", 0) + p.get("view_through_conversions", 0) + p.get("in_platform_leads", 0),
            p.get("clicks", 0),
        ) if p else None

        metrics_data = {
            "Impressions":         (_fmt_int(r["impressions"]),         _pct_change(r["impressions"], p.get("impressions", 0)) if p else "N/A"),
            "Clicks":              (_fmt_int(r["clicks"]),              _pct_change(r["clicks"], p.get("clicks", 0)) if p else "N/A"),
            "CTR":                 (_fmt_pct(ctr_curr * 100 if ctr_curr is not None else None),
                                    _pct_change(ctr_curr, ctr_prev) if (ctr_curr is not None and ctr_prev is not None) else "N/A"),
            "Direct Conversion":   (_fmt_int(r["direct_conversions"]),  _pct_change(r["direct_conversions"], p.get("direct_conversions", 0)) if p else "N/A"),
            "View-through Conv.":  (_fmt_int(r["view_through_conversions"]), _pct_change(r["view_through_conversions"], p.get("view_through_conversions", 0)) if p else "N/A"),
            "In-Platform Leads":   (_fmt_int(r["in_platform_leads"]),   _pct_change(r["in_platform_leads"], p.get("in_platform_leads", 0)) if p else "N/A"),
            "Total Conversions":   (_fmt_int(r["total_interactions"]),  _pct_change(r["total_interactions"], p.get("total_interactions", 0)) if p else "N/A"),
            "Conversion Rate":     (_fmt_pct(conv_rate_curr * 100 if conv_rate_curr is not None else None),
                                    _pct_change(conv_rate_curr, conv_rate_prev) if (conv_rate_curr is not None and conv_rate_prev is not None) else "N/A"),
        }
        rows.append({"label": grp, "metrics": metrics_data})

    return _yoy_delta_table(rows, label_col=label_col, metric_cols=col_labels)


def _df_to_html(df, title):
    """Convert a DataFrame to a styled HTML section for creative tables."""
    rows_html = ""
    for _, row in df.iterrows():
        cells = "".join(f"<td>{v}</td>" for v in row)
        rows_html += f"<tr>{cells}</tr>"
    headers = "".join(f"<th>{c}</th>" for c in df.columns)
    return ui.HTML(f"""
    <div class="creative-section" style="margin-bottom:24px;">
        <h3 style="font-family:Manrope,sans-serif; font-size:14px; font-weight:600;
                    color:#021326; margin:0 0 12px 0;">{title}</h3>
        <div style="overflow-x:auto;">
            <table class="creative-table" style="width:100%; border-collapse:collapse;
                   font-family:Manrope,sans-serif; font-size:12px;">
                <thead><tr style="border-bottom:2px solid #e5e1dc;">{headers}</tr></thead>
                <tbody>{rows_html}</tbody>
            </table>
        </div>
    </div>
    """)
