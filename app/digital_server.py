"""Digital Performance page — reactive server logic (all 5 sub-tabs)."""

import base64
import pandas as pd
from shiny import render, reactive, ui, req
import plotly.graph_objects as go
from urllib.request import urlopen, Request

from formatters import (
    fmt_number,
    fmt_currency,
    fmt_compact,
    resolve_line_label_layout,
)

# ── Image cache: URL → base64 data URI (fetched once, reused) ────
_IMAGE_CACHE: dict[str, str | None] = {}

def _get_image_data_uri(url: str) -> str | None:
    """Fetch an image URL server-side and return a base64 data URI.
    Returns None if the fetch fails. Results are cached in memory."""
    if url in _IMAGE_CACHE:
        return _IMAGE_CACHE[url]
    try:
        req_obj = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urlopen(req_obj, timeout=8)
        ct = resp.headers.get("Content-Type", "image/jpeg")
        data = resp.read()
        if len(data) < 100:  # too small, likely error/tracking pixel
            _IMAGE_CACHE[url] = None
            return None
        b64 = base64.b64encode(data).decode("ascii")
        data_uri = f"data:{ct};base64,{b64}"
        _IMAGE_CACHE[url] = data_uri
        return data_uri
    except Exception:
        _IMAGE_CACHE[url] = None
        return None

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
    paginated: bool = False,
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

    tbl_class = "sortable-table paginated-table" if paginated else "sortable-table"
    html = (
        '<div style="overflow-x:auto;">'
        f'<table class="{tbl_class}" style="width:100%;border-collapse:collapse;">'
        "<thead><tr>" + "".join(header_cells) + "</tr></thead>"
        "<tbody>" + "".join(rows_html) + "</tbody>"
        "<tfoot>" + rows_html_total + "</tfoot>"
        "</table></div>"
    )
    return ui.HTML(html)


def _plain_table(df: "pd.DataFrame", paginated: bool = False) -> "ui.HTML":
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
    tbl_class = "sortable-table paginated-table" if paginated else "sortable-table"
    html = (
        '<div style="overflow-x:auto;">'
        f'<table class="{tbl_class}" style="width:100%;border-collapse:collapse;">'
        "<thead><tr>" + "".join(headers) + "</tr></thead>"
        "<tbody>" + "".join(rows_html) + "</tbody>"
        "<tfoot>" + total_row + "</tfoot>"
        "</table></div>"
    )
    return ui.HTML(html)


def _heatmap_table(df: "pd.DataFrame", heatmap_cols: list, paginated: bool = False) -> "ui.HTML":
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
    tbl_class = "sortable-table paginated-table" if paginated else "sortable-table"
    html = (
        '<div style="overflow-x:auto;">'
        f'<table class="{tbl_class}" style="width:100%;border-collapse:collapse;">'
        "<thead><tr>" + "".join(headers) + "</tr></thead>"
        "<tbody>" + "".join(rows_html) + "</tbody>"
        "<tfoot>" + total_row + "</tfoot>"
        "</table></div>"
    )
    return ui.HTML(html)


def _plotly_html(fig, no_toolbar=True):
    config = {"displayModeBar": False} if no_toolbar else {}
    return ui.HTML(fig.to_html(full_html=False, include_plotlyjs=False, config=config))


def _add_minmax_labels(fig, trace_idx=0, color=None, fmt=",.0f", prefix="", suffix=""):
    """Add data labels for the min and max values of a trace on a line chart.
    Only annotates the first trace by default; pass trace_idx to target another."""
    trace = fig.data[trace_idx]
    y_vals = list(trace.y)
    x_vals = list(trace.x)
    if not y_vals or all(v is None or v == 0 for v in y_vals):
        return
    valid = [(i, v) for i, v in enumerate(y_vals) if v is not None and v != 0]
    if len(valid) < 2:
        return
    max_i, max_v = max(valid, key=lambda t: t[1])
    min_i, min_v = min(valid, key=lambda t: t[1])
    label_color = color or getattr(trace.line, "color", "#021326") or "#021326"
    for idx, val, yshift in [(max_i, max_v, 14), (min_i, min_v, -14)]:
        fig.add_annotation(
            x=x_vals[idx], y=val,
            text=f"{prefix}{val:{fmt}}{suffix}",
            showarrow=False, yshift=yshift,
            font=dict(family="Manrope, sans-serif", size=10, color=label_color),
        )


def _add_minmax_labels_all(fig, fmt=",.0f", prefix="", suffix=""):
    """Add min/max data labels for ALL traces, each in its own color."""
    for i, trace in enumerate(fig.data):
        color = getattr(trace.line, "color", None) or CHART_COLORS[i % len(CHART_COLORS)]
        _add_minmax_labels(fig, trace_idx=i, color=color, fmt=fmt, prefix=prefix, suffix=suffix)


def _add_bar_labels(fig):
    """Add data labels to bar chart segments: white inside, black outside for small bars."""
    for trace in fig.data:
        trace.textposition = "auto"
        trace.textfont = dict(family="Manrope, sans-serif", size=10)
        if hasattr(trace, "text") and trace.text is not None:
            trace.insidetextfont = dict(color="#ffffff", size=10, family="Manrope, sans-serif")
            trace.outsidetextfont = dict(color="#021326", size=10, family="Manrope, sans-serif")


def _add_line_label_annotations(fig, series_defs, chart_height=320, min_gap_px=20):
    """Render stacked line labels as annotations with explicit pixel spacing."""
    layout_map = resolve_line_label_layout(
        series_defs,
        chart_height=chart_height,
        min_gap_px=min_gap_px,
    )
    for series in series_defs:
        s_idx = series["series_idx"]
        xs = list(series["xs"])
        ys = list(series["ys"])
        texts = list(series["texts"])
        color = series.get("color", "#021326")
        font_size = series.get("font_size", 9)
        for x_val, y_val, text in zip(xs, ys, texts):
            spec = layout_map.get(s_idx, {}).get(x_val, {"show": bool(text), "yshift": 14, "xshift": 0})
            if not text or not spec.get("show", True):
                continue
            fig.add_annotation(
                x=x_val,
                y=y_val,
                text=text,
                showarrow=False,
                yshift=spec.get("yshift", 0),
                xshift=spec.get("xshift", 0),
                xanchor="center",
                yanchor="middle",
                font=dict(family="Manrope, sans-serif", size=font_size, color=color),
            )


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


def _fmt_digital_count(n, compact=False):
    """Format Digital Performance count metrics as rounded whole numbers."""
    if n is None or (isinstance(n, float) and pd.isna(n)):
        return "—"
    rounded = round(n)
    if compact:
        abs_val = abs(rounded)
        if abs_val >= 1_000_000_000:
            v = rounded / 1_000_000_000
            s = f"{v:.1f}B"
            return s[:-2] + "B" if s.endswith(".0B") else s
        if abs_val >= 1_000_000:
            v = rounded / 1_000_000
            s = f"{v:.1f}M"
            return s[:-2] + "M" if s.endswith(".0M") else s
        if abs_val >= 1_000:
            v = rounded / 1_000
            s = f"{v:.1f}K"
            return s[:-2] + "K" if s.endswith(".0K") else s
    return f"{rounded:,}"


def _fmt_delta(curr, prev, invert=False, label="YoY"):
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
        f"{arrow} {abs(rounded):.1f}% {label}",
        class_=f"kpi-badge kpi-badge--{sentiment}",
    )


def digital_server(
    input, output, session, *,
    get_q8, get_q9, get_q10,
    get_q11_creative, get_q11_keywords, get_q11_youtube, get_q12,
):
    """Register all digital performance outputs."""
    Q8 = get_q8
    Q9 = get_q9
    Q10 = get_q10
    Q11_CREATIVE = get_q11_creative
    Q11_KEYWORDS = get_q11_keywords
    Q11_YOUTUBE = get_q11_youtube
    Q12 = get_q12

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
        return _apply_dig_filters(Q8())

    @reactive.calc
    def _dig_q8_prior():
        """Prior period for Q8 — previous month (MoM comparison)."""
        df = Q8()
        period = input.dig_period()
        if period and len(period) == 2:
            start, end = pd.Timestamp(period[0]), pd.Timestamp(period[1])
            # Shift by 1 month
            prior_start = start - pd.DateOffset(months=1)
            prior_end = end - pd.DateOffset(months=1)
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
        return _apply_dig_filters(Q9())

    @reactive.calc
    def _dig_q9_prior():
        """Prior period for Q9 — previous month (MoM comparison)."""
        df = Q9()
        period = input.dig_period()
        if period and len(period) == 2:
            start, end = pd.Timestamp(period[0]), pd.Timestamp(period[1])
            prior_start = start - pd.DateOffset(months=1)
            prior_end = end - pd.DateOffset(months=1)
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
        """Fixed prior academic year Jul 2024 – Jun 2025 for YoY comparison."""
        df = Q8()
        yoy_start = pd.Timestamp("2024-07-01")
        yoy_end = pd.Timestamp("2025-06-30")
        df = df[(df["day"] >= yoy_start) & (df["day"] <= yoy_end)]
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
        """Fixed prior academic year Jul 2024 – Jun 2025 for YoY comparison (Q9)."""
        df = Q9()
        yoy_start = pd.Timestamp("2024-07-01")
        yoy_end = pd.Timestamp("2025-06-30")
        df = df[(df["day"] >= yoy_start) & (df["day"] <= yoy_end)]
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
        return _fmt_digital_count(v, compact=True)

    @render.ui
    def dig_key_interactions_delta():
        curr = _dig_q8()["total_interactions"].sum()
        prev = _dig_q8_prior()["total_interactions"].sum()
        return _fmt_delta(curr, prev, label="MoM")

    @render.text
    def dig_cpi():
        df = _dig_q8()
        return fmt_currency(_safe_div(df["budget"].sum(), df["total_interactions"].sum()))

    @render.ui
    def dig_cpi_delta():
        df_c, df_p = _dig_q8(), _dig_q8_prior()
        curr = _safe_div(df_c["budget"].sum(), df_c["total_interactions"].sum())
        prev = _safe_div(df_p["budget"].sum(), df_p["total_interactions"].sum())
        return _fmt_delta(curr, prev, invert=True, label="MoM")

    @render.text
    def dig_inquiry_int():
        v = _dig_q9()[_dig_q9()["interaction_category"] == "RFI/Lead Gen"]["total_interactions"].sum()
        return _fmt_digital_count(v, compact=True)

    @render.ui
    def dig_inquiry_int_delta():
        curr = _dig_q9()[_dig_q9()["interaction_category"] == "RFI/Lead Gen"]["total_interactions"].sum()
        prev = _dig_q9_prior()
        prev_v = prev[prev["interaction_category"] == "RFI/Lead Gen"]["total_interactions"].sum() if not prev.empty else 0
        return _fmt_delta(curr, prev_v, label="MoM")

    @render.text
    def dig_visit_int():
        v = _dig_q9()[_dig_q9()["interaction_category"] == "Visit/Event"]["total_interactions"].sum()
        return _fmt_digital_count(v, compact=True)

    @render.ui
    def dig_visit_int_delta():
        curr = _dig_q9()[_dig_q9()["interaction_category"] == "Visit/Event"]["total_interactions"].sum()
        prev = _dig_q9_prior()
        prev_v = prev[prev["interaction_category"] == "Visit/Event"]["total_interactions"].sum() if not prev.empty else 0
        return _fmt_delta(curr, prev_v, label="MoM")

    @render.text
    def dig_apply_int():
        v = _dig_q9()[_dig_q9()["interaction_category"] == "Apply"]["total_interactions"].sum()
        return _fmt_digital_count(v, compact=True)

    @render.ui
    def dig_apply_int_delta():
        curr = _dig_q9()[_dig_q9()["interaction_category"] == "Apply"]["total_interactions"].sum()
        prev = _dig_q9_prior()
        prev_v = prev[prev["interaction_category"] == "Apply"]["total_interactions"].sum() if not prev.empty else 0
        return _fmt_delta(curr, prev_v, label="MoM")

    # --- Engagement & Spend metrics ---

    @render.text
    def dig_budget():
        return fmt_currency(_dig_q8()["budget"].sum())

    @render.ui
    def dig_budget_delta():
        return _fmt_delta(_dig_q8()["budget"].sum(), _dig_q8_prior()["budget"].sum(), invert=True, label="MoM")

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
            invert=True, label="MoM",
        )

    @render.text
    def dig_direct_conv():
        return _fmt_digital_count(_dig_q8()['direct_conversions'].sum(), compact=True)

    @render.ui
    def dig_direct_conv_delta():
        return _fmt_delta(
            _dig_q8()["direct_conversions"].sum(),
            _dig_q8_prior()["direct_conversions"].sum(),
            label="MoM",
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
            invert=True, label="MoM",
        )

    @render.text
    def dig_ipl():
        return _fmt_digital_count(_dig_q8()["in_platform_leads"].sum(), compact=True)

    @render.ui
    def dig_ipl_delta():
        return _fmt_delta(
            _dig_q8()["in_platform_leads"].sum(),
            _dig_q8_prior()["in_platform_leads"].sum(),
            label="MoM",
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
            invert=True, label="MoM",
        )

    @render.text
    def dig_vtc():
        return _fmt_digital_count(_dig_q8()["view_through_conversions"].sum(), compact=True)

    @render.ui
    def dig_vtc_delta():
        return _fmt_delta(
            _dig_q8()["view_through_conversions"].sum(),
            _dig_q8_prior()["view_through_conversions"].sum(),
            label="MoM",
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
            invert=True, label="MoM",
        )

    # --- Budget KPI card (Overview top strip) ---

    @render.text
    def dig_budget_kpi():
        return fmt_currency(_dig_q8()["budget"].sum())

    @render.ui
    def dig_budget_kpi_delta():
        return _fmt_delta(_dig_q8()["budget"].sum(), _dig_q8_prior()["budget"].sum(), invert=True, label="MoM")

    # --- Clicks metric card (Engagement & Spend grid) ---

    @render.text
    def dig_clicks():
        return _fmt_digital_count(_dig_q8()["clicks"].sum(), compact=True)

    @render.ui
    def dig_clicks_delta():
        return _fmt_delta(_dig_q8()["clicks"].sum(), _dig_q8_prior()["clicks"].sum(), label="MoM")

    # --- Inline cost outputs for Overview KPI cards ---

    def _dig_cost_inline(curr_metric_val, prev_metric_val, cost_label, label="MoM"):
        """Generic inline cost element for a digital KPI card."""
        budget_c = _dig_q8()["budget"].sum()
        budget_p = _dig_q8_prior()["budget"].sum()
        curr_val = _safe_div(budget_c, curr_metric_val)
        prev_val = _safe_div(budget_p, prev_metric_val)
        value_str = fmt_currency(curr_val) if curr_val is not None else "\u2014"
        yoy_el = _fmt_delta(curr_val, prev_val, invert=True, label=label)
        return ui.tags.div(
            ui.tags.div(
                ui.tags.span(cost_label, style="font-size:10px;color:#9B9893;font-weight:600;"),
                ui.tags.span(value_str, style="font-size:12px;font-weight:700;color:#021326;margin-left:6px;"),
                yoy_el,
                style="display:flex;align-items:center;gap:4px;flex-wrap:wrap;",
            ),
            style="margin-top:6px;padding-top:6px;border-top:1px solid #e5e1dc;",
        )

    @render.ui
    def dig_cost_key_int():
        c = _dig_q8()["total_interactions"].sum()
        p = _dig_q8_prior()["total_interactions"].sum()
        return _dig_cost_inline(c, p, "Cost/Int.")

    @render.ui
    def dig_cost_inquiry_int():
        q9_c = _dig_q9()
        q9_p = _dig_q9_prior()
        c = q9_c[q9_c["interaction_category"] == "RFI/Lead Gen"]["total_interactions"].sum()
        p = q9_p[q9_p["interaction_category"] == "RFI/Lead Gen"]["total_interactions"].sum() if not q9_p.empty else 0
        return _dig_cost_inline(c, p, "Cost/Inquiry Int.")

    @render.ui
    def dig_cost_visit_int():
        q9_c = _dig_q9()
        q9_p = _dig_q9_prior()
        c = q9_c[q9_c["interaction_category"] == "Visit/Event"]["total_interactions"].sum()
        p = q9_p[q9_p["interaction_category"] == "Visit/Event"]["total_interactions"].sum() if not q9_p.empty else 0
        return _dig_cost_inline(c, p, "Cost/Visit Int.")

    @render.ui
    def dig_cost_apply_int():
        q9_c = _dig_q9()
        q9_p = _dig_q9_prior()
        c = q9_c[q9_c["interaction_category"] == "Apply"]["total_interactions"].sum()
        p = q9_p[q9_p["interaction_category"] == "Apply"]["total_interactions"].sum() if not q9_p.empty else 0
        return _dig_cost_inline(c, p, "Cost/Apply Int.")

    # --- Trending Chart ---

    @render.ui
    def dig_trending_chart():
        df_curr = _dig_q8()
        df_prior = _dig_q8_prior()
        if df_curr.empty:
            return ui.tags.div("No data available.", class_="empty-state")

        # Determine selected metric
        try:
            metric_key = input.dig_trending_metric()
        except Exception:
            metric_key = "clicks"

        _METRIC_LABELS = {
            "clicks": "Clicks",
            "ctr": "CTR",
            "direct_conversions": "Direct Interactions",
            "view_through_conversions": "View-through Interactions",
            "in_platform_leads": "In-Platform Leads",
            "budget": "Budget",
            "cost_per_total_interaction": "Cost Per Total Interaction",
        }
        metric_label = _METRIC_LABELS.get(metric_key, metric_key)

        # Derived metrics need special aggregation
        is_rate = metric_key == "ctr"
        is_cost = metric_key in ("budget", "cost_per_total_interaction")
        is_derived = metric_key in ("ctr", "cost_per_total_interaction")

        def _aggregate_daily(df):
            agg_cols = {"impressions": "sum", "clicks": "sum",
                        "direct_conversions": "sum", "view_through_conversions": "sum",
                        "in_platform_leads": "sum", "total_interactions": "sum",
                        "budget": "sum"}
            daily = df.groupby("day").agg(agg_cols).reset_index().sort_values("day")
            # Derived columns
            daily["ctr"] = daily.apply(
                lambda r: (r["clicks"] / r["impressions"] * 100) if r["impressions"] > 0 else 0, axis=1)
            daily["cost_per_total_interaction"] = daily.apply(
                lambda r: (r["budget"] / r["total_interactions"]) if r["total_interactions"] > 0 else 0, axis=1)
            return daily

        curr_daily = _aggregate_daily(df_curr)

        # Build full date spine
        period = input.dig_period()
        if period and len(period) == 2:
            start_dt = pd.Timestamp(period[0])
            end_dt   = pd.Timestamp(period[1])
        else:
            start_dt = curr_daily["day"].min()
            end_dt   = curr_daily["day"].max()

        all_days = pd.DataFrame({"day": pd.date_range(start_dt, end_dt, freq="D")})
        curr_daily = all_days.merge(curr_daily, on="day", how="left").fillna(0)

        # Tick labels on odd days
        odd_days = curr_daily[curr_daily["day"].dt.day % 2 == 1]["day"]
        tickvals = odd_days.tolist()
        ticktext = [pd.Timestamp(d).strftime("%b ") + str(pd.Timestamp(d).day) for d in odd_days]

        # Format hover values based on metric type
        if is_rate:
            hover_fmt = f"%{{x|%b %e}}<br>{metric_label}: %{{y:.2f}}%<extra></extra>"
        elif metric_key == "budget":
            hover_fmt = f"%{{x|%b %e}}<br>{metric_label}: $%{{y:,.0f}}<extra></extra>"
        elif metric_key == "cost_per_total_interaction":
            hover_fmt = f"%{{x|%b %e}}<br>{metric_label}: $%{{y:,.2f}}<extra></extra>"
        else:
            hover_fmt = f"%{{x|%b %e}}<br>{metric_label}: %{{y:,.0f}}<extra></extra>"

        def _fmt_text(vals, mk):
            if mk == "ctr":
                return [f"{v:.1f}%" for v in vals]
            elif mk in ("budget", "cost_per_total_interaction"):
                return [f"${v:,.0f}" if v >= 1 else f"${v:.2f}" for v in vals]
            else:
                return [f"{v:,.0f}" for v in vals]

        # Compute prior series first so we can resolve label collisions for both
        _merged = None
        if not df_prior.empty:
            prior_daily = _aggregate_daily(df_prior)
            prior_daily["day_num"] = prior_daily["day"].dt.day
            curr_daily["day_num"] = curr_daily["day"].dt.day
            _merged = curr_daily[["day", "day_num"]].merge(
                prior_daily[["day_num", metric_key]], on="day_num", how="left"
            ).fillna(0)

        _series_defs = [{
            "series_idx": 0,
            "xs": curr_daily["day"].tolist(),
            "ys": curr_daily[metric_key].tolist(),
            "texts": _fmt_text(curr_daily[metric_key].tolist(), metric_key),
            "default_pos": "top center",
        }]
        if _merged is not None:
            _series_defs.append({
                "series_idx": 1,
                "xs": _merged["day"].tolist(),
                "ys": _merged[metric_key].tolist(),
                "texts": _fmt_text(_merged[metric_key].tolist(), metric_key),
                "default_pos": "bottom center",
            })
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=curr_daily["day"], y=curr_daily[metric_key],
            mode="lines+markers", name=metric_label,
            line=dict(color="#EA332D", width=2),
            marker=dict(color="#EA332D", size=4),
            hovertemplate=hover_fmt,
        ))

        if _merged is not None:
            if is_rate:
                hover_fmt_prior = f"%{{x|%b %e}}<br>{metric_label} (prev month): %{{y:.2f}}%<extra></extra>"
            elif metric_key == "budget":
                hover_fmt_prior = f"%{{x|%b %e}}<br>{metric_label} (prev month): $%{{y:,.0f}}<extra></extra>"
            elif metric_key == "cost_per_total_interaction":
                hover_fmt_prior = f"%{{x|%b %e}}<br>{metric_label} (prev month): $%{{y:,.2f}}<extra></extra>"
            else:
                hover_fmt_prior = f"%{{x|%b %e}}<br>{metric_label} (prev month): %{{y:,.0f}}<extra></extra>"

            fig.add_trace(go.Scatter(
                x=_merged["day"], y=_merged[metric_key],
                mode="lines+markers", name=f"{metric_label} (previous month)",
                line=dict(color="#C99D44", width=1.8, dash="dash"),
                marker=dict(color="#C99D44", size=3),
                hovertemplate=hover_fmt_prior,
            ))

        # Y-axis formatting
        yaxis_opts = dict(showgrid=True, gridcolor="#F0EEEA")
        if is_rate:
            yaxis_opts["ticksuffix"] = "%"
        elif is_cost or metric_key == "budget":
            yaxis_opts["tickprefix"] = "$"

        layout = _base_layout(320)
        layout["xaxis"] = dict(
            tickvals=tickvals, ticktext=ticktext,
            tickfont=dict(family="Manrope, sans-serif", size=10, color="#9B9893"),
            showgrid=False, title="", tickangle=0,
        )
        layout["yaxis"] = {**layout.get("yaxis", {}), **yaxis_opts}
        fig.update_layout(**layout)
        _series_defs[0]["color"] = "#EA332D"
        _series_defs[0]["font_size"] = 9
        if len(_series_defs) > 1:
            _series_defs[1]["color"] = "#C99D44"
            _series_defs[1]["font_size"] = 9
        _add_line_label_annotations(fig, _series_defs, chart_height=320, min_gap_px=20)
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
            hovertemplate="%{x}<br>Total Key Interactions: %{y:,.0f}<extra></extra>",
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

        _curr_texts = [f"${v:,.0f}" if v and v >= 1 else "" for v in curr_daily["cptc"]]
        _series_defs = [{
            "series_idx": 0,
            "xs": curr_daily["day"].tolist(),
            "ys": curr_daily["cptc"].tolist(),
            "texts": _curr_texts,
            "default_pos": "top center",
        }]
        _prior_texts = None
        merged = None

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
            _prior_texts = [f"${v:,.0f}" if pd.notna(v) and v and v >= 1 else "" for v in merged["cptc"]]
            _series_defs.append({
                "series_idx": 1,
                "xs": merged["day"].tolist(),
                "ys": merged["cptc"].tolist(),
                "texts": _prior_texts,
                "default_pos": "bottom center",
            })

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=curr_daily["day"], y=curr_daily["cptc"],
            mode="lines+markers", name="Cost Per Total Key Interaction",
            line=dict(color="#EA332D", width=2),
            marker=dict(color="#EA332D", size=4),
            hovertemplate="%{x|%b %e}<br>Cost/Conv: $%{y:,.2f}<extra></extra>",
        ))

        if merged is not None:
            fig.add_trace(go.Scatter(
                x=merged["day"], y=merged["cptc"],
                mode="lines+markers", name="Cost Per Total Key Int. (previous month)",
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
        _series_defs[0]["color"] = "#EA332D"
        _series_defs[0]["font_size"] = 9
        if len(_series_defs) > 1:
            _series_defs[1]["color"] = "#C99D44"
            _series_defs[1]["font_size"] = 9
        _add_line_label_annotations(fig, _series_defs, chart_height=320, min_gap_px=20)
        return _plotly_html(fig)

    # ══════════════════════════════════════════════════════════
    # TAB 1b: OVERVIEW YoY  (same outputs, _yoy suffix, compare curr vs prior year)
    # ══════════════════════════════════════════════════════════

    @render.text
    def dig_impressions_yoy():
        return _fmt_digital_count(_dig_q8()["impressions"].sum(), compact=True)

    @render.ui
    def dig_impressions_yoy_delta():
        return _fmt_delta(_dig_q8()["impressions"].sum(), _dig_q8_yoy()["impressions"].sum())

    @render.text
    def dig_clicks_yoy():
        return _fmt_digital_count(_dig_q8()["clicks"].sum(), compact=True)

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
        return _fmt_digital_count(v, compact=True)

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
        return _fmt_digital_count(v, compact=True)

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
        return _fmt_digital_count(v, compact=True)

    @render.ui
    def dig_inquiry_int_delta_yoy():
        curr = _dig_q9()[_dig_q9()["interaction_category"] == "RFI/Lead Gen"]["total_interactions"].sum()
        py = _dig_q9_yoy()
        prev_v = py[py["interaction_category"] == "RFI/Lead Gen"]["total_interactions"].sum() if not py.empty else 0
        return _fmt_delta(curr, prev_v)

    @render.text
    def dig_visit_int_yoy():
        v = _dig_q9()[_dig_q9()["interaction_category"] == "Visit/Event"]["total_interactions"].sum()
        return _fmt_digital_count(v, compact=True)

    @render.ui
    def dig_visit_int_delta_yoy():
        curr = _dig_q9()[_dig_q9()["interaction_category"] == "Visit/Event"]["total_interactions"].sum()
        py = _dig_q9_yoy()
        prev_v = py[py["interaction_category"] == "Visit/Event"]["total_interactions"].sum() if not py.empty else 0
        return _fmt_delta(curr, prev_v)

    @render.text
    def dig_apply_int_yoy():
        v = _dig_q9()[_dig_q9()["interaction_category"] == "Apply"]["total_interactions"].sum()
        return _fmt_digital_count(v, compact=True)

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
        return _fmt_digital_count(_dig_q8()['direct_conversions'].sum(), compact=True)

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
        return _fmt_digital_count(_dig_q8()["in_platform_leads"].sum(), compact=True)

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
        return _fmt_digital_count(_dig_q8()["view_through_conversions"].sum(), compact=True)

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

    # --- Budget KPI card (YoY top strip) ---

    @render.text
    def dig_budget_yoy_kpi():
        return fmt_currency(_dig_q8()["budget"].sum())

    @render.ui
    def dig_budget_yoy_kpi_delta():
        return _fmt_delta(_dig_q8()["budget"].sum(), _dig_q8_yoy()["budget"].sum(), invert=True)

    # --- Inline cost outputs for YoY KPI cards ---

    def _dig_cost_inline_yoy(curr_metric_val, prev_metric_val, cost_label):
        budget_c = _dig_q8()["budget"].sum()
        budget_p = _dig_q8_yoy()["budget"].sum()
        curr_val = _safe_div(budget_c, curr_metric_val)
        prev_val = _safe_div(budget_p, prev_metric_val)
        value_str = fmt_currency(curr_val) if curr_val is not None else "\u2014"
        yoy_el = _fmt_delta(curr_val, prev_val, invert=True)
        return ui.tags.div(
            ui.tags.div(
                ui.tags.span(cost_label, style="font-size:10px;color:#9B9893;font-weight:600;"),
                ui.tags.span(value_str, style="font-size:12px;font-weight:700;color:#021326;margin-left:6px;"),
                yoy_el,
                style="display:flex;align-items:center;gap:4px;flex-wrap:wrap;",
            ),
            style="margin-top:6px;padding-top:6px;border-top:1px solid #e5e1dc;",
        )

    @render.ui
    def dig_cost_interactions_yoy():
        return _dig_cost_inline_yoy(
            _dig_q8()["impressions"].sum(), _dig_q8_yoy()["impressions"].sum(), "Cost/Int.")

    @render.ui
    def dig_cost_clicks_yoy():
        return _dig_cost_inline_yoy(
            _dig_q8()["clicks"].sum(), _dig_q8_yoy()["clicks"].sum(), "Cost/Click")

    @render.ui
    def dig_cost_total_conv_yoy():
        df_c, df_p = _dig_q8(), _dig_q8_yoy()
        c = df_c["direct_conversions"].sum() + df_c["view_through_conversions"].sum() + df_c["in_platform_leads"].sum()
        p = df_p["direct_conversions"].sum() + df_p["view_through_conversions"].sum() + df_p["in_platform_leads"].sum()
        return _dig_cost_inline_yoy(c, p, "Cost/Key Int.")

    # --- Cost per View-through Int. (YoY Engagement & Spend) ---

    @render.text
    def dig_cpvtc_yoy():
        df = _dig_q8()
        return fmt_currency(_safe_div(df["budget"].sum(), df["view_through_conversions"].sum()))

    @render.ui
    def dig_cpvtc_yoy_delta():
        df_c, df_p = _dig_q8(), _dig_q8_yoy()
        return _fmt_delta(
            _safe_div(df_c["budget"].sum(), df_c["view_through_conversions"].sum()),
            _safe_div(df_p["budget"].sum(), df_p["view_through_conversions"].sum()),
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
            df_curr.groupby("month")["total_interactions"].sum()
            .reset_index().sort_values("month")
        )
        curr_monthly["month_dt"] = curr_monthly["month"].dt.to_timestamp()
        curr_monthly["label"] = curr_monthly["month_dt"].dt.strftime("%b %y")
        # month position index (0, 1, 2, …) for aligning prior year
        curr_monthly = curr_monthly.reset_index(drop=True)
        curr_monthly["month_pos"] = curr_monthly.index

        _series_defs = [{
            "series_idx": 0,
            "xs": curr_monthly["month_dt"].tolist(),
            "ys": curr_monthly["total_interactions"].tolist(),
            "texts": [f"{v:,.0f}" for v in curr_monthly["total_interactions"]],
            "default_pos": "top center",
        }]

        if not df_prior.empty:
            df_prior = df_prior.copy()
            df_prior["month"] = df_prior["day"].dt.to_period("M")
            prior_monthly = (
                df_prior.groupby("month")["total_interactions"].sum()
                .reset_index().sort_values("month")
            ).reset_index(drop=True)
            prior_monthly["month_pos"] = prior_monthly.index
            prior_monthly["prior_label"] = prior_monthly["month"].dt.strftime("%b %y")
            merged = curr_monthly[["month_dt", "month_pos"]].merge(
                prior_monthly[["month_pos", "total_interactions", "prior_label"]], on="month_pos", how="left"
            )
            merged["total_interactions"] = merged["total_interactions"].fillna(0)
            merged["prior_label"] = merged["prior_label"].fillna("")
            _series_defs.append({
                "series_idx": 1,
                "xs": merged["month_dt"].tolist(),
                "ys": merged["total_interactions"].tolist(),
                "texts": [f"{v:,.0f}" for v in merged["total_interactions"]],
                "default_pos": "bottom center",
            })
        else:
            merged = None

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=curr_monthly["month_dt"], y=curr_monthly["total_interactions"],
            mode="lines+markers", name="Total Interactions",
            line=dict(color="#EA332D", width=2),
            marker=dict(color="#EA332D", size=4),
            hovertemplate="%{x|%b %y}<br>Total Interactions: %{y:,.0f}<extra></extra>",
        ))

        if merged is not None:
            fig.add_trace(go.Scatter(
                x=merged["month_dt"], y=merged["total_interactions"],
                customdata=merged["prior_label"],
                mode="lines+markers", name="Total Interactions (previous year)",
                line=dict(color="#C99D44", width=1.8, dash="dash"),
                marker=dict(color="#C99D44", size=3),
                hovertemplate="%{customdata}<br>Total Interactions (prev): %{y:,.0f}<extra></extra>",
            ))

        layout = _base_layout(320)
        layout["xaxis"] = dict(
            tickvals=curr_monthly["month_dt"].tolist(),
            ticktext=curr_monthly["label"].tolist(),
            tickfont=dict(family="Manrope, sans-serif", size=10, color="#9B9893"),
            showgrid=False, title="", tickangle=0,
        )
        fig.update_layout(**layout)
        _series_defs[0]["color"] = "#EA332D"
        _series_defs[0]["font_size"] = 9
        if len(_series_defs) > 1:
            _series_defs[1]["color"] = "#C99D44"
            _series_defs[1]["font_size"] = 9
        _add_line_label_annotations(fig, _series_defs, chart_height=320, min_gap_px=20)
        return _plotly_html(fig)

    @render.ui
    def dig_strategy_bar_yoy():
        df = _dig_q8()
        if df.empty:
            return ui.tags.div("No data available.", class_="empty-state")

        try:
            metric_key = input.dig_strategy_bar_metric_yoy()
        except Exception:
            metric_key = "total_interactions"
        metric_label = _STRATEGY_METRIC_LABELS.get(metric_key, metric_key)

        strat = df.groupby("product_name")[metric_key].sum().sort_values(ascending=True).reset_index()
        strat = strat[strat[metric_key] > 0]
        if strat.empty:
            return ui.tags.div("No data available.", class_="empty-state")
        total = strat[metric_key].sum()
        strat["pct"] = (strat[metric_key] / total * 100).round(1)
        x_max = strat[metric_key].max() * 1.28
        is_currency = metric_key == "budget"
        hover_fmt = f"<b>%{{y}}</b><br>{metric_label}: %{{x:$,.0f}}<extra></extra>" if is_currency else f"<b>%{{y}}</b><br>{metric_label}: %{{x:,}}<extra></extra>"
        fig = go.Figure(go.Bar(
            x=strat[metric_key], y=strat["product_name"],
            orientation="h", marker_color=CHART_COLORS[0],
            text=[f"{p:.1f}%" for p in strat["pct"]], textposition="outside",
            textfont=dict(family="Manrope, sans-serif", size=10, color=CARNEGIE_NAVY),
            hovertemplate=hover_fmt,
        ))
        layout = _base_layout(max(260, len(strat) * 28 + 60))
        layout["margin"] = dict(l=8, r=8, t=8, b=24, autoexpand=True)
        layout["xaxis"] = dict(showgrid=True, gridcolor="#F0EEEA", title="", range=[0, x_max])
        if is_currency:
            layout["xaxis"]["tickprefix"] = "$"
        layout["yaxis"] = dict(showgrid=False, title="", automargin=True)
        fig.update_layout(**layout)
        return _plotly_html(fig)

    @render.ui
    def dig_strategy_trend_yoy():
        df = _dig_q8()
        if df.empty:
            return ui.tags.div("No data available.", class_="empty-state")

        try:
            metric_key = input.dig_strategy_trend_metric_yoy()
        except Exception:
            metric_key = "total_interactions"
        metric_label = _STRATEGY_TREND_METRIC_LABELS.get(metric_key, metric_key)

        top5 = df.groupby("product_name")["total_interactions"].sum().nlargest(5).index.tolist()
        df_top = df[df["product_name"].isin(top5)].copy()

        # Group by month for YoY page
        df_top["month"] = df_top["day"].dt.to_period("M")
        all_months = sorted(df_top["month"].unique())
        all_months_dt = [m.to_timestamp() for m in all_months]
        ticktext = [m.strftime("%b %y") for m in all_months_dt]

        if metric_key == "ctr":
            agg_cols = {"clicks": "sum", "impressions": "sum"}
        elif metric_key == "cost_per_total_interaction":
            agg_cols = {"budget": "sum", "total_interactions": "sum"}
        else:
            agg_cols = {metric_key: "sum"}

        is_rate = metric_key == "ctr"
        is_currency = metric_key in ("budget", "cost_per_total_interaction")

        _series_defs = []
        _series_payloads = []
        for i, prod in enumerate(top5):
            sub = (
                df_top[df_top["product_name"] == prod]
                .groupby("month").agg(agg_cols)
                .reset_index()
            )
            sub["month_dt"] = sub["month"].dt.to_timestamp()
            spine = pd.DataFrame({"month_dt": all_months_dt})
            merge_cols = ["month_dt"] + [c for c in agg_cols]
            sub = spine.merge(sub[merge_cols], on="month_dt", how="left").fillna(0)
            if metric_key == "ctr":
                sub["_val"] = sub.apply(lambda r: (r["clicks"] / r["impressions"] * 100) if r["impressions"] > 0 else 0, axis=1)
            elif metric_key == "cost_per_total_interaction":
                sub["_val"] = sub.apply(lambda r: (r["budget"] / r["total_interactions"]) if r["total_interactions"] > 0 else 0, axis=1)
            else:
                sub["_val"] = sub[metric_key]

            hover_fmt_val = "$%{y:,.2f}" if is_currency else "%{y:.2f}%" if is_rate else "%{y:,.0f}"
            _txt = [f"${v:,.0f}" for v in sub["_val"]] if is_currency else [f"{v:.1f}%" for v in sub["_val"]] if is_rate else [f"{v:,.0f}" for v in sub["_val"]]
            _clr = _STRATEGY_TREND_COLORS[i % len(_STRATEGY_TREND_COLORS)]
            _series_defs.append({
                "series_idx": i,
                "xs": sub["month_dt"].tolist(),
                "ys": sub["_val"].tolist(),
                "texts": _txt,
                "default_pos": "top center" if i % 2 == 0 else "bottom center",
            })
            _series_payloads.append((prod, sub.copy(), _clr, hover_fmt_val))

        fig = go.Figure()
        for i, (prod, sub, _clr, hover_fmt_val) in enumerate(_series_payloads):
            fig.add_trace(go.Scatter(
                x=sub["month_dt"], y=sub["_val"],
                mode="lines+markers", name=prod,
                line=dict(color=_clr, width=2),
                marker=dict(color=_clr, size=4),
                hovertemplate=f"<b>{prod}</b><br>%{{x|%b %y}}<br>{metric_label}: {hover_fmt_val}<extra></extra>",
            ))

        layout = _base_layout(320)
        layout["xaxis"] = dict(
            tickvals=all_months_dt, ticktext=ticktext,
            tickfont=dict(family="Manrope, sans-serif", size=10, color="#9B9893"),
            showgrid=False, title="", tickangle=0,
        )
        if is_rate:
            layout["yaxis"]["ticksuffix"] = "%"
        elif is_currency:
            layout["yaxis"]["tickprefix"] = "$"
        fig.update_layout(**layout)
        for i, (_, _, _clr, _) in enumerate(_series_payloads):
            _series_defs[i]["color"] = _clr
            _series_defs[i]["font_size"] = 9
        _add_line_label_annotations(fig, _series_defs, chart_height=320, min_gap_px=20)
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

    _STRATEGY_METRIC_LABELS = {
        "total_interactions": "Total Interactions",
        "clicks": "Clicks",
        "direct_conversions": "Direct Interactions",
        "view_through_conversions": "View-through Interactions",
        "in_platform_leads": "In-Platform Leads",
        "budget": "Budget",
    }

    @render.ui
    def dig_strategy_bar():
        df = _dig_q8()
        if df.empty:
            return ui.tags.div("No data available.", class_="empty-state")

        try:
            metric_key = input.dig_strategy_bar_metric()
        except Exception:
            metric_key = "total_interactions"
        metric_label = _STRATEGY_METRIC_LABELS.get(metric_key, metric_key)

        strat = df.groupby("product_name")[metric_key].sum().sort_values(ascending=True).reset_index()
        strat = strat[strat[metric_key] > 0]
        if strat.empty:
            return ui.tags.div("No data available.", class_="empty-state")

        total = strat[metric_key].sum()
        strat["pct"] = (strat[metric_key] / total * 100).round(1)
        x_max = strat[metric_key].max() * 1.28

        is_currency = metric_key == "budget"
        hover_fmt = f"<b>%{{y}}</b><br>{metric_label}: %{{x:$,.0f}}<extra></extra>" if is_currency else f"<b>%{{y}}</b><br>{metric_label}: %{{x:,}}<extra></extra>"

        fig = go.Figure(go.Bar(
            x=strat[metric_key], y=strat["product_name"],
            orientation="h", marker_color=CHART_COLORS[0],
            text=[f"{p:.1f}%" for p in strat["pct"]],
            textposition="outside",
            textfont=dict(family="Manrope, sans-serif", size=10, color=CARNEGIE_NAVY),
            hovertemplate=hover_fmt,
        ))
        layout = _base_layout(max(260, len(strat) * 28 + 60))
        layout["margin"] = dict(l=8, r=8, t=8, b=24, autoexpand=True)
        layout["xaxis"] = dict(showgrid=True, gridcolor="#F0EEEA", title="", range=[0, x_max])
        if is_currency:
            layout["xaxis"]["tickprefix"] = "$"
        layout["yaxis"] = dict(showgrid=False, title="", automargin=True)
        fig.update_layout(**layout)
        return _plotly_html(fig)

    # --- Strategy trend ---

    _STRATEGY_TREND_COLORS = ["#A4B9D3", "#FBCFB1", "#E9DBF6", "#B3C7BD", "#FFF8B4"]

    _STRATEGY_TREND_METRIC_LABELS = {
        "total_interactions": "Total Interactions",
        "clicks": "Clicks",
        "ctr": "CTR",
        "direct_conversions": "Direct Interactions",
        "view_through_conversions": "View-through Interactions",
        "in_platform_leads": "In-Platform Leads",
        "budget": "Budget",
        "cost_per_total_interaction": "Cost Per Total Interaction",
    }

    @render.ui
    def dig_strategy_trend():
        df = _dig_q8()
        if df.empty:
            return ui.tags.div("No data available.", class_="empty-state")

        try:
            metric_key = input.dig_strategy_trend_metric()
        except Exception:
            metric_key = "total_interactions"
        metric_label = _STRATEGY_TREND_METRIC_LABELS.get(metric_key, metric_key)

        # Determine top 5 strategies by total_interactions
        top5 = df.groupby("product_name")["total_interactions"].sum().nlargest(5).index.tolist()
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

        # Determine which raw columns to aggregate
        if metric_key == "ctr":
            agg_cols = {"clicks": "sum", "impressions": "sum"}
        elif metric_key == "cost_per_total_interaction":
            agg_cols = {"budget": "sum", "total_interactions": "sum"}
        else:
            agg_cols = {metric_key: "sum"}

        is_rate = metric_key == "ctr"
        is_currency = metric_key in ("budget", "cost_per_total_interaction")

        _series_defs = []
        _series_payloads = []
        for i, prod in enumerate(top5):
            sub = df_top[df_top["product_name"] == prod].groupby("day").agg(agg_cols).reset_index()
            spine = pd.DataFrame({"day": all_days})
            sub = spine.merge(sub, on="day", how="left").fillna(0)
            if metric_key == "ctr":
                sub["_val"] = sub.apply(lambda r: (r["clicks"] / r["impressions"] * 100) if r["impressions"] > 0 else 0, axis=1)
            elif metric_key == "cost_per_total_interaction":
                sub["_val"] = sub.apply(lambda r: (r["budget"] / r["total_interactions"]) if r["total_interactions"] > 0 else 0, axis=1)
            else:
                sub["_val"] = sub[metric_key]

            hover_fmt_val = "$%{y:,.2f}" if is_currency else "%{y:.2f}%" if is_rate else "%{y:,.0f}"
            _txt = [f"${v:,.0f}" for v in sub["_val"]] if is_currency else [f"{v:.1f}%" for v in sub["_val"]] if is_rate else [f"{v:,.0f}" for v in sub["_val"]]
            _clr = _STRATEGY_TREND_COLORS[i % len(_STRATEGY_TREND_COLORS)]
            _series_defs.append({
                "series_idx": i,
                "xs": sub["day"].tolist(),
                "ys": sub["_val"].tolist(),
                "texts": _txt,
                "default_pos": "top center" if i % 2 == 0 else "bottom center",
            })
            _series_payloads.append((prod, sub.copy(), _clr, hover_fmt_val))

        fig = go.Figure()
        for i, (prod, sub, _clr, hover_fmt_val) in enumerate(_series_payloads):
            fig.add_trace(go.Scatter(
                x=sub["day"], y=sub["_val"],
                mode="lines+markers", name=prod,
                line=dict(color=_clr, width=2),
                marker=dict(color=_clr, size=4),
                hovertemplate=f"<b>{prod}</b><br>%{{x|%b %e}}<br>{metric_label}: {hover_fmt_val}<extra></extra>",
            ))

        layout = _base_layout(320)
        layout["xaxis"] = dict(
            tickvals=odd_days, ticktext=[d.strftime("%b ") + str(d.day) for d in odd_days],
            tickfont=dict(family="Manrope, sans-serif", size=10, color="#9B9893"),
            showgrid=False, title="", tickangle=0,
        )
        if is_rate:
            layout["yaxis"]["ticksuffix"] = "%"
        elif is_currency:
            layout["yaxis"]["tickprefix"] = "$"
        fig.update_layout(**layout)
        for i, (_, _, _clr, _) in enumerate(_series_payloads):
            _series_defs[i]["color"] = _clr
            _series_defs[i]["font_size"] = 9
        _add_line_label_annotations(fig, _series_defs, chart_height=320, min_gap_px=20)
        return _plotly_html(fig)

    # --- Subgroup performance table ---

    @render.ui
    def dig_subgroup_table():
        df_c = _dig_q8()
        df_p = _dig_q8_prior()
        if df_c.empty:
            return ui.tags.div("No data available.", class_="empty-state")
        return _build_yoy_comparison_table(df_c, df_p, group_col="subgroup_name", label_col="Subgroup")

    # --- Strategy performance table ---

    @render.ui
    def dig_strategy_table():
        df_c = _dig_q8()
        df_p = _dig_q8_prior()
        if df_c.empty:
            return ui.tags.div("No data available.", class_="empty-state")
        return _build_yoy_comparison_table(df_c, df_p, group_col="product_name", label_col="Strategy")

    # --- Interactions by month & year ---

    @render.ui
    def dig_interactions_by_month():
        # Apply only non-date filters so all years/months are always visible
        df = Q8()
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
        df = Q8()
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

    # Category KPI cards (explicit definitions for Shiny compatibility)

    @render.text
    def dig_cat_total():
        return _fmt_digital_count(_dig_q9()["total_interactions"].sum(), compact=True)

    @render.ui
    def dig_cat_total_delta():
        c = _dig_q9()["total_interactions"].sum()
        p = _dig_q9_prior()
        pv = p["total_interactions"].sum() if not p.empty else 0
        return _fmt_delta(c, pv, label="MoM")

    @render.text
    def dig_cat_rfi():
        return _fmt_digital_count(_dig_q9()[_dig_q9()['interaction_category'] == 'RFI/Lead Gen']['total_interactions'].sum(), compact=True)

    @render.ui
    def dig_cat_rfi_delta():
        c = _dig_q9()[_dig_q9()["interaction_category"] == "RFI/Lead Gen"]["total_interactions"].sum()
        p = _dig_q9_prior()
        pv = p[p["interaction_category"] == "RFI/Lead Gen"]["total_interactions"].sum() if not p.empty else 0
        return _fmt_delta(c, pv, label="MoM")

    @render.text
    def dig_cat_visit():
        return _fmt_digital_count(_dig_q9()[_dig_q9()['interaction_category'] == 'Visit/Event']['total_interactions'].sum(), compact=True)

    @render.ui
    def dig_cat_visit_delta():
        c = _dig_q9()[_dig_q9()["interaction_category"] == "Visit/Event"]["total_interactions"].sum()
        p = _dig_q9_prior()
        pv = p[p["interaction_category"] == "Visit/Event"]["total_interactions"].sum() if not p.empty else 0
        return _fmt_delta(c, pv, label="MoM")

    @render.text
    def dig_cat_apply():
        return _fmt_digital_count(_dig_q9()[_dig_q9()['interaction_category'] == 'Apply']['total_interactions'].sum(), compact=True)

    @render.ui
    def dig_cat_apply_delta():
        c = _dig_q9()[_dig_q9()["interaction_category"] == "Apply"]["total_interactions"].sum()
        p = _dig_q9_prior()
        pv = p[p["interaction_category"] == "Apply"]["total_interactions"].sum() if not p.empty else 0
        return _fmt_delta(c, pv, label="MoM")

    @render.text
    def dig_cat_enroll():
        return _fmt_digital_count(_dig_q9()[_dig_q9()['interaction_category'] == 'Enroll/Deposit']['total_interactions'].sum(), compact=True)

    @render.ui
    def dig_cat_enroll_delta():
        c = _dig_q9()[_dig_q9()["interaction_category"] == "Enroll/Deposit"]["total_interactions"].sum()
        p = _dig_q9_prior()
        pv = p[p["interaction_category"] == "Enroll/Deposit"]["total_interactions"].sum() if not p.empty else 0
        return _fmt_delta(c, pv, label="MoM")

    @render.text
    def dig_cat_other():
        return _fmt_digital_count(_dig_q9()[_dig_q9()['interaction_category'] == 'Other']['total_interactions'].sum(), compact=True)

    @render.ui
    def dig_cat_other_delta():
        c = _dig_q9()[_dig_q9()["interaction_category"] == "Other"]["total_interactions"].sum()
        p = _dig_q9_prior()
        pv = p[p["interaction_category"] == "Other"]["total_interactions"].sum() if not p.empty else 0
        return _fmt_delta(c, pv, label="MoM")

    # --- Cost Metrics panel (Interactions page) ---

    @render.ui
    def dig_int_cost_panel():
        """Cost-per-category metrics for the Interactions page collapsible row."""
        budget_c = _dig_q8()["budget"].sum()
        budget_p = _dig_q8_prior()["budget"].sum()

        q9_c = _dig_q9()
        q9_p = _dig_q9_prior()

        _costs = [
            ("Cost per RFI / Lead Gen", "RFI/Lead Gen"),
            ("Cost per Visit / Events", "Visit/Event"),
            ("Cost per Application", "Apply"),
            ("Cost per Enroll", "Enroll/Deposit"),
            ("Cost per Key Interaction", None),
        ]

        badges = []
        for label, cat in _costs:
            if cat:
                curr_int = q9_c[q9_c["interaction_category"] == cat]["total_interactions"].sum()
                prev_int = q9_p[q9_p["interaction_category"] == cat]["total_interactions"].sum() if not q9_p.empty else 0
            else:
                curr_int = q9_c["total_interactions"].sum()
                prev_int = q9_p["total_interactions"].sum() if not q9_p.empty else 0

            curr_val = _safe_div(budget_c, curr_int)
            prev_val = _safe_div(budget_p, prev_int)

            value_str = fmt_currency(curr_val) if curr_val is not None else "\u2014"
            yoy_el = _fmt_delta(curr_val, prev_val, invert=True, label="MoM")

            badges.append(ui.tags.div(
                ui.tags.div(label, class_="secondary-label"),
                ui.tags.div(
                    ui.tags.div(value_str, class_="secondary-value"),
                    yoy_el,
                    class_="secondary-value-row",
                ),
                class_="secondary-badge dig-metric-badge",
            ))

        return ui.tags.div(
            *badges,
            id="int-cost-metrics-row",
            class_="secondary-row collapsible-row",
            style="display:grid; grid-template-columns:repeat(5, 1fr);",
            title="Cost metrics use total campaign budget divided by category interaction volume.",
        )

    # --- Inline cost metrics for Interactions KPI cards ---

    def _cost_inline_cat(cat_filter, cost_label):
        """Render inline cost for an interaction category card."""
        budget_c = _dig_q8()["budget"].sum()
        budget_p = _dig_q8_prior()["budget"].sum()
        q9_c = _dig_q9()
        q9_p = _dig_q9_prior()
        if cat_filter:
            curr_int = q9_c[q9_c["interaction_category"] == cat_filter]["total_interactions"].sum()
            prev_int = q9_p[q9_p["interaction_category"] == cat_filter]["total_interactions"].sum() if not q9_p.empty else 0
        else:
            curr_int = q9_c["total_interactions"].sum()
            prev_int = q9_p["total_interactions"].sum() if not q9_p.empty else 0
        curr_val = _safe_div(budget_c, curr_int)
        prev_val = _safe_div(budget_p, prev_int)
        value_str = fmt_currency(curr_val) if curr_val is not None else "\u2014"
        yoy_el = _fmt_delta(curr_val, prev_val, invert=True, label="MoM")
        return ui.tags.div(
            ui.tags.div(
                ui.tags.span(cost_label, style="font-size:10px;color:#9B9893;font-weight:600;"),
                ui.tags.span(value_str, style="font-size:12px;font-weight:700;color:#021326;margin-left:6px;"),
                yoy_el,
                style="display:flex;align-items:center;gap:4px;flex-wrap:wrap;",
            ),
            style="margin-top:6px;padding-top:6px;border-top:1px solid #e5e1dc;",
        )

    @render.ui
    def dig_cost_cat_total():
        return _cost_inline_cat(None, "Cost/Key Int.")

    @render.ui
    def dig_cost_cat_rfi():
        return _cost_inline_cat("RFI/Lead Gen", "Cost/RFI")

    @render.ui
    def dig_cost_cat_visit():
        return _cost_inline_cat("Visit/Event", "Cost/Visit")

    @render.ui
    def dig_cost_cat_apply():
        return _cost_inline_cat("Apply", "Cost/Apply")

    @render.ui
    def dig_cost_cat_enroll():
        return _cost_inline_cat("Enroll/Deposit", "Cost/Enroll")

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

        _series_defs = []
        _series_payloads = []
        for i, cat in enumerate(cats):
            sub = (
                df[df["interaction_category"] == cat]
                .groupby("day")["total_interactions"].sum()
                .reset_index()
            )
            spine = pd.DataFrame({"day": all_days})
            sub = spine.merge(sub, on="day", how="left").fillna(0)
            _clr = STRATEGY_COLORS[i % len(STRATEGY_COLORS)]
            _series_defs.append({
                "series_idx": i,
                "xs": sub["day"].tolist(),
                "ys": sub["total_interactions"].tolist(),
                "texts": [f"{v:,.0f}" for v in sub["total_interactions"]],
                "default_pos": "top center" if i % 2 == 0 else "bottom center",
            })
            _series_payloads.append((cat, sub.copy(), _clr))

        fig = go.Figure()
        for i, (cat, sub, _clr) in enumerate(_series_payloads):
            fig.add_trace(go.Scatter(
                x=sub["day"], y=sub["total_interactions"],
                mode="lines+markers", name=cat,
                line=dict(color=_clr, width=2),
                marker=dict(size=4, color=_clr),
                hovertemplate=f"<b>{cat}</b><br>%{{x|%b %e}}<br>Interactions: %{{y:,.0f}}<extra></extra>",
            ))

        layout = _base_layout(340)
        layout["xaxis"] = dict(
            tickvals=tickvals, ticktext=ticktext,
            tickfont=dict(family="Manrope, sans-serif", size=10, color="#9B9893"),
            showgrid=False, title="", tickangle=0,
        )
        fig.update_layout(**layout)
        for i, (_, _, _clr) in enumerate(_series_payloads):
            _series_defs[i]["color"] = _clr
            _series_defs[i]["font_size"] = 9
        _add_line_label_annotations(fig, _series_defs, chart_height=340, min_gap_px=20)
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
        _add_bar_labels(fig)
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
        df_p = _dig_q9_filtered_prior()

        funnel_order = ["RFI/Lead Gen", "Visit/Event", "Apply", "Enroll/Deposit"]

        # Current period pivot
        pivot_c = df.groupby(["product_name", "campaign_name", "interaction_category"])["total_interactions"].sum().reset_index()
        wide_c = pivot_c.pivot_table(
            index=["product_name", "campaign_name"],
            columns="interaction_category", values="total_interactions",
            aggfunc="sum", fill_value=0,
        ).reset_index()
        wide_c.columns.name = None

        # Prior period pivot
        if not df_p.empty:
            pivot_p = df_p.groupby(["product_name", "campaign_name", "interaction_category"])["total_interactions"].sum().reset_index()
            wide_p = pivot_p.pivot_table(
                index=["product_name", "campaign_name"],
                columns="interaction_category", values="total_interactions",
                aggfunc="sum", fill_value=0,
            ).reset_index()
            wide_p.columns.name = None
        else:
            wide_p = pd.DataFrame(columns=["product_name", "campaign_name"])

        cat_cols = [c for c in funnel_order if c in wide_c.columns]
        cat_cols += [c for c in wide_c.columns if c not in ["product_name", "campaign_name"] + cat_cols]
        wide_c["Grand Total"] = wide_c.select_dtypes(include="number").sum(axis=1)
        wide_c = wide_c.sort_values("Grand Total", ascending=False)

        metric_cols = [c for c in cat_cols if c not in ["product_name", "campaign_name"]] + ["Grand Total"]
        rows = []
        for _, r in wide_c.iterrows():
            key = (r["product_name"], r["campaign_name"])
            p_row = wide_p[(wide_p["product_name"] == key[0]) & (wide_p["campaign_name"] == key[1])] if not wide_p.empty else pd.DataFrame()
            metrics = {}
            for col in metric_cols:
                cv = r.get(col, 0) if col in r.index else 0
                pv = p_row[col].sum() if (not p_row.empty and col in p_row.columns) else 0
                metrics[col] = (f"{round(cv):,}", _pct_change(cv, pv))
            rows.append({"label": f"{r['product_name']} | {r['campaign_name']}", "metrics": metrics})

        # Build using YoY delta table with two-part label
        label_col = "Strategy / Campaign"
        return _yoy_delta_table(rows, label_col=label_col, metric_cols=metric_cols)

    # --- Interactions by month pivot ---

    @render.ui
    def dig_interactions_month_table():
        # Always show last 12 months regardless of page date filter
        df_full = Q9()
        # Apply only non-date global filters
        grp = input.dig_group()
        if grp and len(grp) > 0:
            df_full = df_full[df_full["group_name"].isin(grp)]
        sub = input.dig_subgroup()
        if sub and len(sub) > 0:
            df_full = df_full[df_full["subgroup_name"].isin(sub)]
        prod = input.dig_product()
        if prod and len(prod) > 0:
            df_full = df_full[df_full["product_name"].isin(prod)]
        camp = input.dig_campaign()
        if camp and len(camp) > 0:
            df_full = df_full[df_full["campaign_name"].isin(camp)]
        cat = input.dig_interaction_cat()
        if cat and len(cat) > 0:
            df_full = df_full[df_full["interaction_category"].isin(cat)]
        cn = input.dig_conversion_name()
        if cn and len(cn) > 0:
            df_full = df_full[df_full["conversion_name"].isin(cn)]
        if df_full.empty:
            return ui.tags.div("No data available.", class_="empty-state")

        df_full = df_full.copy()
        df_full["month"] = df_full["day"].dt.to_period("M")

        # Last 12 months ending at the latest month in the data
        latest = df_full["month"].max()
        months_12 = pd.period_range(end=latest, periods=12, freq="M")
        month_labels = {str(m): m.to_timestamp().strftime("%b %y") for m in months_12}

        agg = df_full.groupby(["interaction_category", "conversion_name", "month"])["total_interactions"].sum().reset_index()
        agg["ym"] = agg["month"].astype(str)
        agg = agg[agg["ym"].isin(month_labels)]

        wide = agg.pivot_table(
            index=["interaction_category", "conversion_name"],
            columns="ym", values="total_interactions", aggfunc="sum", fill_value=0,
        ).reset_index()
        wide.columns.name = None

        # Ensure all 12 months are present as columns
        for ym in month_labels:
            if ym not in wide.columns:
                wide[ym] = 0

        # Sort columns chronologically
        month_cols = sorted(month_labels.keys())
        wide["Grand Total"] = wide[month_cols].sum(axis=1)
        wide = wide.sort_values("Grand Total", ascending=False)

        # Rename month columns to "Feb 26" format
        wide = wide.rename(columns={
            **month_labels,
            "interaction_category": "Category",
            "conversion_name": "Interaction Name",
        })
        display_month_cols = [month_labels[m] for m in month_cols]
        heatmap_cols = display_month_cols + ["Grand Total"]
        for c in heatmap_cols:
            wide[c] = wide[c].apply(lambda v: f"{round(v):,}" if isinstance(v, (int, float)) else v)

        col_order = ["Category", "Interaction Name"] + display_month_cols + ["Grand Total"]
        return _heatmap_table(wide[[c for c in col_order if c in wide.columns]], heatmap_cols, paginated=True)

    # --- Interactions detail table ---

    @render.ui
    def dig_interactions_detail_table():
        df = _dig_q9_filtered()
        if df.empty:
            return ui.tags.div("No data available.", class_="empty-state")
        df_p = _dig_q9_filtered_prior()

        grp_cols = ["interaction_category", "conversion_name", "product_name", "campaign_name"]
        agg_c = df.groupby(grp_cols).agg(
            direct=("direct_conversions", "sum"),
            vt=("view_through_conversions", "sum"),
            total=("total_interactions", "sum"),
        ).reset_index().sort_values("total", ascending=False)

        agg_p = df_p.groupby(grp_cols).agg(
            direct=("direct_conversions", "sum"),
            vt=("view_through_conversions", "sum"),
            total=("total_interactions", "sum"),
        ).reset_index() if not df_p.empty else pd.DataFrame(columns=grp_cols + ["direct", "vt", "total"])

        metric_cols = ["Direct Key Int.", "View-Through Int.", "Total Key Int."]
        rows = []
        for _, r in agg_c.iterrows():
            key_mask = (
                (agg_p["interaction_category"] == r["interaction_category"]) &
                (agg_p["conversion_name"] == r["conversion_name"]) &
                (agg_p["product_name"] == r["product_name"]) &
                (agg_p["campaign_name"] == r["campaign_name"])
            ) if not agg_p.empty else pd.Series(dtype=bool)
            p_row = agg_p[key_mask] if not agg_p.empty else pd.DataFrame()
            pv_d = p_row["direct"].sum() if not p_row.empty else 0
            pv_v = p_row["vt"].sum() if not p_row.empty else 0
            pv_t = p_row["total"].sum() if not p_row.empty else 0
            label = f"{r['interaction_category']} | {r['conversion_name']} | {r['product_name']} | {r['campaign_name']}"
            rows.append({"label": label, "metrics": {
                "Direct Key Int.":      (f"{round(r['direct']):,}",  _pct_change(r["direct"],  pv_d)),
                "View-Through Int.":    (f"{round(r['vt']):,}",      _pct_change(r["vt"],      pv_v)),
                "Total Key Int.":       (f"{round(r['total']):,}",   _pct_change(r["total"],   pv_t)),
            }})
        return _yoy_delta_table(rows, "Category / Interaction / Strategy / Campaign", metric_cols, paginated=True)

    # ══════════════════════════════════════════════════════════
    # TAB 3: GEOGRAPHY
    # ══════════════════════════════════════════════════════════

    # State name → 2-letter abbreviation lookup
    _STATE_NAME_TO_ABBR = {
        "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
        "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
        "District of Columbia": "DC", "Florida": "FL", "Georgia": "GA", "Hawaii": "HI",
        "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
        "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
        "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
        "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
        "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
        "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
        "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
        "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
        "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
        "Wisconsin": "WI", "Wyoming": "WY", "Puerto Rico": "PR",
    }

    _DIG_GEO_METRIC_LABELS = {
        "impressions": "Impressions by state",
        "clicks": "Clicks by state",
        "total_conversions": "Total Interactions by state",
    }
    _DIG_GEO_METRIC_SHORT = {
        "impressions": "Impressions",
        "clicks": "Clicks",
        "total_conversions": "Total Key Int.",
    }

    _DIG_SMALL_STATES = {"CT", "DE", "DC", "MA", "MD", "NH", "NJ", "RI", "VT"}
    _DIG_STATE_CENTROIDS = {
        "AL": (32.7, -86.7), "AK": (64.2, -153.4), "AZ": (34.3, -111.1),
        "AR": (34.9, -92.4), "CA": (37.2, -119.5), "CO": (39.0, -105.5),
        "CT": (41.6, -72.7), "DE": (39.0, -75.5), "FL": (27.8, -81.7),
        "GA": (32.7, -83.4), "HI": (20.3, -156.4), "ID": (44.4, -114.6),
        "IL": (40.0, -89.2), "IN": (40.3, -86.1), "IA": (42.0, -93.5),
        "KS": (38.5, -98.4), "KY": (37.5, -85.3), "LA": (31.1, -91.9),
        "ME": (45.4, -69.0), "MD": (39.1, -76.8), "MA": (42.3, -71.8),
        "MI": (44.3, -85.4), "MN": (46.4, -93.1), "MS": (32.7, -89.7),
        "MO": (38.3, -92.5), "MT": (46.9, -110.5), "NE": (41.5, -99.9),
        "NV": (39.3, -116.6), "NH": (43.7, -71.6), "NJ": (40.1, -74.5),
        "NM": (34.5, -106.2), "NY": (42.9, -75.5), "NC": (35.5, -79.4),
        "ND": (47.4, -100.5), "OH": (40.4, -82.8), "OK": (35.6, -96.9),
        "OR": (44.0, -120.5), "PA": (40.9, -77.8), "RI": (41.7, -71.5),
        "SC": (33.8, -80.9), "SD": (44.4, -100.4), "TN": (35.9, -86.7),
        "TX": (31.5, -99.3), "UT": (39.3, -111.1), "VT": (44.1, -72.7),
        "VA": (37.5, -78.9), "WA": (47.4, -120.6), "WV": (38.6, -80.6),
        "WI": (44.3, -89.8), "WY": (43.0, -107.6),
        "DC": (38.9, -77.0), "PR": (18.2, -66.5),
    }

    @render.ui
    def dig_geo_map_title():
        try:
            metric = input.dig_geo_metric()
        except Exception:
            metric = "total_conversions"
        label = _DIG_GEO_METRIC_LABELS.get(metric, "Total Interactions by state")
        return ui.tags.h2(label, class_="section-heading", style="margin:0;")

    @render.ui
    def dig_geo_map():
        df = _apply_dig_filters_monthly(Q10())
        if df.empty:
            return ui.tags.div("No data available.", class_="empty-state")

        try:
            metric = input.dig_geo_metric()
        except Exception:
            metric = "total_conversions"
        metric_short = _DIG_GEO_METRIC_SHORT.get(metric, "Total Key Int.")

        # Region is now sanitized to 2-letter state codes, "International", or "Unknown"
        state_df = df[~df["region"].isin(["Unknown", "International", ""])].copy()
        state_df = state_df[state_df["region"].str.match(r"^[A-Z]{2}$", na=False)]
        map_df = state_df.groupby("region")[metric].sum().reset_index()
        map_df.columns = ["abbr", "value"]

        if map_df.empty:
            return ui.tags.div("No mappable state data available.", class_="empty-state")

        import numpy as _np
        z_raw = map_df["value"].fillna(0)
        z_display = z_raw.round(0).astype(int)
        _POW = 0.3
        z_log = z_raw ** _POW
        _max_raw = z_raw.max()
        _tick_vals = [v ** _POW for v in [0, _max_raw * 0.1, _max_raw * 0.3, _max_raw * 0.6, _max_raw]]
        _tick_text = [_fmt_digital_count(v) for v in [0, _max_raw * 0.1, _max_raw * 0.3, _max_raw * 0.6, _max_raw]]

        fig = go.Figure(go.Choropleth(
            locations=map_df["abbr"],
            locationmode="USA-states",
            z=z_log,
            customdata=z_display,
            colorscale=[
                [0, "#FFFFFF"], [0.3, "#FADADB"],
                [0.6, "#F08080"], [1, "#EA332D"],
            ],
            zmin=0, zmax=float(z_log.max()),
            hovertemplate=f"<b>%{{location}}</b><br>{metric_short}: %{{customdata:,}}<extra></extra>",
            colorbar=dict(
                title=metric_short, thickness=12, len=0.6,
                tickvals=_tick_vals, ticktext=_tick_text,
                tickfont=dict(size=11, color=CARNEGIE_GRAY_TEXT),
                title_font=dict(size=11, color=CARNEGIE_GRAY_TEXT),
            ),
        ))
        fig.update_layout(
            font=dict(family="Manrope, sans-serif", color=CARNEGIE_NAVY),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=8, b=8), height=420,
            geo=dict(
                bgcolor="rgba(0,0,0,0)", lakecolor=CARNEGIE_BG,
                landcolor="#eae6e1", showlakes=True, showframe=False,
                scope="usa", projection_type="albers usa",
            ),
        )

        # Text labels for large states
        label_rows = map_df[
            map_df["abbr"].isin(_DIG_STATE_CENTROIDS) &
            ~map_df["abbr"].isin(_DIG_SMALL_STATES) &
            (map_df["value"] > 0)
        ]
        if not label_rows.empty:
            lats = [_DIG_STATE_CENTROIDS[s][0] for s in label_rows["abbr"]]
            lons = [_DIG_STATE_CENTROIDS[s][1] for s in label_rows["abbr"]]
            texts = [f"{s}<br>{_fmt_digital_count(v)}" for s, v in zip(label_rows["abbr"], label_rows["value"])]
            fig.add_scattergeo(
                lat=lats, lon=lons, text=texts, mode="text",
                textfont=dict(family="Manrope, sans-serif", size=9, color="#1A1A1A"),
                showlegend=False, hoverinfo="skip", geo="geo",
            )

        # Top 5 states panel
        top_states = map_df.nlargest(5, "value")
        top_rows = [
            ui.tags.div(
                ui.tags.span(row["abbr"]),
                ui.tags.span(_fmt_digital_count(row["value"]), class_="count"),
                class_="top-state-row",
            )
            for _, row in top_states.iterrows()
        ]

        return ui.tags.div(
            ui.tags.div(_plotly_html(fig, no_toolbar=False)),
            ui.tags.div(
                ui.tags.div("TOP STATES", class_="top-states-title"),
                *top_rows,
                class_="top-states",
            ),
            class_="map-layout",
        )

    @reactive.calc
    def _dig_q10_yoy():
        """Fixed prior academic year Jul 2024 – Jun 2025 for YoY comparison (Q10)."""
        df = Q10()
        df["_month_start"] = pd.to_datetime(
            df["event_year"].astype(str) + "-" + df["event_month"].astype(str).str.zfill(2) + "-01"
        )
        yoy_start = pd.Timestamp("2024-07-01")
        yoy_end = pd.Timestamp("2025-06-30")
        df = df[(df["_month_start"] >= yoy_start) & (df["_month_start"] <= yoy_end)]
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
        return df

    @render.ui
    def dig_geo_table():
        df = _apply_dig_filters_monthly(Q10())
        if df.empty:
            return ui.tags.div("No data available.", class_="empty-state")

        df_p = _dig_q10_yoy()

        try:
            metric = input.dig_geo_metric()
        except Exception:
            metric = "total_conversions"
        metrics = ["impressions", "clicks", "direct_conversions",
                   "view_through_conversions", "total_conversions"]
        agg = df.groupby("region")[metrics].sum().reset_index()
        agg["CTR"] = (agg["clicks"] / agg["impressions"].replace(0, float("nan")) * 100).round(2)

        agg_p = df_p.groupby("region")[metrics].sum().reset_index() if not df_p.empty else pd.DataFrame(columns=["region"] + metrics)

        # Compute International and Unknown summary
        total_impr = agg["impressions"].sum()
        intl_row = agg[agg["region"] == "International"]
        unk_row = agg[agg["region"] == "Unknown"]
        intl_impr = round(intl_row["impressions"].sum()) if not intl_row.empty else 0
        unk_impr = round(unk_row["impressions"].sum()) if not unk_row.empty else 0
        intl_pct = (intl_impr / total_impr * 100) if total_impr > 0 else 0
        unk_pct = (unk_impr / total_impr * 100) if total_impr > 0 else 0

        badge_style = (
            "display:inline-flex;align-items:center;gap:8px;"
            "padding:8px 16px;border-radius:8px;"
            "font-family:Manrope,sans-serif;font-size:13px;font-weight:600;"
        )
        summary_badges = ui.tags.div(
            ui.tags.div(
                ui.tags.span("International", style="color:#6b7280;font-weight:600;"),
                ui.tags.span(_fmt_digital_count(intl_impr), style="color:#021326;"),
                ui.tags.span(f"({intl_pct:.1f}%)", style="color:#9B9893;font-size:11px;"),
                style=badge_style + "background:#f0f7ff;border:1px solid #d0e3f7;",
            ),
            ui.tags.div(
                ui.tags.span("Unknown", style="color:#6b7280;font-weight:600;"),
                ui.tags.span(_fmt_digital_count(unk_impr), style="color:#021326;"),
                ui.tags.span(f"({unk_pct:.1f}%)", style="color:#9B9893;font-size:11px;"),
                style=badge_style + "background:#fef3c7;border:1px solid #f0dfa0;",
            ),
            style="display:flex;gap:16px;margin-bottom:16px;flex-wrap:wrap;",
        )

        # Filter to US state rows only for table display
        us_agg = agg[~agg["region"].isin(["Unknown", "International", ""])].copy()
        us_agg = us_agg.sort_values(metric, ascending=False)

        prev_map = {}
        if not agg_p.empty:
            us_p = agg_p[~agg_p["region"].isin(["Unknown", "International", ""])].copy()
            prev_map = us_p.set_index("region").to_dict(orient="index")

        # Build YoY delta table
        col_labels = ["Impressions", "Clicks", "CTR", "Direct Key Int.",
                      "View-Through Int.", "Total Key Int."]
        rows = []
        for _, r in us_agg.iterrows():
            p = prev_map.get(r["region"], {})
            ctr_curr = r["CTR"]
            ctr_prev = (p.get("clicks", 0) / p.get("impressions", 1) * 100) if p.get("impressions", 0) > 0 else None
            metrics_data = {
                "Impressions":      (f"{round(r['impressions']):,}",         _pct_change(r["impressions"], p.get("impressions", 0)) if p else "N/A"),
                "Clicks":           (f"{round(r['clicks']):,}",              _pct_change(r["clicks"], p.get("clicks", 0)) if p else "N/A"),
                "CTR":              (f"{ctr_curr:.2f}%",                     _pct_change(ctr_curr, ctr_prev) if ctr_prev is not None else "N/A"),
                "Direct Key Int.":  (f"{round(r['direct_conversions']):,}",  _pct_change(r["direct_conversions"], p.get("direct_conversions", 0)) if p else "N/A"),
                "View-Through Int.":(f"{round(r['view_through_conversions']):,}", _pct_change(r["view_through_conversions"], p.get("view_through_conversions", 0)) if p else "N/A"),
                "Total Key Int.":   (f"{round(r['total_conversions']):,}",   _pct_change(r["total_conversions"], p.get("total_conversions", 0)) if p else "N/A"),
            }
            rows.append({"label": r["region"], "metrics": metrics_data})

        table = _yoy_delta_table(rows, "Region", col_labels, paginated=True)
        return ui.tags.div(summary_badges, table)

    # ══════════════════════════════════════════════════════════
    # TAB 4: CREATIVE
    # ══════════════════════════════════════════════════════════
    #
    # CREATIVE SEARCH BAR — Searchable fields:
    #   - campaign_name: Campaign name (e.g., "CWU - UG - Display")
    #   - ad_group: Ad group / ad set name
    #   - product_name: Strategy/platform (e.g., "Display", "Meta")
    #   - platform_campaign_name: Platform-level campaign identifier
    #   - creative: Creative text identifier (size/format info, e.g., "300x250")
    #   - ad_description: Ad description text (when available)
    #   - keyword: Keyword text (PPC Keywords page only)
    #   - match_type: Match type (PPC Keywords page only)
    #
    # NOT SEARCHABLE (data not available in source CSV):
    #   - Creative message text (e.g., ad copy like "See What's Possible")
    #   - Headline text on ad images
    #   - Visual content of creative assets
    #
    # KNOWN LIMITATION (first rollout):
    #   Users cannot search by the actual ad copy or message shown in creatives.
    #   The CSV data provides structural metadata (campaign, ad group, size) but
    #   not the rendered text content of the ads themselves.
    #

    # ── Sub-page product mappings ──

    _CRV_DISPLAY_PRODUCTS = {"Display", "IP Targeting", "Audience Select",
                              "Mobile Footprint", "Discovery", "Mobile Location Targeting"}
    _CRV_SUB_PRODUCT_MAP = {
        "display": _CRV_DISPLAY_PRODUCTS,
        "meta": {"Facebook/Instagram", "Meta"},
        "linkedin": {"LinkedIn"},
        "youtube": {"YouTube", "Youtube"},
        "snapchat": {"Snapchat Snap Ads", "Snapchat"},
        "tiktok": {"TikTok"},
        "spotify": {"Spotify"},
        "reddit": {"Reddit"},
    }

    import re as _re
    _SIZE_RE = _re.compile(r"(\d{2,4}x\d{2,4})")

    def _extract_creative_size(creative_text: str) -> str:
        """Extract ad size (e.g. '300x250') from creative text field."""
        if not creative_text:
            return ""
        m = _SIZE_RE.search(creative_text)
        return m.group(1) if m else ""

    # ── Reactive: base creative data with global + sub-page filters ──

    @reactive.calc
    def _crv_sub_tab():
        try:
            return input.crv_sub()
        except Exception:
            return "display"

    @reactive.calc
    def _crv_display_view():
        """Return 'ad_group' or 'ad_size' for the Display Creative subtoggle."""
        try:
            return input.crv_display_view()
        except Exception:
            return "ad_group"

    @render.ui
    def crv_display_subtoggle():
        if _crv_sub_tab() != "display":
            return None
        return ui.tags.div(
            ui.input_radio_buttons(
                "crv_display_view", None,
                choices={
                    "ad_group": "Display Creative",
                    "ad_size": "Display Creative by Ad Size",
                },
                selected="ad_group",
                inline=True,
            ),
            class_="insight-segmented",
            style="margin-top:8px;",
        )

    @reactive.calc
    def _crv_is_ppc():
        return _crv_sub_tab() == "ppc"

    @reactive.calc
    def _crv_base():
        """Apply global filters + sub-page product filter to creative data."""
        sub = _crv_sub_tab()
        if sub == "ppc":
            # PPC uses keyword data
            df = _apply_dig_filters_monthly(Q11_KEYWORDS())
            # Exclude Reddit
            df = df[~df["product_name"].str.contains("Reddit", case=False, na=False)]
            return df
        if sub == "youtube":
            # YouTube uses its own daily-grain CSV
            df = Q11_YOUTUBE()
            period = input.dig_period()
            if period and len(period) == 2:
                start, end = pd.Timestamp(period[0]), pd.Timestamp(period[1])
                df = df[(df["day"] >= start) & (df["day"] <= end)]
            grp = input.dig_group()
            if grp and len(grp) > 0 and "group_name" in df.columns:
                df = df[df["group_name"].isin(grp)]
            sub_grp = input.dig_subgroup()
            if sub_grp and len(sub_grp) > 0 and "subgroup_name" in df.columns:
                df = df[df["subgroup_name"].isin(sub_grp)]
            prod = input.dig_product()
            if prod and len(prod) > 0 and "product_name" in df.columns:
                df = df[df["product_name"].isin(prod)]
            camp = input.dig_campaign()
            if camp and len(camp) > 0 and "campaign_name" in df.columns:
                df = df[df["campaign_name"].isin(camp)]
            return df
        # All other subs use creative data
        df = _apply_dig_filters_monthly(Q11_CREATIVE())
        products = _CRV_SUB_PRODUCT_MAP.get(sub)
        if products:
            df = df[df["product_name"].isin(products)]
        # Display subtoggle filter
        if sub == "display":
            view = _crv_display_view()
            if view == "ad_size":
                df = df[df["creative"].notna() & (df["creative"].str.strip() != "")]
            else:
                df = df[df["ad_group"].notna() & (df["ad_group"].str.strip() != "")]
        return df

    @reactive.calc
    def _crv_base_prior():
        """Prior period for creative data — shift date range back by 1 month (MoM)."""
        sub_tab = _crv_sub_tab()
        if sub_tab == "youtube":
            df = Q11_YOUTUBE()
            period = input.dig_period()
            if period and len(period) == 2:
                start, end = pd.Timestamp(period[0]), pd.Timestamp(period[1])
                prior_start = start - pd.DateOffset(months=1)
                prior_end = end - pd.DateOffset(months=1)
                df = df[(df["day"] >= prior_start) & (df["day"] <= prior_end)]
            else:
                df = df.iloc[0:0]
        else:
            source = Q11_KEYWORDS() if sub_tab == "ppc" else Q11_CREATIVE()
            df = source
            period = input.dig_period()
            if period and len(period) == 2:
                start, end = pd.Timestamp(period[0]), pd.Timestamp(period[1])
                prior_start = start - pd.DateOffset(months=1)
                prior_end = end - pd.DateOffset(months=1)
                df["_month_start"] = pd.to_datetime(
                    df["event_year"].astype(str) + "-" + df["event_month"].astype(str).str.zfill(2) + "-01"
                )
                df = df[(df["_month_start"] >= prior_start.replace(day=1)) &
                        (df["_month_start"] <= prior_end)]
                df = df.drop(columns=["_month_start"])
            else:
                df = df.iloc[0:0]
        # Apply same global filters
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
        # Apply sub-page product filter
        if sub_tab == "ppc":
            df = df[~df["product_name"].str.contains("Reddit", case=False, na=False)]
        else:
            products = _CRV_SUB_PRODUCT_MAP.get(sub_tab)
            if products and "product_name" in df.columns:
                df = df[df["product_name"].isin(products)]
        # Display subtoggle filter
        if sub_tab == "display":
            view = _crv_display_view()
            if view == "ad_size":
                df = df[df["creative"].notna() & (df["creative"].str.strip() != "")]
            else:
                df = df[df["ad_group"].notna() & (df["ad_group"].str.strip() != "")]
        return df

    def _crv_aggregate(df):
        """Aggregate a creative/keyword DataFrame to row-level grain."""
        if df.empty:
            return df
        is_kw = "keyword" in df.columns
        if is_kw:
            grp_cols = ["platform_campaign_name", "product_name", "keyword", "match_type"]
            str_agg = {}
            num_agg = {c: "sum" for c in ["impressions", "clicks", "direct_conversions",
                                           "budget"] if c in df.columns}
        else:
            # Meta and Display ad_size view: group by creative instead of ad_group
            sub_tab_agg = _crv_sub_tab()
            if sub_tab_agg == "youtube":
                grp_cols = ["platform_campaign_name", "campaign_name", "creative",
                            "image_url", "ad_url"]
                str_agg = {c: "first" for c in ["ad_group", "ad_description", "preview_url",
                                                 "group_name", "subgroup_name", "product_name"] if c in df.columns}
                num_agg = {c: "sum" for c in ["impressions", "clicks", "direct_conversions",
                                               "view_through_conversions", "in_platform_leads",
                                               "total_conversions", "budget",
                                               "video_starts", "video_completions",
                                               ] if c in df.columns}
                if "video_avg" in df.columns:
                    num_agg["video_avg"] = "mean"
                valid_grp = [c for c in grp_cols if c in df.columns]
                agged = df.groupby(valid_grp, as_index=False, dropna=False).agg({**str_agg, **num_agg})
                if "impressions" in agged.columns and "clicks" in agged.columns:
                    agged["ctr"] = (agged["clicks"] / agged["impressions"].replace(0, float("nan")) * 100).round(2)
                else:
                    agged["ctr"] = 0.0
                return agged
            display_view = _crv_display_view() if sub_tab_agg == "display" else None
            exact_creative_tabs = {"meta", "linkedin", "snapchat", "tiktok", "spotify", "reddit"}
            use_exact_creative_grain = sub_tab_agg in exact_creative_tabs
            use_creative_grain = (display_view == "ad_size") or (sub_tab_agg == "meta")
            if use_exact_creative_grain:
                grp_cols = ["platform_campaign_name", "campaign_name", "creative",
                            "image_url", "ad_url"]
                str_agg = {c: "first" for c in ["ad_group", "ad_description", "preview_url",
                                                 "group_name", "subgroup_name", "product_name"] if c in df.columns}
            elif use_creative_grain:
                grp_cols = ["campaign_name", "creative", "product_name",
                            "platform_campaign_name", "group_name", "subgroup_name"]
                str_agg = {c: "first" for c in ["ad_group", "ad_description", "image_url",
                                                 "preview_url", "ad_url"] if c in df.columns}
            else:
                grp_cols = ["campaign_name", "ad_group", "product_name",
                            "platform_campaign_name", "group_name", "subgroup_name"]
                str_agg = {c: "first" for c in ["creative", "ad_description", "image_url",
                                                 "preview_url", "ad_url"] if c in df.columns}
            num_agg = {c: "sum" for c in ["impressions", "clicks", "direct_conversions",
                                           "view_through_conversions", "in_platform_leads",
                                           "total_conversions", "budget",
                                           "visits", "likes", "shares", "comments", "followers",
                                           "video_starts", "video_completions",
                                           ] if c in df.columns}
            # video_avg is a pre-aggregated rate — take mean across rows in the group
            if "video_avg" in df.columns:
                num_agg["video_avg"] = "mean"
            # ad_headline2 is text — preserve via str_agg if not already there
            if "ad_headline2" in df.columns and "ad_headline2" not in str_agg:
                str_agg["ad_headline2"] = "first"
        valid_grp = [c for c in grp_cols if c in df.columns]
        agged = df.groupby(valid_grp, as_index=False).agg({**str_agg, **num_agg})
        if "impressions" in agged.columns and "clicks" in agged.columns:
            agged["ctr"] = (agged["clicks"] / agged["impressions"].replace(0, float("nan")) * 100).round(2)
        else:
            agged["ctr"] = 0.0

        if is_kw:
            # PPC: Total Conv. = direct_conversions, Cost Per Click, Cost Per Direct Conv, Conv Rate
            if "budget" in agged.columns and "clicks" in agged.columns:
                agged["cost_per_click"] = (agged["budget"] / agged["clicks"].replace(0, float("nan"))).round(2)
            else:
                agged["cost_per_click"] = 0.0
            if "budget" in agged.columns and "direct_conversions" in agged.columns:
                agged["cost_per_conversion"] = (agged["budget"] / agged["direct_conversions"].replace(0, float("nan"))).round(2)
            else:
                agged["cost_per_conversion"] = 0.0
            agged["total_conversions"] = agged.get("direct_conversions", 0)
            if "clicks" in agged.columns and "direct_conversions" in agged.columns:
                agged["conv_rate"] = (agged["direct_conversions"] / agged["clicks"].replace(0, float("nan")) * 100).round(2)
            else:
                agged["conv_rate"] = 0.0
        else:
            if "impressions" in agged.columns and "total_conversions" in agged.columns:
                agged["conv_rate"] = (agged["total_conversions"] / agged["impressions"].replace(0, float("nan")) * 100).round(2)
            else:
                agged["conv_rate"] = 0.0
        agged = agged.sort_values("impressions", ascending=False).reset_index(drop=True)
        return agged

    @reactive.calc
    def _crv_agg():
        """Aggregate creative data at the creative-level grain."""
        return _crv_aggregate(_crv_base())

    @reactive.calc
    def _crv_filtered():
        """Apply text search and sorting to aggregated creative/keyword data."""
        df = _crv_agg()
        if df.empty:
            return df
        search = str(input.crv_search()).strip().lower()
        if search:
            mask = pd.Series(False, index=df.index)
            for col in ["campaign_name", "ad_group", "product_name",
                        "platform_campaign_name", "creative", "ad_description",
                        "keyword", "match_type"]:
                if col in df.columns:
                    mask = mask | df[col].fillna("").str.lower().str.contains(search, regex=False)
            df = df[mask].reset_index(drop=True)

        # Sort by selected metric
        try:
            raw = str(input.crv_sort())
        except Exception:
            raw = "impressions"
        ascending = raw.endswith("__asc")
        sort_col = raw.replace("__asc", "")
        if sort_col not in df.columns:
            sort_col = "impressions"
        df = df.sort_values(sort_col, ascending=ascending, na_position="last").reset_index(drop=True)
        return df

    # ── KPI renders (funnel-card pattern) ──

    @render.text
    def dig_crv_total():
        return f"{len(_crv_agg()):,}"

    @render.ui
    def dig_crv_total_delta():
        curr = len(_crv_aggregate(_crv_base()))
        prev = len(_crv_aggregate(_crv_base_prior()))
        return _fmt_delta(curr, prev)

    @render.text
    def dig_crv_impressions():
        df = _crv_agg()
        return _fmt_digital_count(df["impressions"].sum() if not df.empty else 0, compact=True)

    @render.ui
    def dig_crv_impressions_delta():
        curr = _crv_base()["impressions"].sum() if not _crv_base().empty else 0
        prev = _crv_base_prior()["impressions"].sum() if not _crv_base_prior().empty else 0
        return _fmt_delta(curr, prev)

    @render.text
    def dig_crv_ctr():
        df = _crv_agg()
        if df.empty or "impressions" not in df.columns:
            return "0.00%"
        impr = df["impressions"].sum()
        clicks = df["clicks"].sum() if "clicks" in df.columns else 0
        ctr = (clicks / impr * 100) if impr > 0 else 0
        return f"{ctr:.2f}%"

    @render.ui
    def dig_crv_ctr_delta():
        c = _crv_base()
        p = _crv_base_prior()
        c_impr = c["impressions"].sum() if not c.empty else 0
        c_clicks = c["clicks"].sum() if not c.empty else 0
        p_impr = p["impressions"].sum() if not p.empty else 0
        p_clicks = p["clicks"].sum() if not p.empty else 0
        curr = (c_clicks / c_impr * 100) if c_impr > 0 else None
        prev = (p_clicks / p_impr * 100) if p_impr > 0 else None
        return _fmt_delta(curr, prev)

    @render.text
    def dig_crv_conversions():
        df = _crv_agg()
        col = "total_conversions" if "total_conversions" in df.columns else "direct_conversions"
        return _fmt_digital_count(df[col].sum() if not df.empty and col in df.columns else 0, compact=True)

    @render.ui
    def dig_crv_conversions_delta():
        def _conv(d):
            if d.empty:
                return 0
            for c in ["total_conversions", "direct_conversions"]:
                if c in d.columns:
                    return d[c].sum()
            return 0
        return _fmt_delta(_conv(_crv_base()), _conv(_crv_base_prior()))

    # ── Search count badge ──

    @render.ui
    def crv_search_count():
        search = str(input.crv_search()).strip()
        if not search:
            return None
        total = len(_crv_filtered())
        label = "creative" if total == 1 else "creatives"
        return ui.tags.span(
            f"{total} {label} found",
            style=(
                "display:inline-block;"
                "padding:3px 10px;border-radius:9999px;"
                "background:#edeae6;color:#56534e;"
                "font-family:Manrope,sans-serif;font-size:11px;font-weight:600;"
                "white-space:nowrap;"
            ),
        )

    # ── Creative card builder ──

    def _fmt_metric(val):
        """Format a numeric metric for display."""
        if pd.isna(val) or val == 0:
            return "0"
        rounded = round(val)
        abs_val = abs(rounded)
        if abs_val >= 1_000_000_000:
            v = rounded / 1_000_000_000
            s = f"{v:.1f}B"
            return s[:-2] + "B" if s.endswith(".0B") else s
        if abs_val >= 1_000_000:
            v = rounded / 1_000_000
            s = f"{v:.1f}M"
            return s[:-2] + "M" if s.endswith(".0M") else s
        if abs_val >= 1_000:
            v = rounded / 1_000
            s = f"{v:.1f}K"
            return s[:-2] + "K" if s.endswith(".0K") else s
        return f"{rounded:,}"

    def _creative_card(row, card_idx):
        """Build a single creative result card with expand/collapse."""
        sub_tab = _crv_sub_tab()
        campaign = str(row.get("campaign_name", "")).strip()
        ad_group = str(row.get("ad_group", "")).strip()
        tactic = str(row.get("product_name", "")).strip()
        image_url = str(row.get("image_url", "")).strip()
        preview_url = str(row.get("preview_url", "")).strip()
        platform_campaign = str(row.get("platform_campaign_name", "")).strip()
        ad_url = str(row.get("ad_url", "")).strip()
        creative_text = str(row.get("creative", "")).strip()
        ad_desc = str(row.get("ad_description", "")).strip()
        ad_headline2 = str(row.get("ad_headline2", "")).strip()
        tactic_short = tactic.split(" - ")[0] if tactic else ""
        creative_size = _extract_creative_size(creative_text)

        # ── Metrics ──
        impr = row.get("impressions", 0)
        clicks = row.get("clicks", 0)
        ctr = row.get("ctr", 0)
        direct = row.get("direct_conversions", 0)
        vt = row.get("view_through_conversions", 0)
        total_conv = row.get("total_conversions", 0)
        conv_rate = row.get("conv_rate", 0)
        in_platform_leads = row.get("in_platform_leads", 0)
        video_avg = row.get("video_avg", 0)
        visits_val = row.get("visits", 0)
        likes_val = row.get("likes", 0)
        shares_val = row.get("shares", 0)
        comments_val = row.get("comments", 0)
        followers_val = row.get("followers", 0)

        # ── Image data URI ──
        data_uri = None
        if image_url and image_url.startswith("http"):
            data_uri = _get_image_data_uri(image_url)

        def _thumb(css_class="crv-card-img"):
            if data_uri:
                return ui.tags.img(src=data_uri, alt="Creative preview", class_=css_class)
            return ui.tags.div(
                ui.tags.div(tactic_short or "Ad", style=(
                    "font-family:Manrope,sans-serif;font-size:11px;font-weight:700;"
                    "color:#6b7280;text-align:center;line-height:1.3;"
                    "max-width:90px;word-break:break-word;"
                )),
                class_="crv-card-fallback",
                style="display:flex;",
            )

        # ══════════════════════════════════════
        # COLLAPSED SUMMARY ROW
        # ══════════════════════════════════════
        image_box = ui.tags.div(_thumb(), class_="crv-card-image")

        def _meta_text_row(label, value):
            if not value:
                return None
            return ui.tags.div(
                ui.tags.span(label, class_="crv-card-meta-label"),
                ui.tags.span(value, class_="crv-card-meta-value"),
                class_="crv-card-meta-row",
            )

        text_children = []
        if sub_tab == "meta":
            text_children.append(ui.tags.div(platform_campaign or campaign or "Untitled", class_="crv-card-title"))
            r = _meta_text_row("Ad Name: ", creative_text)
            if r: text_children.append(r)
            r = _meta_text_row("Description: ", ad_desc)
            if r: text_children.append(r)
        elif sub_tab in ("linkedin", "youtube"):
            text_children.append(ui.tags.div(platform_campaign or campaign or "Untitled", class_="crv-card-title"))
            r = _meta_text_row("Description: ", ad_headline2)
            if r: text_children.append(r)
        elif sub_tab in ("snapchat", "tiktok", "spotify", "reddit"):
            text_children.append(ui.tags.div(platform_campaign or campaign or "Untitled", class_="crv-card-title"))
            r = _meta_text_row("Description: ", creative_text)
            if r: text_children.append(r)
        else:
            # display sub-tabs
            text_children.append(ui.tags.div(campaign or "Untitled Creative", class_="crv-card-title"))
            if tactic:
                text_children.append(ui.tags.div(
                    ui.tags.span("Tactic: ", class_="crv-card-meta-label"),
                    ui.tags.span(tactic, class_="crv-card-meta-value"),
                    class_="crv-card-meta-row",
                ))
            display_view = _crv_display_view() if sub_tab == "display" else None
            if display_view == "ad_size":
                if creative_size:
                    text_children.append(ui.tags.div(
                        ui.tags.span("Creative Size: ", class_="crv-card-meta-label"),
                        ui.tags.span(creative_size, class_="crv-card-meta-value"),
                        class_="crv-card-meta-row",
                    ))
            else:
                if ad_group:
                    text_children.append(ui.tags.div(
                        ui.tags.span("Ad Group: ", class_="crv-card-meta-label"),
                        ui.tags.span(ad_group, class_="crv-card-meta-value"),
                        class_="crv-card-meta-row",
                    ))
        text_section = ui.tags.div(*text_children, class_="crv-card-text")

        def _metric_cell(label, value):
            return ui.tags.div(
                ui.tags.div(label, class_="crv-metric-label"),
                ui.tags.div(value, class_="crv-metric-value"),
                class_="crv-metric-cell",
            )

        _ctr_fmt = f"{ctr:.2f}%" if pd.notna(ctr) else "—"
        _cr_fmt = f"{conv_rate:.2f}%" if pd.notna(conv_rate) else "—"
        _va_fmt = f"{video_avg:.2f}%" if pd.notna(video_avg) and video_avg else "—"

        if sub_tab == "meta":
            metrics_summary = ui.tags.div(
                _metric_cell("Impressions", _fmt_metric(impr)),
                _metric_cell("Clicks", _fmt_metric(clicks)),
                _metric_cell("CTR", _ctr_fmt),
                _metric_cell("Direct Int.", _fmt_metric(direct)),
                _metric_cell("View-through Int.", _fmt_metric(vt)),
                _metric_cell("Total Int.", _fmt_metric(total_conv)),
                class_="crv-metric-grid",
            )
        elif sub_tab == "linkedin":
            metrics_summary = ui.tags.div(
                _metric_cell("Impressions", _fmt_metric(impr)),
                _metric_cell("Clicks", _fmt_metric(clicks)),
                _metric_cell("CTR", _ctr_fmt),
                _metric_cell("Direct Int.", _fmt_metric(direct)),
                _metric_cell("View-through Int.", _fmt_metric(vt)),
                _metric_cell("In-Platform Leads", _fmt_metric(in_platform_leads)),
                _metric_cell("Total Int.", _fmt_metric(total_conv)),
                _metric_cell("Int. Rate", _cr_fmt),
                class_="crv-metric-grid",
            )
        elif sub_tab == "youtube":
            metrics_summary = ui.tags.div(
                _metric_cell("Impressions", _fmt_metric(impr)),
                _metric_cell("Clicks", _fmt_metric(clicks)),
                _metric_cell("CTR", _ctr_fmt),
                _metric_cell("YouTube View Rate", _va_fmt),
                _metric_cell("View-through Int.", _fmt_metric(vt)),
                _metric_cell("In-Platform Leads", _fmt_metric(in_platform_leads)),
                _metric_cell("Total Int.", _fmt_metric(total_conv)),
                _metric_cell("Int. Rate", _cr_fmt),
                class_="crv-metric-grid",
            )
        elif sub_tab == "snapchat":
            metrics_summary = ui.tags.div(
                _metric_cell("Impressions", _fmt_metric(impr)),
                _metric_cell("Clicks (Swipe Ups)", _fmt_metric(clicks)),
                _metric_cell("CTR (Swipe Up Rate)", _ctr_fmt),
                _metric_cell("Total Int.", _fmt_metric(total_conv)),
                _metric_cell("Int. Rate", _cr_fmt),
                class_="crv-metric-grid",
            )
        elif sub_tab == "tiktok":
            metrics_summary = ui.tags.div(
                _metric_cell("Impressions", _fmt_metric(impr)),
                _metric_cell("Clicks", _fmt_metric(clicks)),
                _metric_cell("CTR", _ctr_fmt),
                _metric_cell("Total Int.", _fmt_metric(total_conv)),
                _metric_cell("Int. Rate", _cr_fmt),
                _metric_cell("Profile Visits", _fmt_metric(visits_val)),
                _metric_cell("Likes", _fmt_metric(likes_val)),
                _metric_cell("Shares", _fmt_metric(shares_val)),
                _metric_cell("Comments", _fmt_metric(comments_val)),
                _metric_cell("Followers", _fmt_metric(followers_val)),
                class_="crv-metric-grid",
            )
        elif sub_tab == "spotify":
            metrics_summary = ui.tags.div(
                _metric_cell("Impressions", _fmt_metric(impr)),
                _metric_cell("Clicks", _fmt_metric(clicks)),
                _metric_cell("CTR", _ctr_fmt),
                class_="crv-metric-grid",
            )
        elif sub_tab == "reddit":
            metrics_summary = ui.tags.div(
                _metric_cell("Impressions", _fmt_metric(impr)),
                _metric_cell("Clicks", _fmt_metric(clicks)),
                _metric_cell("CTR", _ctr_fmt),
                _metric_cell("Total Int.", _fmt_metric(total_conv)),
                class_="crv-metric-grid",
            )
        else:
            # display tabs
            _is_display = sub_tab == "display"
            metrics_summary = ui.tags.div(
                _metric_cell("Impressions", _fmt_metric(impr)),
                _metric_cell("Clicks", _fmt_metric(clicks)),
                _metric_cell("CTR", _ctr_fmt),
                _metric_cell("View-through Int." if _is_display else "View-through Conv.", _fmt_metric(vt)),
                _metric_cell("Total Int." if _is_display else "Total Conv.", _fmt_metric(total_conv)),
                _metric_cell("Int. Rate", _cr_fmt),
                class_="crv-metric-grid",
            )

        # Details toggle button
        card_id = f"crv-expand-{card_idx}"
        toggle_btn = ui.tags.button(
            ui.tags.span("Details", class_="crv-toggle-label"),
            ui.tags.span("▾", class_="crv-toggle-chevron"),
            class_="crv-details-btn",
            onclick=f"window._crvToggle('{card_id}', this)",
        )

        summary_row = ui.tags.div(
            image_box,
            ui.tags.div(text_section, metrics_summary, class_="crv-card-body"),
            ui.tags.div(toggle_btn, class_="crv-card-actions"),
            class_="crv-card-summary",
        )

        # ══════════════════════════════════════
        # EXPANDED PANEL  (3-column layout)
        # ══════════════════════════════════════

        # ── Col 1: Creative preview ──
        col_image = ui.tags.div(
            ui.tags.div(_thumb("crv-card-img-lg"), class_="crv-expand-image"),
            class_="crv-expand-col-img",
        )

        # ── Col 2: Performance metrics + insight chips ──
        def _detail_metric(label, value):
            return ui.tags.div(
                ui.tags.div(label, class_="crv-dm-label"),
                ui.tags.div(value, class_="crv-dm-value"),
                class_="crv-dm-cell",
            )

        reach_group = ui.tags.div(
            ui.tags.div("Reach & Engagement", class_="crv-dm-group-title"),
            ui.tags.div(
                _detail_metric("Impressions", _fmt_metric(impr)),
                _detail_metric("Clicks", _fmt_metric(clicks)),
                _detail_metric("CTR", _ctr_fmt),
                class_="crv-dm-grid",
            ),
            class_="crv-dm-group",
        )

        if sub_tab == "linkedin":
            conv_detail_cells = [
                _detail_metric("Direct Int.", _fmt_metric(direct)),
                _detail_metric("View-through Int.", _fmt_metric(vt)),
                _detail_metric("In-Platform Leads", _fmt_metric(in_platform_leads)),
                _detail_metric("Total Int.", _fmt_metric(total_conv)),
                _detail_metric("Int. Rate", _cr_fmt),
            ]
        elif sub_tab == "youtube":
            conv_detail_cells = [
                _detail_metric("YouTube View Rate", _va_fmt),
                _detail_metric("View-through Int.", _fmt_metric(vt)),
                _detail_metric("In-Platform Leads", _fmt_metric(in_platform_leads)),
                _detail_metric("Total Int.", _fmt_metric(total_conv)),
                _detail_metric("Int. Rate", _cr_fmt),
            ]
        elif sub_tab in ("snapchat", "tiktok"):
            conv_detail_cells = [
                _detail_metric("Total Int.", _fmt_metric(total_conv)),
                _detail_metric("Int. Rate", _cr_fmt),
            ]
        elif sub_tab == "reddit":
            conv_detail_cells = [
                _detail_metric("Total Int.", _fmt_metric(total_conv)),
            ]
        elif sub_tab == "meta":
            conv_detail_cells = [
                _detail_metric("Direct Int.", _fmt_metric(direct)),
                _detail_metric("View-through Int.", _fmt_metric(vt)),
                _detail_metric("Total Int.", _fmt_metric(total_conv)),
            ]
        elif sub_tab == "spotify":
            conv_detail_cells = []
        else:
            # display
            conv_detail_cells = [
                _detail_metric("Direct", _fmt_metric(direct)),
                _detail_metric("View-through", _fmt_metric(vt)),
                _detail_metric("Total", _fmt_metric(total_conv)),
                _detail_metric("Int. Rate", _cr_fmt),
            ]

        conv_group = ui.tags.div(
            ui.tags.div("Interactions", class_="crv-dm-group-title"),
            ui.tags.div(*conv_detail_cells, class_="crv-dm-grid"),
            class_="crv-dm-group",
        ) if conv_detail_cells else ""

        # Insight chips
        chips = []
        ctr_val = ctr if pd.notna(ctr) else 0
        conv_rate_val = conv_rate if pd.notna(conv_rate) else 0
        impr_val = impr if pd.notna(impr) else 0
        clicks_val = clicks if pd.notna(clicks) else 0
        direct_val = direct if pd.notna(direct) else 0
        vt_val = vt if pd.notna(vt) else 0
        total_val = total_conv if pd.notna(total_conv) else 0

        if ctr_val >= 2:
            chips.append(("positive", "Strong CTR"))
        elif ctr_val < 0.5 and impr_val > 0:
            chips.append(("warning", "CTR below benchmark"))

        if clicks_val >= 1000:
            chips.append(("positive", "Strong click volume"))

        if conv_rate_val >= 5:
            chips.append(("positive", "Interaction efficiency strong"))
        elif conv_rate_val < 0.5 and impr_val > 1000:
            chips.append(("warning", "Int. rate low"))

        if direct_val == 0 and vt_val > 0:
            chips.append(("neutral", "No direct interactions"))

        if total_val > 0 and vt_val / total_val > 0.7:
            chips.append(("neutral", "High view-through share"))

        if total_val == 0 and impr_val > 0 and sub_tab not in ("spotify",):
            chips.append(("warning", "No interactions recorded"))

        chip_els = [ui.tags.span(text, class_=f"crv-chip crv-chip--{tone}") for tone, text in chips]
        chip_section = ui.tags.div(*chip_els, class_="crv-chip-row") if chip_els else ""

        col_metrics = ui.tags.div(
            reach_group, conv_group, chip_section,
            class_="crv-expand-col-metrics",
        )

        # ── Col 3: Metadata card ──
        def _meta_row(label, value, is_link=False):
            if not value:
                return None
            if is_link and value.startswith("http"):
                val_el = ui.tags.a(
                    value if len(value) <= 50 else value[:47] + "...",
                    href=value, target="_blank", class_="crv-meta-link",
                    title=value,
                )
            else:
                val_el = ui.tags.span(value, class_="crv-expand-meta-val")
            return ui.tags.div(
                ui.tags.span(label, class_="crv-expand-meta-key"),
                val_el,
                class_="crv-expand-meta-row",
            )

        def _preview_row(label="Ad Preview", click_to_view=True):
            if not (preview_url and preview_url.startswith("http")):
                return None
            link_text = "Click to View" if click_to_view else (
                preview_url if len(preview_url) <= 50 else preview_url[:47] + "..."
            )
            return ui.tags.div(
                ui.tags.span(label, class_="crv-expand-meta-key"),
                ui.tags.a(link_text, href=preview_url, target="_blank", class_="crv-meta-link",
                          title=preview_url),
                class_="crv-expand-meta-row",
            )

        if sub_tab == "meta":
            meta_rows = [r for r in [
                _meta_row("Landing Page", ad_url, is_link=True),
                _preview_row(click_to_view=True),
                _meta_row("Image URL", image_url, is_link=True),
            ] if r is not None]
        elif sub_tab == "linkedin":
            meta_rows = [r for r in [
                _meta_row("Landing Page", ad_url, is_link=True),
                _preview_row(click_to_view=True),
            ] if r is not None]
        elif sub_tab == "youtube":
            meta_rows = [r for r in [
                _meta_row("Landing Page", ad_url, is_link=True),
            ] if r is not None]
        elif sub_tab == "snapchat":
            meta_rows = [r for r in [
                _meta_row("Landing Page", ad_url, is_link=True),
                _preview_row(click_to_view=True),
            ] if r is not None]
        elif sub_tab in ("tiktok", "spotify", "reddit"):
            meta_rows = [r for r in [
                _meta_row("Landing Page", ad_url, is_link=True),
                _preview_row(click_to_view=False),
            ] if r is not None]
        else:
            # display tabs
            display_view_meta = _crv_display_view() if sub_tab == "display" else None
            if display_view_meta == "ad_size":
                meta_rows = [r for r in [
                    _meta_row("Tactic", tactic),
                    _meta_row("Platform Campaign", platform_campaign),
                    _meta_row("Creative Size", creative_size) if creative_size else None,
                    _meta_row("Creative", creative_text) if creative_text else None,
                    _meta_row("Image URL", image_url, is_link=True),
                    _meta_row("Landing Page", ad_url, is_link=True),
                ] if r is not None]
            else:
                meta_rows = [r for r in [
                    _meta_row("Tactic", tactic),
                    _meta_row("Platform Campaign", platform_campaign),
                    _meta_row("Ad Group", ad_group) if ad_group else None,
                    _meta_row("Image URL", image_url, is_link=True),
                    _meta_row("Landing Page", ad_url, is_link=True),
                ] if r is not None]

        col_meta = ui.tags.div(
            ui.tags.div("Details", class_="crv-expand-meta-title"),
            *meta_rows,
            class_="crv-expand-col-meta",
        ) if meta_rows else ""

        expanded_panel = ui.tags.div(
            col_image, col_metrics, col_meta,
            class_="crv-expand-panel",
            id=card_id,
            style="display:none;",
        )

        # ══════════════════════════════════════
        # FULL CARD
        # ══════════════════════════════════════
        return ui.tags.div(summary_row, expanded_panel, class_="crv-card")

    # ── Card list render ──

    def _ppc_table(df):
        """Render PPC keyword data as a table."""
        display = df.copy()
        # Build display columns
        col_map = {
            "platform_campaign_name": "Campaign Name",
            "keyword": "Keyword",
            "match_type": "Match Type",
        }
        metric_cols = ["impressions", "clicks", "ctr", "cost_per_click",
                       "total_conversions", "cost_per_conversion", "conv_rate"]
        metric_labels = {
            "impressions": "Impressions",
            "clicks": "Clicks",
            "ctr": "CTR",
            "cost_per_click": "Cost Per Click",
            "total_conversions": "Direct Int.",
            "cost_per_conversion": "Cost Per Direct Int.",
            "conv_rate": "Int. Rate",
        }
        # Format columns
        for c in ["impressions", "clicks"]:
            if c in display.columns:
                display[c] = display[c].apply(lambda v: f"{round(v):,}" if pd.notna(v) else "0")
        for c in ["ctr", "conv_rate"]:
            if c in display.columns:
                display[c] = display[c].apply(lambda v: f"{v:.2f}%" if pd.notna(v) else "—")
        for c in ["cost_per_click", "cost_per_conversion"]:
            if c in display.columns:
                display[c] = display[c].apply(lambda v: f"${v:,.2f}" if pd.notna(v) and v != float("inf") else "—")
        if "total_conversions" in display.columns:
            display["total_conversions"] = display["total_conversions"].apply(
                lambda v: f"{round(v):,}" if pd.notna(v) else "0")

        # Rename and select
        rename = {**col_map, **metric_labels}
        display = display.rename(columns=rename)
        text_cols = set(col_map.values())
        show_cols = [rename.get(c, c) for c in list(col_map.keys()) + metric_cols if rename.get(c, c) in display.columns]
        display = display[[c for c in show_cols if c in display.columns]]
        heatmap_cols = [c for c in show_cols if c not in text_cols]
        return ui.tags.div(
            _heatmap_table(display, heatmap_cols, paginated=True),
            class_="carnegie-table-card",
        )

    @render.ui
    def crv_card_list():
        df = _crv_filtered()
        sub_tab = _crv_sub_tab()
        empty_label = "keywords" if sub_tab == "ppc" else "creatives"
        if df.empty:
            return ui.tags.div(f"No {empty_label} available for the selected filters.",
                               class_="empty-state",
                               style="padding:40px 0;text-align:center;color:#6b7280;font-size:14px;")

        # PPC: render as table
        if sub_tab == "ppc":
            return _ppc_table(df)

        # Creative sub-pages: render as cards with pagination
        per_page = _crv_per_page()
        page = _crv_current_page()
        total = len(df)
        max_page = max(1, -(-total // per_page))
        page = min(page, max_page)
        start = (page - 1) * per_page
        end = min(start + per_page, total)
        page_df = df.iloc[start:end]

        cards = [_creative_card(row, start + i) for i, (_, row) in enumerate(page_df.iterrows())]
        return ui.tags.div(
            *cards, class_="crv-card-list",
            style="display:flex;flex-direction:column;gap:16px;margin-bottom:28px;",
        )

    # ── Pagination helpers ──

    @reactive.effect
    @reactive.event(input.crv_search, input.crv_sub, input.dig_period,
                    input.dig_group, input.dig_subgroup, input.dig_product, input.dig_campaign)
    def _crv_reset_page():
        ui.insert_ui(
            ui.tags.script("Shiny.setInputValue('crv_page', 1);"),
            selector="body", where="beforeEnd",
        )

    @reactive.calc
    def _crv_per_page():
        try:
            v = input.crv_per_page()
            return max(1, int(v))
        except Exception:
            return 10

    @reactive.calc
    def _crv_current_page():
        try:
            v = input.crv_page()
            return max(1, int(v))
        except Exception:
            return 1

    @render.ui
    def crv_pag_range():
        df = _crv_filtered()
        total = len(df)
        if total == 0:
            return ui.tags.span("No results", class_="insight-pag-text")
        per_page = _crv_per_page()
        page = min(_crv_current_page(), max(1, -(-total // per_page)))
        start = (page - 1) * per_page + 1
        end = min(page * per_page, total)
        return ui.tags.span(f"{start}–{end} of {total}", class_="insight-pag-text")

    @render.ui
    def crv_pag_buttons():
        df = _crv_filtered()
        total = len(df)
        per_page = _crv_per_page()
        max_page = max(1, -(-total // per_page))
        page = min(_crv_current_page(), max_page)

        prev_disabled = "disabled" if page <= 1 else ""
        next_disabled = "disabled" if page >= max_page else ""

        return ui.tags.div(
            ui.tags.button(
                "\u25C0 Prev", class_=f"insight-pag-btn {prev_disabled}",
                onclick=f"Shiny.setInputValue('crv_page', {page - 1});",
            ),
            ui.tags.span(f"Page {page} of {max_page}", class_="insight-pag-text",
                         style="margin:0 12px;"),
            ui.tags.button(
                "Next \u25B6", class_=f"insight-pag-btn {next_disabled}",
                onclick=f"Shiny.setInputValue('crv_page', {page + 1});",
            ),
            style="display:flex;align-items:center;",
        )

    # ══════════════════════════════════════════════════════════
    # TAB 5: INSIGHTS
    # ══════════════════════════════════════════════════════════

    @reactive.calc
    def _dig_notes():
        df = Q12()
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

    # ── Helpers for Insights card rendering ──

    def _insight_card(row, show_campaign=False):
        """Build a single insight card from a DataFrame row."""
        note_type = row.get("note_type", "")
        is_milestone = str(row.get("is_milestone", "")).strip().lower() == "yes"
        date_str = row["day"].strftime("%b %d, %Y") if pd.notna(row.get("day")) else ""
        notes = str(row.get("notes", "")).strip()
        campaign = str(row.get("campaign_name", "")).strip()

        # Build headline: first sentence or first 100 chars
        headline = notes.split(". ")[0].split(".\n")[0]
        if len(headline) > 100:
            headline = headline[:97] + "..."
        if headline and not headline.endswith("."):
            headline += "."

        # Preview = remainder after headline, truncated
        remainder = notes[len(headline.rstrip(".")):].strip().lstrip(".").strip()
        preview = remainder[:200] + "..." if len(remainder) > 200 else remainder

        # Unique id for expand/collapse
        card_id = f"ic_{hash(str(row.get('day','')) + notes[:30]) & 0xFFFFFFFF:08x}"

        # ── Section 1: Header (metadata row) ──
        type_colors = {
            "Performance": ("#021326", "#e8e6e0"),
            "Performance with Recommendation": ("#7c3aed", "#ede9fe"),
            "Optimization": ("#0369a1", "#e0f2fe"),
            "Campaign Launch": ("#047857", "#d1fae5"),
            "Budget": ("#b45309", "#fef3c7"),
            "Key Dates": ("#be185d", "#fce7f3"),
        }
        bg, fg = type_colors.get(note_type, ("#6b7280", "#f3f4f6"))[::-1]

        meta_items = [
            ui.tags.span(
                note_type.upper(), class_="insight-type-badge",
                style=(
                    f"background:{bg};color:{fg};"
                    "display:inline-block;padding:3px 11px;border-radius:9999px;"
                    "font-family:Manrope,sans-serif;font-size:10px;font-weight:700;"
                    "letter-spacing:0.06em;text-transform:uppercase;line-height:1.5;white-space:nowrap;"
                ),
            ),
        ]
        if is_milestone:
            meta_items.append(
                ui.tags.span(
                    "\u2605 MILESTONE", class_="insight-milestone-badge",
                    style=(
                        "display:inline-block;padding:3px 11px;border-radius:9999px;"
                        "font-family:Manrope,sans-serif;font-size:10px;font-weight:700;"
                        "letter-spacing:0.04em;background:#fef3c7;color:#92400e;"
                        "line-height:1.5;white-space:nowrap;"
                    ),
                )
            )
        meta_items.append(ui.tags.span(
            date_str, class_="insight-date",
            style="font-family:Manrope,sans-serif;font-size:12px;font-weight:500;color:#6b7280;margin-left:auto;white-space:nowrap;",
        ))

        header = ui.tags.div(
            *meta_items,
            class_="insight-card-header",
            style=(
                "display:flex;align-items:center;gap:10px;flex-wrap:wrap;"
                "padding:16px 24px 12px;border-bottom:1px solid #edeae6;"
                "background:#fcfbf9;border-radius:14px 14px 0 0;"
            ),
        )

        # ── Section 2: Body (content area) ──
        body_children = []
        if show_campaign and campaign:
            body_children.append(ui.tags.div(
                ui.tags.span("Campaign:", class_="insight-campaign-label",
                             style="font-weight:700;color:#6b7280;text-transform:uppercase;font-size:10px;letter-spacing:0.05em;"),
                ui.tags.span(campaign, class_="insight-campaign-name",
                             style="font-weight:600;color:#021326;font-size:13px;"),
                class_="insight-campaign-row",
                style="display:flex;align-items:center;gap:6px;margin-bottom:12px;padding:8px 12px;background:#f5f3ef;border:1px solid #edeae6;border-radius:8px;",
            ))
        body_children.append(ui.tags.div(
            headline, class_="insight-headline",
            style="font-size:15px;font-weight:700;color:#021326;line-height:1.5;margin-bottom:6px;",
        ))
        if preview:
            body_children.append(ui.tags.div(
                preview, class_="insight-preview",
                style="font-size:13.5px;color:#56534e;line-height:1.65;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;",
            ))

        body = ui.tags.div(
            *body_children,
            class_="insight-card-body",
            style="padding:18px 24px 14px;",
        )

        # ── Section 3: Footer (only if there's more text beyond the headline) ──
        has_more = bool(remainder.strip())

        sections = [header, body]

        if has_more:
            toggle_js = (
                f"var b=document.getElementById('{card_id}');"
                "var link=this;"
                "if(b.style.display==='none'){"
                "  b.style.display='block';"
                "  link.textContent='\\u25BE Hide full analysis';"
                "}else{"
                "  b.style.display='none';"
                "  link.textContent='\\u25B8 View full analysis';"
                "}"
            )

            footer = ui.tags.div(
                ui.tags.a(
                    "\u25B8 View full analysis",
                    href="javascript:void(0)",
                    onclick=toggle_js,
                    class_="insight-expand-link",
                    style="font-size:12px;font-weight:600;color:#FA3320;text-decoration:none;",
                ),
                ui.tags.div(
                    ui.tags.div(notes, class_="insight-full-text",
                                style="font-size:13.5px;color:#021326;line-height:1.75;white-space:pre-wrap;word-break:break-word;"),
                    id=card_id,
                    class_="insight-expand-body",
                    style="display:none;margin-top:14px;padding-top:14px;border-top:1px solid #edeae6;",
                ),
                class_="insight-card-footer",
                style=(
                    "padding:12px 24px 14px;background:#faf9f7;"
                    "border-top:1px solid #edeae6;border-radius:0 0 14px 14px;"
                ),
            )
            sections.append(footer)

        return ui.tags.div(
            *sections,
            class_="insight-card",
            style=(
                "background:#ffffff;border:1px solid #d9d5cf;"
                "border-radius:14px;box-shadow:0 1px 4px rgba(0,0,0,0.05);"
                "overflow:hidden;margin-bottom:0;padding:0;"
            ),
        )

    @reactive.calc
    def _insights_view_data():
        """Return filtered data for the active insights view."""
        df = _dig_notes()
        view = input.insights_view()
        if view == "performance":
            df = df[df["note_type"].str.contains("Performance", case=False, na=False)]
        else:
            df = df[
                (df["note_type"] == "Optimization")
                | df["note_type"].str.contains("Campaign", case=False, na=False)
                | df["note_type"].str.contains("Budget", case=False, na=False)
            ]
        # Text search filter
        search = str(input.insights_search()).strip().lower()
        if search:
            mask = pd.Series(False, index=df.index)
            for col in ["notes", "campaign_name", "note_type"]:
                if col in df.columns:
                    mask = mask | df[col].fillna("").str.lower().str.contains(search, regex=False)
            df = df[mask]
        return df.sort_values("day", ascending=False).reset_index(drop=True)

    # Reset page to 1 when view or filters change
    @reactive.effect
    @reactive.event(input.insights_view, input.dig_milestone_only, input.dig_note_type,
                    input.dig_period, input.insights_search)
    def _insights_reset_page():
        try:
            from shiny.session import session_context
        except Exception:
            pass
        # Push page back to 1 on the client
        ui.insert_ui(
            ui.tags.script("Shiny.setInputValue('insights_page', 1);"),
            selector="body", where="beforeEnd",
        )

    @reactive.calc
    def _insights_per_page():
        try:
            v = input.insights_per_page()
            return max(1, int(v))
        except Exception:
            return 10

    @reactive.calc
    def _insights_current_page():
        try:
            v = input.insights_page()
            return max(1, int(v))
        except Exception:
            return 1

    @render.ui
    def insights_search_count():
        search = str(input.insights_search()).strip()
        if not search:
            return None
        total = len(_insights_view_data())
        label = "note" if total == 1 else "notes"
        return ui.tags.span(
            f"{total} {label} found",
            style=(
                "display:inline-block;"
                "padding:3px 10px;border-radius:9999px;"
                "background:#edeae6;color:#56534e;"
                "font-family:Manrope,sans-serif;font-size:11px;font-weight:600;"
                "white-space:nowrap;"
            ),
        )

    @render.ui
    def insights_card_list():
        df = _insights_view_data()
        if df.empty:
            return ui.tags.div("No insights available for the selected filters.",
                               class_="empty-state")
        per_page = _insights_per_page()
        page = _insights_current_page()
        total = len(df)
        max_page = max(1, -(-total // per_page))  # ceil division
        page = min(page, max_page)
        start = (page - 1) * per_page
        end = min(start + per_page, total)
        page_df = df.iloc[start:end]

        show_campaign = input.insights_view() == "optimization"
        cards = [_insight_card(row, show_campaign=show_campaign)
                 for _, row in page_df.iterrows()]
        return ui.tags.div(
            *cards, class_="insight-card-list",
            style="display:flex;flex-direction:column;gap:16px;margin-bottom:28px;",
        )

    @render.ui
    def insights_pag_range():
        df = _insights_view_data()
        total = len(df)
        if total == 0:
            return ui.tags.span("No results", class_="insight-pag-text")
        per_page = _insights_per_page()
        page = min(_insights_current_page(), max(1, -(-total // per_page)))
        start = (page - 1) * per_page + 1
        end = min(page * per_page, total)
        return ui.tags.span(f"{start}\u2013{end} of {total}", class_="insight-pag-text")

    @render.ui
    def insights_pag_buttons():
        df = _insights_view_data()
        total = len(df)
        per_page = _insights_per_page()
        max_page = max(1, -(-total // per_page))
        page = min(_insights_current_page(), max_page)

        if max_page <= 1:
            return ui.tags.span()

        def _page_btn(label, target, disabled=False, active=False):
            cls = "insight-pag-btn"
            if active:
                cls += " insight-pag-btn--active"
            if disabled:
                cls += " insight-pag-btn--disabled"
            return ui.tags.button(
                label,
                class_=cls,
                disabled="disabled" if disabled else None,
                onclick=f"Shiny.setInputValue('insights_page', {target});" if not disabled else None,
            )

        buttons = []
        # Prev
        buttons.append(_page_btn("\u2039", page - 1, disabled=(page <= 1)))

        # Page numbers — show up to 5 centered around current
        if max_page <= 7:
            pages = range(1, max_page + 1)
        else:
            if page <= 3:
                pages = list(range(1, 6)) + ["...", max_page]
            elif page >= max_page - 2:
                pages = [1, "..."] + list(range(max_page - 4, max_page + 1))
            else:
                pages = [1, "..."] + list(range(page - 1, page + 2)) + ["...", max_page]

        for p in pages:
            if p == "...":
                buttons.append(ui.tags.span("\u2026", class_="insight-pag-ellipsis"))
            else:
                buttons.append(_page_btn(str(p), p, active=(p == page)))

        # Next
        buttons.append(_page_btn("\u203A", page + 1, disabled=(page >= max_page)))

        return ui.tags.div(*buttons, class_="insight-pag-btns")


def _pct_change(curr, prev):
    """Format percentage change."""
    if not prev or prev == 0:
        return "N/A"
    pct = (curr - prev) / abs(prev) * 100
    return f"{pct:+.1f}%"


def _build_yoy_comparison_table(df_c, df_p, group_col: str, label_col: str) -> "ui.HTML":
    """
    Build a YoY table with interleaved metric + Δ% columns.
    Columns: Impressions, Clicks, CTR, Direct Interaction, View-through Interaction,
             In-Platform Leads, Total Interactions, Interaction Rate.
    """
    raw_metrics = [
        "impressions", "clicks", "direct_conversions",
        "view_through_conversions", "in_platform_leads", "total_interactions",
    ]
    col_labels = [
        "Interactions", "Clicks", "CTR",
        "Direct Key Interaction", "View-Through Int.", "In-Platform Leads",
        "Total Interactions", "Interaction Rate",
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
            "Interactions":        (_fmt_int(r["impressions"]),         _pct_change(r["impressions"], p.get("impressions", 0)) if p else "N/A"),
            "Clicks":              (_fmt_int(r["clicks"]),              _pct_change(r["clicks"], p.get("clicks", 0)) if p else "N/A"),
            "CTR":                 (_fmt_pct(ctr_curr * 100 if ctr_curr is not None else None),
                                    _pct_change(ctr_curr, ctr_prev) if (ctr_curr is not None and ctr_prev is not None) else "N/A"),
            "Direct Key Interaction":   (_fmt_int(r["direct_conversions"]),  _pct_change(r["direct_conversions"], p.get("direct_conversions", 0)) if p else "N/A"),
            "View-Through Int.":  (_fmt_int(r["view_through_conversions"]), _pct_change(r["view_through_conversions"], p.get("view_through_conversions", 0)) if p else "N/A"),
            "In-Platform Leads":   (_fmt_int(r["in_platform_leads"]),   _pct_change(r["in_platform_leads"], p.get("in_platform_leads", 0)) if p else "N/A"),
            "Total Interactions":  (_fmt_int(r["total_interactions"]),  _pct_change(r["total_interactions"], p.get("total_interactions", 0)) if p else "N/A"),
            "Interaction Rate":    (_fmt_pct(conv_rate_curr * 100 if conv_rate_curr is not None else None),
                                    _pct_change(conv_rate_curr, conv_rate_prev) if (conv_rate_curr is not None and conv_rate_prev is not None) else "N/A"),
        }
        rows.append({"label": grp, "metrics": metrics_data})

    return _yoy_delta_table(rows, label_col=label_col, metric_cols=col_labels)


def _df_to_html(df, title):
    """Convert a DataFrame to a styled HTML section for creative tables."""
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

    headers = "".join(
        f'<th style="{th_first_style if ci == 0 else th_style}">{col}</th>'
        for ci, col in enumerate(df.columns)
    )
    rows_html = ""
    for _, row in df.iterrows():
        cells = "".join(
            f'<td style="{td_first if ci == 0 else td_base}">{v}</td>'
            for ci, v in enumerate(row)
        )
        rows_html += f"<tr>{cells}</tr>"

    title_html = (
        f'<div style="font-family:Manrope,sans-serif;font-size:14px;font-weight:600;'
        f'color:#021326;margin:0 0 12px 0;">{title}</div>'
    )
    return ui.HTML(
        f'<div class="carnegie-table-card" style="margin-bottom:20px;">'
        f'{title_html}'
        f'<div style="overflow-x:auto;">'
        f'<table class="sortable-table paginated-table" style="width:100%;border-collapse:collapse;">'
        f"<thead><tr>{headers}</tr></thead>"
        f"<tbody>{rows_html}</tbody>"
        f"</table></div></div>"
    )
