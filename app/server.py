"""Carnegie ROI Dashboard — Reactive server logic."""

from datetime import date
from shiny import render, reactive, ui, req
import plotly.graph_objects as go
import pandas as pd

from data_loader import Q6, Q2, Q3, GOALS, ACAD_ORDER, MONTH_LABELS
from metrics import (
    FUNNEL_COLS, COST_PER_DEFS,
    compute_funnel_kpis, compute_yoy_change,
    compute_cost_summary, compute_campaign_breakdown,
    compute_geo_detail,
)
from formatters import fmt_number, fmt_pct, fmt_currency, fmt_yoy
from digital_server import digital_server, _plain_table, _heatmap_table

# ── Carnegie brand colors for Plotly ─────────────────────────

CARNEGIE_NAVY = "#021326"

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
CARNEGIE_GRAY_TEXT = "#6b7280"
CARNEGIE_GRAY_BORDER = "#e5e1dc"
CARNEGIE_BG = "#f8f4f0"
CARNEGIE_WHITE = "#ffffff"
CARNEGIE_GREEN = "#2d8a4e"
CARNEGIE_AMBER = "#c8962d"

MONTH_ORDER = ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
               "Jan", "Feb", "Mar", "Apr", "May", "Jun"]

# ── Primary funnel stages (6) ───────────────────────────────
PRIMARY_KEYS = [
    "total_inquiries", "total_app_starts", "total_app_submits",
    "total_admits", "total_deposits", "total_net_deposits",
]

PRIMARY_LABELS = {
    "total_inquiries": "Inquiries",
    "total_app_starts": "App Starts",
    "total_app_submits": "App Submits",
    "total_admits": "Admits",
    "total_deposits": "Deposits",
    "total_net_deposits": "Net Deposits",
}


def _plotly_html(fig, no_toolbar=True):
    """Convert plotly figure to HTML widget. Plotly JS is loaded once in the page <head>."""
    config = {"displayModeBar": False} if no_toolbar else {}
    return ui.HTML(fig.to_html(full_html=False, include_plotlyjs=False, config=config))


def _base_chart_layout(height=360):
    """Standard Carnegie chart layout."""
    return dict(
        font=dict(family="Manrope, sans-serif", color=CARNEGIE_NAVY, size=10.5),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=48, r=16, t=8, b=40),
        height=height,
        xaxis=dict(
            tickfont=dict(family="Manrope, sans-serif", size=10.5, color="#9B9893"),
            showgrid=False, title="",
        ),
        yaxis=dict(
            tickfont=dict(family="Manrope, sans-serif", size=10.5, color="#9B9893"),
            gridcolor="#F0EEEA", gridwidth=0.8,
            showline=False, nticks=5, title="",
        ),
        legend=dict(
            orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5,
            font=dict(family="Manrope, sans-serif", size=10.5),
        ),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor=CARNEGIE_WHITE, bordercolor=CARNEGIE_GRAY_BORDER,
            font=dict(family="Inter, sans-serif", size=13, color=CARNEGIE_NAVY),
        ),
    )


def server_logic(input, output, session):

    # ══════════════════════════════════════════════════════════
    # SHARED REACTIVE DATA
    # ══════════════════════════════════════════════════════════

    def _apply_global_filters(df):
        """Apply sidebar global filters to a Q6 DataFrame."""
        df = df[df["institution_name"] == input.institution()]
        df = df[df["term_semester"] == input.term_semester()]
        st = input.student_type()
        if isinstance(st, (list, tuple)):
            if "All" not in st and len(st) > 0:
                df = df[df["student_type"].isin(st)]
        elif st != "All":
            df = df[df["student_type"] == st]
        if not input.is_international():
            df = df[df["is_international"] == False]  # noqa: E712
        return df

    @reactive.calc
    def filtered_main():
        """Q6 filtered by global filters + current term_year."""
        df = _apply_global_filters(Q6.copy())
        return df[df["term_year"] == int(input.term_year())]

    @reactive.calc
    def prior_main():
        """Q6 filtered by global filters + prior term_year."""
        df = _apply_global_filters(Q6.copy())
        return df[df["term_year"] == int(input.term_year()) - 1]

    @reactive.calc
    def trending_main():
        """Q6 filtered by global filters — ALL term_years (for trending)."""
        return _apply_global_filters(Q6.copy())

    @reactive.calc
    def filtered_deep_dive():
        """Q6 current year + page-specific Lead Source and Program Level filters."""
        df = filtered_main()
        try:
            src = input.source_filter()
            if src and len(src) > 0:
                df = df[df["origin_source_first"].isin(src)]
        except Exception:
            pass
        try:
            pl = input.program_level_adv()
            if pl and len(pl) > 0:
                df = df[df["program_level"].isin(pl)]
        except Exception:
            pass
        return df

    @reactive.calc
    def prior_deep_dive():
        """Q6 prior year + page-specific Lead Source filter."""
        df = prior_main()
        try:
            src = input.source_filter()
            if src and len(src) > 0:
                df = df[df["origin_source_first"].isin(src)]
        except Exception:
            pass
        try:
            pl = input.program_level_adv()
            if pl and len(pl) > 0:
                df = df[df["program_level"].isin(pl)]
        except Exception:
            pass
        return df

    @reactive.calc
    def filtered_q2():
        """Q2 for cost metrics only (no page-specific source filter)."""
        df = Q2.copy()
        df = df[df["institution_name"] == input.institution()]
        df = df[df["term_year"] == int(input.term_year())]
        df = df[df["term_semester"] == input.term_semester()]
        return df

    @reactive.calc
    def prior_q2():
        df = Q2.copy()
        df = df[df["institution_name"] == input.institution()]
        df = df[df["term_year"] == int(input.term_year()) - 1]
        df = df[df["term_semester"] == input.term_semester()]
        return df

    @reactive.calc
    def filtered_q3():
        """Q3 for city-level detail only."""
        df = Q3.copy()
        df = df[df["institution_name"] == input.institution()]
        df = df[df["term_year"] == int(input.term_year())]
        df = df[df["term_semester"] == input.term_semester()]
        return df

    # ── Update filter choices ─────────────────────────────────

    @reactive.effect
    def _update_source_choices():
        """Populate Lead Source filter from Q6 origin_source_first, sorted by inquiry volume."""
        df = filtered_main()
        if df.empty:
            ui.update_selectize("source_filter", choices=[], selected=[])
            return
        src_totals = df.groupby("origin_source_first")["total_inquiries"].sum().sort_values(ascending=False)
        sources = [s for s in src_totals.index.tolist() if s and str(s).strip() and s != "Unknown"]
        ui.update_selectize("source_filter", choices=sources, selected=[])

    @reactive.effect
    def _update_program_level_choices():
        """Populate Program Level advanced filter from Q6."""
        df = filtered_main()
        levels = sorted([l for l in df["program_level"].dropna().unique().tolist() if l and str(l).strip()])
        ui.update_selectize("program_level_adv", choices=levels, selected=[])

    # ══════════════════════════════════════════════════════════
    # KPI CALCULATIONS (from Q6)
    # ══════════════════════════════════════════════════════════

    def _aggregate_kpis(df):
        """Sum funnel columns from a Q6 DataFrame into a KPI dict."""
        if df.empty:
            result = {col: 0 for col in PRIMARY_KEYS}
            result["total_enrolled"] = 0
            result["admitted_rate"] = None
            result["yield_rate"] = None
            return result
        sums = {col: int(df[col].sum()) for col in PRIMARY_KEYS + ["total_enrolled"]}
        submits = sums["total_app_submits"]
        admits = sums["total_admits"]
        sums["admitted_rate"] = (admits / submits * 100) if submits > 0 else None
        sums["yield_rate"] = (sums["total_net_deposits"] / admits * 100) if admits > 0 else None
        return sums

    @reactive.calc
    def current_kpis():
        return _aggregate_kpis(filtered_main())

    @reactive.calc
    def prior_kpis():
        return _aggregate_kpis(prior_main())

    @reactive.calc
    def yoy_changes():
        return compute_yoy_change(current_kpis(), prior_kpis())

    # ══════════════════════════════════════════════════════════
    # PAGE 1: ROI OVERVIEW
    # ══════════════════════════════════════════════════════════

    @render.ui
    def page_subtitle():
        return ui.tags.span(f"\u2014 {input.institution()}", class_="page-subtitle")

    @render.ui
    def period_badge():
        return ui.tags.span(
            f"{input.term_semester()} {input.term_year()} \u00b7 as of {date.today().strftime('%b %d, %Y')}",
            class_="period-badge",
        )

    # --- Primary KPI value outputs ---

    @render.text
    def kpi_total_inquiries():
        return fmt_number(current_kpis()["total_inquiries"])

    @render.text
    def kpi_total_app_starts():
        return fmt_number(current_kpis()["total_app_starts"])

    @render.text
    def kpi_total_app_submits():
        return fmt_number(current_kpis()["total_app_submits"])

    @render.text
    def kpi_total_admits():
        return fmt_number(current_kpis()["total_admits"])

    @render.text
    def kpi_total_deposits():
        return fmt_number(current_kpis()["total_deposits"])

    @render.text
    def kpi_total_net_deposits():
        return fmt_number(current_kpis()["total_net_deposits"])

    # --- Secondary metric outputs ---

    @render.text
    def kpi_admitted_rate():
        return fmt_pct(current_kpis()["admitted_rate"])

    @render.text
    def kpi_yield_rate():
        return fmt_pct(current_kpis()["yield_rate"])

    @render.text
    def kpi_total_enrolled():
        return fmt_number(current_kpis().get("total_enrolled", 0))

    @render.text
    def kpi_cost_per_net_deposit():
        total_spend = filtered_q2()["total_cost"].sum()
        net_deps = current_kpis().get("total_net_deposits", 0)
        if net_deps > 0 and total_spend > 0:
            return fmt_currency(total_spend / net_deps)
        return "\u2014"

    # --- YoY badge outputs ---

    def _yoy_badge(key: str):
        changes = yoy_changes()
        text, sentiment = fmt_yoy(changes.get(key))
        badge_class = f"kpi-badge kpi-badge--{sentiment}"
        return ui.tags.span(text, class_=badge_class)

    def _yoy_badge_pp(key: str):
        """YoY badge for percentage-point metrics (absolute diff, not relative %)."""
        curr = current_kpis().get(key)
        prior = prior_kpis().get(key)
        if curr is None or prior is None:
            return ui.tags.span("N/A", class_="kpi-badge kpi-badge--na")
        diff = round(curr - prior)
        if diff > 0:
            text, sentiment = f"\u25b2 {diff}pp vs. PY", "positive"
        elif diff < 0:
            text, sentiment = f"\u25bc {abs(diff)}pp vs. PY", "negative"
        else:
            text, sentiment = "0pp vs. PY", "neutral"
        return ui.tags.span(text, class_=f"kpi-badge kpi-badge--{sentiment}")

    @render.ui
    def yoy_total_inquiries():
        return _yoy_badge("total_inquiries")

    @render.ui
    def yoy_total_app_starts():
        return _yoy_badge("total_app_starts")

    @render.ui
    def yoy_total_app_submits():
        return _yoy_badge("total_app_submits")

    @render.ui
    def yoy_total_admits():
        return _yoy_badge("total_admits")

    @render.ui
    def yoy_total_deposits():
        return _yoy_badge("total_deposits")

    @render.ui
    def yoy_total_net_deposits():
        return _yoy_badge("total_net_deposits")

    @render.ui
    def yoy_admitted_rate():
        return _yoy_badge_pp("admitted_rate")

    @render.ui
    def yoy_yield_rate():
        return _yoy_badge_pp("yield_rate")

    @render.ui
    def yoy_total_enrolled():
        return _yoy_badge("total_enrolled")

    def _cost_yoy_badge(denominator_key):
        """YoY badge for a cost metric — inverted sentiment (cost down = green)."""
        curr_spend = filtered_q2()["total_cost"].sum()
        curr_denom = current_kpis().get(denominator_key, 0)
        curr_val = (curr_spend / curr_denom) if curr_denom > 0 and curr_spend > 0 else None

        prior_spend = prior_q2()["total_cost"].sum()
        prior_denom = prior_kpis().get(denominator_key, 0)
        prior_val = (prior_spend / prior_denom) if prior_denom > 0 and prior_spend > 0 else None

        if curr_val is None or prior_val is None or prior_val == 0:
            return ui.tags.span("N/A", class_="kpi-badge kpi-badge--na")
        pct = ((curr_val - prior_val) / abs(prior_val)) * 100
        text, _ = fmt_yoy(pct)
        sentiment = "positive" if pct < 0 else "negative" if pct > 0 else "neutral"
        return ui.tags.span(text, class_=f"kpi-badge kpi-badge--{sentiment}")

    @render.ui
    def yoy_cost_per_net_deposit():
        return _cost_yoy_badge("total_net_deposits")

    @render.ui
    def cost_detail_panel():
        """All cost metrics in a single collapsible row."""
        _costs = [
            ("Cost/Net Deposit", "total_net_deposits"),
            ("Cost/Inquiry",     "total_inquiries"),
            ("Cost/App Start",   "total_app_starts"),
            ("Cost/App Submit",  "total_app_submits"),
            ("Cost/Admit",       "total_admits"),
            ("Cost/Deposit",     "total_deposits"),
        ]
        total_spend = filtered_q2()["total_cost"].sum()
        prior_spend = prior_q2()["total_cost"].sum()
        kpis = current_kpis()
        prior = prior_kpis()

        badges = []
        for label, denom_key in _costs:
            denom = kpis.get(denom_key, 0)
            curr_val = total_spend / denom if denom > 0 and total_spend > 0 else None
            prior_denom = prior.get(denom_key, 0)
            prior_val = prior_spend / prior_denom if prior_denom > 0 and prior_spend > 0 else None

            value_str = fmt_currency(curr_val) if curr_val is not None else "\u2014"

            if curr_val is not None and prior_val is not None and prior_val != 0:
                pct = (curr_val - prior_val) / abs(prior_val) * 100
                text, _ = fmt_yoy(pct)
                sentiment = "positive" if pct < 0 else "negative" if pct > 0 else "neutral"
                yoy_el = ui.tags.span(text, class_=f"kpi-badge kpi-badge--{sentiment}")
            else:
                yoy_el = ui.tags.span("N/A", class_="kpi-badge kpi-badge--na")

            badges.append(ui.tags.div(
                ui.tags.div(label, class_="secondary-label"),
                ui.tags.div(value_str, class_="secondary-value"),
                yoy_el,
                class_="secondary-badge",
            ))

        return ui.tags.div(
            *badges,
            id="cost-metrics-row",
            class_="secondary-row collapsible-row",
            title="Cost metrics reflect Carnegie campaign spend divided by total funnel volume.",
        )

    # --- Progress bars ---

    def _goal_color(pct: float) -> str:
        if pct >= 95:
            return "#B3C7BD"
        elif pct >= 80:
            return "#C48A1A"
        return "#560422"

    def _progress_bar(key: str):
        goal = GOALS.get(key)
        if not goal or goal <= 0:
            return ui.tags.div()
        actual = current_kpis().get(key, 0)
        pct = (actual / goal) * 100
        bar_width = min(pct, 100)
        color = _goal_color(pct)
        return ui.tags.div(
            ui.tags.div(style=f"width:{bar_width:.0f}%; height:4px; background:{color}; border-radius:2px;"),
            class_="progress-micro",
        )

    @render.ui
    def progress_total_inquiries():
        return _progress_bar("total_inquiries")

    @render.ui
    def progress_total_app_starts():
        return _progress_bar("total_app_starts")

    @render.ui
    def progress_total_app_submits():
        return _progress_bar("total_app_submits")

    @render.ui
    def progress_total_admits():
        return _progress_bar("total_admits")

    @render.ui
    def progress_total_deposits():
        return _progress_bar("total_deposits")

    @render.ui
    def progress_total_net_deposits():
        return _progress_bar("total_net_deposits")

    # --- Trending Performance Chart (Q6) ---

    @render.ui
    def trending_chart():
        req(input.trending_metric(), input.trending_mode())
        metric_col = f"total_{input.trending_metric()}"
        mode = input.trending_mode()
        df = trending_main()
        if df.empty:
            return ui.tags.div("No data available for the selected filters.", class_="empty-state")

        current_ty = int(input.term_year())
        prior_ty = current_ty - 1
        stage_label = PRIMARY_LABELS.get(metric_col, metric_col)
        fig = go.Figure()

        if mode == "yearly":
            # Aggregate total per term_year, show all available years as bars
            agg = df.groupby("term_year", as_index=False)[metric_col].sum()
            agg = agg.sort_values("term_year")
            if agg.empty:
                return ui.tags.div("No data available.", class_="empty-state")
            x_labels = [str(y) for y in agg["term_year"]]
            values = agg[metric_col].tolist()
            colors = [
                "#EA332D" if y == current_ty else "#C99D44" if y == prior_ty else CHART_COLORS[1]
                for y in agg["term_year"]
            ]
            # Value labels inside bars (near top)
            bar_text = [f"{v:,.0f}" for v in values]
            fig.add_trace(go.Bar(
                x=x_labels, y=values,
                name=stage_label,
                marker_color=colors,
                text=bar_text,
                textposition="inside",
                insidetextanchor="end",
                textfont=dict(family="Manrope, sans-serif", size=13, color="#ffffff"),
                hovertemplate=f"<b>%{{x}}</b><br>{stage_label}: %{{y:,.0f}}<extra></extra>",
            ))
            # YoY % annotations + connector shapes between each pair of bars
            annotations = []
            shapes = []
            y_max = max(values)
            label_y = y_max * 1.10  # annotation label height
            line_y = y_max * 1.04   # horizontal connector height
            for i in range(1, len(values)):
                prev = values[i - 1]
                curr_v = values[i]
                if prev and prev != 0:
                    pct = (curr_v - prev) / prev * 100
                    arrow = "▲" if pct >= 0 else "▼"
                    color = "#132B23" if pct >= 0 else "#560422"
                    # Label centered between the two bars
                    annotations.append(dict(
                        x=i - 0.5, y=label_y,
                        xref="x", yref="y",
                        text=f"{arrow} {abs(pct):.1f}%",
                        showarrow=False,
                        font=dict(family="Manrope, sans-serif", size=13, color=color),
                        xanchor="center", yanchor="bottom",
                    ))
                    line_color = "#9B9893"
                    lw = 1
                    # Left vertical leg: top of left bar → connector height
                    shapes.append(dict(
                        type="line", xref="x", yref="y",
                        x0=i - 1, y0=prev, x1=i - 1, y1=line_y,
                        line=dict(color=line_color, width=lw, dash="dot"),
                    ))
                    # Right vertical leg: top of right bar → connector height
                    shapes.append(dict(
                        type="line", xref="x", yref="y",
                        x0=i, y0=curr_v, x1=i, y1=line_y,
                        line=dict(color=line_color, width=lw, dash="dot"),
                    ))
                    # Horizontal connector between the two legs
                    shapes.append(dict(
                        type="line", xref="x", yref="y",
                        x0=i - 1, y0=line_y, x1=i, y1=line_y,
                        line=dict(color=line_color, width=lw, dash="dot"),
                    ))
            layout = _base_chart_layout(360)
            layout["xaxis"] = dict(
                tickfont=dict(family="Manrope, sans-serif", size=11, color="#9B9893"),
                showgrid=False, title="",
            )
            layout["bargap"] = 0.4
            layout["annotations"] = annotations
            layout["shapes"] = shapes
            layout["yaxis"] = dict(
                tickfont=dict(family="Manrope, sans-serif", size=10.5, color="#9B9893"),
                gridcolor="#F0EEEA", gridwidth=0.8,
                showline=False, nticks=5, title="",
                range=[0, y_max * 1.22],
            )
        else:
            # Monthly mode — cumulative by academic month, current vs prior year
            def _monthly_series(term_year, cap_current_month=False):
                sub = df[df["term_year"] == term_year]
                if sub.empty:
                    return pd.DataFrame()
                agg = sub.groupby(["acad_pos", "month_label"], as_index=False)[metric_col].sum()
                agg = agg.sort_values("acad_pos")
                if cap_current_month:
                    current_acad_pos = ACAD_ORDER.get(date.today().month, 12)
                    agg = agg[agg["acad_pos"] <= current_acad_pos]
                return agg

            curr = _monthly_series(current_ty, cap_current_month=True)
            prior = _monthly_series(prior_ty)

            if curr.empty and prior.empty:
                return ui.tags.div("No data available.", class_="empty-state")

            # Always cumulative in monthly mode
            if not curr.empty:
                curr["cumulative"] = curr[metric_col].cumsum()
            if not prior.empty:
                prior["cumulative"] = prior[metric_col].cumsum()
            y_col = "cumulative"

            prior_label = f"{prior_ty - 1}-{str(prior_ty)[-2:]}"
            curr_label = f"{current_ty - 1}-{str(current_ty)[-2:]}"

            if not curr.empty:
                fig.add_trace(go.Scatter(
                    x=curr["month_label"], y=curr[y_col],
                    mode="lines+markers",
                    name=curr_label,
                    line=dict(color="#EA332D", width=2.5),
                    marker=dict(color="#EA332D", size=7),
                    hovertemplate=f"<b>%{{x}} {curr_label}</b><br>{stage_label}: %{{y:,.0f}}<extra></extra>",
                ))

            if not prior.empty:
                fig.add_trace(go.Scatter(
                    x=prior["month_label"], y=prior[y_col],
                    mode="lines+markers",
                    name=prior_label,
                    line=dict(color="#C99D44", width=1.8, dash="dash"),
                    marker=dict(color="#C99D44", size=5),
                    hovertemplate=f"<b>%{{x}} {prior_label}</b><br>{stage_label}: %{{y:,.0f}}<extra></extra>",
                ))

                if len(curr) >= 3:
                    curr["trend"] = curr[y_col].rolling(window=3).mean()
                    trend_df = curr.dropna(subset=["trend"])
                    if not trend_df.empty:
                        fig.add_trace(go.Scatter(
                            x=trend_df["month_label"], y=trend_df["trend"],
                            mode="lines", name="3-mo trend",
                            line=dict(color="rgba(2,19,38,0.4)", width=1.5, dash="dot"),
                            hovertemplate=f"<b>%{{x}} {curr_label}</b><br>3-mo avg: %{{y:,.0f}}<extra></extra>",
                        ))

            layout = _base_chart_layout(360)
            layout["xaxis"] = dict(
                categoryorder="array", categoryarray=MONTH_ORDER,
                tickfont=dict(family="Manrope, sans-serif", size=10.5, color="#9B9893"),
                showgrid=False, title="",
            )

        fig.update_layout(**layout)
        return _plotly_html(fig)

    # --- Funnel at a Glance ---

    @render.ui
    def funnel_at_glance():
        kpis = current_kpis()
        prior = prior_kpis()

        stages = [
            ("Inquiries",    "total_inquiries"),
            ("App Starts",   "total_app_starts"),
            ("App Submits",  "total_app_submits"),
            ("Admits",       "total_admits"),
            ("Deposits",     "total_deposits"),
            ("Net Deposits", "total_net_deposits"),
        ]

        if all(kpis.get(k, 0) == 0 for _, k in stages):
            return ui.tags.div("No data.", class_="empty-state")

        n = len(stages)
        vals = [kpis.get(k, 0) for _, k in stages]
        max_val = max(v for v in vals if v > 0) or 1

        # SVG layout
        # Left area: funnel trapezoids
        # Right margin: conversion rate pills (outside the funnel)
        FUNNEL_W = 105      # width of funnel area
        RIGHT_MARGIN = 48   # space for pills on right
        W = FUNNEL_W + RIGHT_MARGIN
        STEP_H = 18
        GAP_H = 0           # no gap — continuous funnel, pills float on border
        TOTAL_H = n * STEP_H + 2
        MIN_W_PCT = 0.30
        MAX_W_PCT = 1.0

        colors = [
            "#F0908A", "#E86E67", "#E04D46",
            "#CE3830", "#B82D27", "#9E231E",
        ]

        # Pre-compute widths
        ratios = [(v / max_val) ** 0.55 for v in vals]
        widths = [MIN_W_PCT + r * (MAX_W_PCT - MIN_W_PCT) for r in ratios]

        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {TOTAL_H}" '
            f'width="100%" style="display:block;margin:0 auto;max-width:{int(W*2.6)}px;">'
        ]
        svg_parts.append(
            '<defs>'
            '<filter id="fgs" x="-5%" y="-5%" width="115%" height="120%">'
            '<feDropShadow dx="0" dy="1" stdDeviation="2" flood-color="#00000020"/>'
            '</filter>'
            '</defs>'
        )

        for i, (label, key) in enumerate(stages):
            val = vals[i]
            top_w = widths[i] * FUNNEL_W
            bot_w = widths[i + 1] * FUNNEL_W if i < n - 1 else top_w * 0.85
            top_x = (FUNNEL_W - top_w) / 2
            bot_x = (FUNNEL_W - bot_w) / 2
            y = i * STEP_H

            pts = f"{top_x:.1f},{y} {top_x+top_w:.1f},{y} {bot_x+bot_w:.1f},{y+STEP_H} {bot_x:.1f},{y+STEP_H}"

            svg_parts.append(
                f'<polygon points="{pts}" fill="{colors[i]}" filter="url(#fgs)"/>'
            )

            # Label: small uppercase, top portion of block
            label_y = y + STEP_H * 0.36
            val_y   = y + STEP_H * 0.72
            cx_block = FUNNEL_W / 2

            svg_parts.append(
                f'<text x="{cx_block:.1f}" y="{label_y:.1f}" '
                f'dominant-baseline="middle" text-anchor="middle" '
                f'font-family="Manrope,sans-serif" font-size="4.5" font-weight="600" '
                f'fill="rgba(255,255,255,0.80)" letter-spacing="0.06em">'
                f'{label.upper()}</text>'
            )
            svg_parts.append(
                f'<text x="{cx_block:.1f}" y="{val_y:.1f}" '
                f'dominant-baseline="middle" text-anchor="middle" '
                f'font-family="Manrope,sans-serif" font-size="7" font-weight="700" '
                f'fill="#ffffff">'
                f'{fmt_number(val)}</text>'
            )

            # Melt Rate inline — to the right of last block
            if i == n - 1:
                deposits = kpis.get("total_deposits", 0)
                net_deposits = kpis.get("total_net_deposits", 0)
                if deposits > 0:
                    melt = (1 - net_deposits / deposits) * 100
                    melt_color = "#132B23" if melt < 3 else "#C99D44" if melt <= 5 else "#560422"
                    pill_x = FUNNEL_W + 6
                    pill_y = y + STEP_H / 2
                    svg_parts.append(
                        f'<text x="{pill_x}" y="{pill_y - 5:.1f}" '
                        f'dominant-baseline="middle" text-anchor="start" '
                        f'font-family="Manrope,sans-serif" font-size="5" font-weight="600" '
                        f'fill="#9B9893">Melt</text>'
                    )
                    svg_parts.append(
                        f'<text x="{pill_x}" y="{pill_y + 4:.1f}" '
                        f'dominant-baseline="middle" text-anchor="start" '
                        f'font-family="Manrope,sans-serif" font-size="6.5" font-weight="700" '
                        f'fill="{melt_color}">{melt:.1f}%</text>'
                    )

            # Conversion rate pill — on right edge, centred on the border between blocks
            if i < n - 1:
                curr_rate = (vals[i + 1] / val * 100) if val > 0 else None
                prior_val = prior.get(key, 0)
                prior_rate = (prior.get(stages[i + 1][1], 0) / prior_val * 100) if prior_val > 0 else None

                border_y = y + STEP_H  # exact border between block i and i+1
                # Right edge of block i at its bottom
                right_edge = bot_x + bot_w

                if curr_rate is not None:
                    if prior_rate is None:
                        rc = "#9B9893"
                    elif curr_rate >= prior_rate:
                        rc = "#132B23"
                    elif curr_rate >= prior_rate - 5:
                        rc = "#C99D44"
                    else:
                        rc = "#560422"

                    rate_text = f"{curr_rate:.1f}%"
                    pill_w = 28
                    pill_h = 9
                    px = right_edge + 4
                    py = border_y

                    svg_parts.append(
                        f'<rect x="{px:.1f}" y="{py - pill_h/2:.1f}" '
                        f'width="{pill_w}" height="{pill_h}" rx="4" '
                        f'fill="white" stroke="{rc}" stroke-width="0.8"/>'
                    )
                    svg_parts.append(
                        f'<text x="{px + pill_w/2:.1f}" y="{py:.1f}" '
                        f'dominant-baseline="middle" text-anchor="middle" '
                        f'font-family="Manrope,sans-serif" font-size="6" font-weight="700" '
                        f'fill="{rc}">{rate_text}</text>'
                    )

        svg_parts.append('</svg>')
        return ui.tags.div(ui.HTML("".join(svg_parts)), class_="fg-panel")

    # --- Goal context text (shown below YoY badge on each KPI card) ---

    def _goal_text_ui(key: str):
        goal = GOALS.get(key)
        if not goal or goal <= 0:
            return ui.tags.div()
        actual = current_kpis().get(key, 0)
        pct = (actual / goal) * 100
        return ui.tags.div(
            f"Goal: {fmt_number(goal)} \u00b7 {pct:.0f}%",
            class_="goal-context-text",
        )

    @render.ui
    def goal_text_total_inquiries():
        return _goal_text_ui("total_inquiries")

    @render.ui
    def goal_text_total_app_starts():
        return _goal_text_ui("total_app_starts")

    @render.ui
    def goal_text_total_app_submits():
        return _goal_text_ui("total_app_submits")

    @render.ui
    def goal_text_total_admits():
        return _goal_text_ui("total_admits")

    @render.ui
    def goal_text_total_deposits():
        return _goal_text_ui("total_deposits")

    @render.ui
    def goal_text_total_net_deposits():
        return _goal_text_ui("total_net_deposits")

    # --- Melt Rate secondary badge ---

    @render.ui
    def melt_rate_secondary():
        deposits = current_kpis().get("total_deposits", 0)
        net_deposits = current_kpis().get("total_net_deposits", 0)
        prior_deps = prior_kpis().get("total_deposits", 0)
        prior_net = prior_kpis().get("total_net_deposits", 0)

        if deposits > 0:
            melt = (1 - net_deposits / deposits) * 100
            melt_cls = "fg-melt--good" if melt < 3 else "fg-melt--warn" if melt <= 5 else "fg-melt--bad"

            # vs PY delta — for melt rate, lower is better → invert sentiment
            if prior_deps > 0:
                prior_melt = (1 - prior_net / prior_deps) * 100
                diff = round(melt - prior_melt)
                # higher melt = worse → up arrow is negative sentiment
                if diff > 0:
                    yoy_text = f"\u25b2 {diff}pp vs. PY"
                    sentiment = "negative"
                elif diff < 0:
                    yoy_text = f"\u25bc {abs(diff)}pp vs. PY"
                    sentiment = "positive"
                else:
                    yoy_text = "0pp vs. PY"
                    sentiment = "neutral"
                yoy_el = ui.tags.span(yoy_text, class_=f"kpi-badge kpi-badge--{sentiment}")
            else:
                yoy_el = ui.tags.span("N/A", class_="kpi-badge kpi-badge--na")

            return ui.tags.div(
                ui.tags.div("Melt Rate", class_="secondary-label"),
                ui.tags.div(f"{melt:.1f}%", class_=f"secondary-value {melt_cls}"),
                yoy_el,
                title="Percentage of deposited students who withdrew before enrollment.",
                class_="secondary-badge",
            )
        return ui.tags.div(
            ui.tags.div("Melt Rate", class_="secondary-label"),
            ui.tags.div("—", class_="secondary-value"),
            class_="secondary-badge",
        )

    # ══════════════════════════════════════════════════════════
    # PAGE 2: FUNNEL DEEP DIVE
    # ══════════════════════════════════════════════════════════

    # --- Funnel Waterfall (uses Q6 KPIs) ---

    @render.ui
    def funnel_waterfall():
        curr = _aggregate_kpis(filtered_deep_dive())
        prior = _aggregate_kpis(prior_deep_dive())

        if all(curr.get(k, 0) == 0 for k in PRIMARY_KEYS):
            return ui.tags.div("No data available for the selected filters.", class_="empty-state")

        labels = [PRIMARY_LABELS[k] for k in PRIMARY_KEYS]
        curr_vals = [curr.get(k, 0) for k in PRIMARY_KEYS]
        prior_vals = [prior.get(k, 0) for k in PRIMARY_KEYS]

        curr_ty = int(input.term_year())
        prior_ty = curr_ty - 1
        curr_label = f"{curr_ty - 1}-{str(curr_ty)[-2:]}"
        prior_label = f"{prior_ty - 1}-{str(prior_ty)[-2:]}"

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=labels, y=curr_vals, name=curr_label,
            marker_color=CHART_COLORS[0],
            text=[f"{v:,}" for v in curr_vals], textposition="outside",
            textfont=dict(family="Manrope, sans-serif", size=11),
            hovertemplate="<b>%{x}</b><br>" + curr_label + ": %{y:,}<extra></extra>",
        ))
        fig.add_trace(go.Bar(
            x=labels, y=prior_vals, name=prior_label,
            marker_color=CHART_COLORS[1],
            text=[f"{v:,}" for v in prior_vals], textposition="outside",
            textfont=dict(family="Manrope, sans-serif", size=11),
            hovertemplate="<b>%{x}</b><br>" + prior_label + ": %{y:,}<extra></extra>",
            opacity=0.5,
        ))

        # YoY % annotations + bracket connectors above each bar group
        annotations = []
        shapes = []
        all_vals = curr_vals + prior_vals
        y_max = max(v for v in all_vals if v > 0) if any(v > 0 for v in all_vals) else 1
        # In grouped bar mode with 2 traces, bar centers are at x ± 0.2
        bar_half = 0.2
        for i, (cv, pv) in enumerate(zip(curr_vals, prior_vals)):
            if pv and pv != 0:
                pct = (cv - pv) / pv * 100
                arrow = "▲" if pct >= 0 else "▼"
                color = "#132B23" if pct >= 0 else "#560422"
                # Per-group heights: bracket sits just above the taller bar
                group_top = max(cv, pv)
                line_y  = group_top + y_max * 0.06
                label_y = group_top + y_max * 0.13
                annotations.append(dict(
                    x=i, y=label_y, xref="x", yref="y",
                    text=f"<b>{arrow} {abs(pct):.1f}%</b>",
                    showarrow=False,
                    font=dict(family="Manrope, sans-serif", size=12, color=color),
                    xanchor="center",
                ))
                line_color = "#9B9893"
                lw = 1
                # Left vertical leg (curr bar center → line_y)
                shapes.append(dict(
                    type="line", xref="x", yref="y",
                    x0=i - bar_half, y0=cv, x1=i - bar_half, y1=line_y,
                    line=dict(color=line_color, width=lw, dash="dot"),
                ))
                # Right vertical leg (prior bar center → line_y)
                shapes.append(dict(
                    type="line", xref="x", yref="y",
                    x0=i + bar_half, y0=pv, x1=i + bar_half, y1=line_y,
                    line=dict(color=line_color, width=lw, dash="dot"),
                ))
                # Horizontal connector
                shapes.append(dict(
                    type="line", xref="x", yref="y",
                    x0=i - bar_half, y0=line_y, x1=i + bar_half, y1=line_y,
                    line=dict(color=line_color, width=lw, dash="dot"),
                ))

        # "Same period" note — bottom-left, below the legend
        current_month_name = date.today().strftime("%b")
        note_text = (
            f"Same period compared: Jul – {current_month_name} &nbsp;|&nbsp; "
            f"{curr_label} vs {prior_label}"
        )
        annotations.append(dict(
            x=0, y=-0.18, xref="paper", yref="paper",
            text=note_text,
            showarrow=False,
            font=dict(family="Manrope, sans-serif", size=10, color=CARNEGIE_GRAY_TEXT),
            xanchor="left",
        ))

        layout = _base_chart_layout(420)
        layout["barmode"] = "group"
        layout["bargap"] = 0.35
        layout["annotations"] = annotations
        layout["shapes"] = shapes
        layout["yaxis"] = dict(
            tickfont=dict(family="Manrope, sans-serif", size=10.5, color="#9B9893"),
            gridcolor="#F0EEEA", gridwidth=0.8,
            showline=False, nticks=5, title="",
            range=[0, y_max * 1.42],
        )
        layout["margin"] = dict(l=48, r=16, t=8, b=52)
        fig.update_layout(**layout)
        return _plotly_html(fig)

    # --- Source Performance Table (Q2 — campaign attribution) ---

    @render.ui
    def source_table():
        """Source performance table — same columns as program detail, grouped by lead source."""
        df_curr = filtered_deep_dive()
        if df_curr.empty:
            return ui.tags.div("No data available.", class_="empty-state")

        agg_cols = ["total_inquiries", "total_app_starts", "total_app_submits",
                    "total_enrolled", "total_deposits", "total_net_deposits"]
        curr = df_curr.groupby("origin_source_first", as_index=False)[agg_cols].sum()
        curr = curr.sort_values("total_inquiries", ascending=False)

        total_inq    = curr["total_inquiries"].sum()
        total_starts = curr["total_app_starts"].sum()
        total_submits = curr["total_app_submits"].sum()
        total_enrolled = curr["total_enrolled"].sum()

        curr["% Inquiries"] = curr["total_inquiries"].apply(
            lambda v: f"{v / total_inq * 100:.1f}%" if total_inq > 0 else "—"
        )
        curr["% App Starts"] = curr["total_app_starts"].apply(
            lambda v: f"{v / total_starts * 100:.1f}%" if total_starts > 0 else "—"
        )
        curr["Start Rate"] = curr.apply(
            lambda r: f"{r['total_app_starts'] / r['total_inquiries'] * 100:.1f}%"
            if r["total_inquiries"] > 0 else "—", axis=1
        )
        curr["% App Submits"] = curr["total_app_submits"].apply(
            lambda v: f"{v / total_submits * 100:.1f}%" if total_submits > 0 else "—"
        )
        curr["Submit Rate"] = curr.apply(
            lambda r: f"{r['total_app_submits'] / r['total_app_starts'] * 100:.1f}%"
            if r["total_app_starts"] > 0 else "—", axis=1
        )
        curr["% Enrolled"] = curr["total_enrolled"].apply(
            lambda v: f"{v / total_enrolled * 100:.1f}%" if total_enrolled > 0 else "—"
        )
        curr["Inq→Enroll Rate"] = curr.apply(
            lambda r: f"{r['total_enrolled'] / r['total_inquiries'] * 100:.1f}%"
            if r["total_inquiries"] > 0 else "—", axis=1
        )

        display = curr.rename(columns={
            "origin_source_first": "Lead Source",
            "total_inquiries":     "Inquiries",
            "total_app_starts":    "App Starts",
            "total_app_submits":   "App Submits",
            "total_enrolled":      "Enrolled",
            "total_deposits":      "Deposits",
            "total_net_deposits":  "Net Deposits",
        })
        cols = [
            "Lead Source",
            "Inquiries", "% Inquiries",
            "App Starts", "% App Starts", "Start Rate",
            "App Submits", "% App Submits", "Submit Rate",
            "Enrolled", "% Enrolled", "Inq→Enroll Rate",
            "Deposits", "Net Deposits",
        ]
        return _plain_table(display[cols])

    # --- Origin Source Trend Chart (Q6 — first-touch, monthly) ---

    @render.ui
    def source_trend_chart():
        try:
            metric_col = input.source_trend_metric()
        except Exception:
            metric_col = "total_inquiries"
        df = filtered_deep_dive()

        if df.empty:
            return ui.tags.div("No data available.", class_="empty-state")

        # Aggregate by origin_source + month
        agg = df.groupby(
            ["origin_source_first", "acad_pos", "month_label"], as_index=False
        )[metric_col].sum()

        # Top 5 sources by total volume
        src_totals = agg.groupby("origin_source_first")[metric_col].sum().nlargest(5)
        top_sources = src_totals.index.tolist()

        if not top_sources:
            return ui.tags.div("No source data available.", class_="empty-state")

        source_colors = CHART_COLORS[:5]

        fig = go.Figure()
        for i, src in enumerate(top_sources):
            sdf = agg[agg["origin_source_first"] == src].sort_values("acad_pos")
            color = source_colors[i % len(source_colors)]
            dash = "solid" if i < 3 else "dash"
            fig.add_trace(go.Scatter(
                x=sdf["month_label"], y=sdf[metric_col],
                mode="lines+markers", name=src,
                line=dict(color=color, width=2.5 if i == 0 else 1.8, dash=dash),
                marker=dict(color=color, size=6 if i == 0 else 5),
                hovertemplate=f"<b>{src}</b><br>%{{x}}: %{{y:,}}<extra></extra>",
            ))

        layout = _base_chart_layout(320)
        layout["xaxis"] = dict(
            categoryorder="array", categoryarray=MONTH_ORDER,
            tickfont=dict(family="Manrope, sans-serif", size=10.5, color="#9B9893"),
            showgrid=False, title="",
        )
        layout["legend"] = dict(
            orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5,
            font=dict(family="Manrope, sans-serif", size=10.5),
        )
        fig.update_layout(**layout)
        return _plotly_html(fig)

    # --- Conversion Rates by Source (Q2) ---

    @render.ui
    def conversion_by_source_chart():
        """Conversion rates by origin_source_first from Q6."""
        df = filtered_deep_dive()
        if df.empty:
            return ui.tags.div("No data available.", class_="empty-state")

        funnel_cols = ["total_inquiries", "total_app_submits", "total_admits", "total_net_deposits"]
        src_agg = df.groupby("origin_source_first", as_index=False)[funnel_cols].sum()

        src_agg["admit_rate"] = src_agg.apply(
            lambda r: (r["total_admits"] / r["total_app_submits"] * 100)
            if r["total_app_submits"] > 0 else 0, axis=1
        )
        src_agg["yield_rate"] = src_agg.apply(
            lambda r: (r["total_net_deposits"] / r["total_admits"] * 100)
            if r["total_admits"] > 0 else 0, axis=1
        )

        bd = src_agg.nlargest(8, "total_inquiries")

        def _wrap_label(text, max_chars=20):
            if len(text) <= max_chars:
                return text
            words = text.split()
            lines, current = [], []
            for word in words:
                if len(" ".join(current + [word])) > max_chars and current:
                    lines.append(" ".join(current))
                    current = [word]
                else:
                    current.append(word)
            if current:
                lines.append(" ".join(current))
            return "<br>".join(lines)

        x_labels = [_wrap_label(s) for s in bd["origin_source_first"]]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=x_labels, y=bd["admit_rate"], name="Admit Rate",
            marker=dict(color="#021326", line=dict(width=0)),
            text=[f"{v:.0f}%" for v in bd["admit_rate"]],
            textposition="outside",
            textfont=dict(family="Manrope", size=10, color="#021326"),
            cliponaxis=False,
            hovertemplate="<b>%{x}</b><br>Admit Rate: %{y:.1f}%<extra></extra>",
        ))
        fig.add_trace(go.Bar(
            x=x_labels, y=bd["yield_rate"], name="Yield Rate",
            marker=dict(color=CHART_COLORS[1], line=dict(width=0)),
            text=[f"{v:.0f}%" for v in bd["yield_rate"]],
            textposition="outside",
            textfont=dict(family="Manrope", size=10, color=CHART_COLORS[1]),
            cliponaxis=False,
            hovertemplate="<b>%{x}</b><br>Yield Rate: %{y:.1f}%<extra></extra>",
        ))

        layout = _base_chart_layout(380)
        layout["margin"] = dict(l=48, r=16, t=24, b=80)
        layout["barmode"] = "group"
        layout["bargap"] = 0.3
        layout["bargroupgap"] = 0.1
        layout["xaxis"] = dict(
            title="",
            tickfont=dict(family="Manrope, sans-serif", size=10, color="#4A4843"),
            tickangle=0, showgrid=False,
        )
        layout["yaxis"] = dict(
            title="", ticksuffix="%", range=[0, 110], dtick=20,
            tickfont=dict(family="Manrope, sans-serif", size=10.5, color="#9B9893"),
            gridcolor="#F0EEEA", gridwidth=0.8, showline=False,
        )
        layout["legend"] = dict(
            orientation="h", yanchor="top", y=-0.25, xanchor="center", x=0.5,
            font=dict(family="Manrope, sans-serif", size=10.5),
        )
        fig.update_layout(**layout)
        return _plotly_html(fig)

    # ══════════════════════════════════════════════════════════
    # PAGE 3: GEOGRAPHY
    # ══════════════════════════════════════════════════════════

    # ══════════════════════════════════════════════════════════
    # PAGE 3 — PROGRAMS TAB
    # ══════════════════════════════════════════════════════════

    def _clean_program_name(name) -> str:
        """Title-case a program name, fixing common acronyms."""
        if not name or str(name).strip() == "":
            return "Not Specified"
        display = str(name).strip().title()
        for old, new in [
            ("Baed", "BAEd"), ("Bsba", "BSBA"), ("Bm ", "BM "),
            ("Ems ", "EMS "), ("Pre ", "Pre-"),
        ]:
            display = display.replace(old, new)
        return display

    @reactive.calc
    def filtered_programs():
        """Q6 filtered by global + program_name_filter, programs only."""
        df = filtered_main()
        df = df[df["program_name"].notna() & (df["program_name"].str.strip() != "")]
        df = df.copy()
        df["program_display"] = df["program_name"].apply(_clean_program_name)
        sel = input.program_name_filter()
        if sel and len(sel) > 0:
            df = df[df["program_display"].isin(sel)]
        return df

    @reactive.calc
    def prior_programs():
        """Q6 prior year filtered the same way as filtered_programs."""
        df = prior_main()
        df = df[df["program_name"].notna() & (df["program_name"].str.strip() != "")]
        df = df.copy()
        df["program_display"] = df["program_name"].apply(_clean_program_name)
        sel = input.program_name_filter()
        if sel and len(sel) > 0:
            df = df[df["program_display"].isin(sel)]
        return df

    @reactive.effect
    def _update_program_name_choices():
        df = filtered_main()
        df = df[df["program_name"].notna() & (df["program_name"].str.strip() != "")].copy()
        df["program_display"] = df["program_name"].apply(_clean_program_name)
        totals = (
            df.groupby("program_display")["total_inquiries"]
            .sum()
            .sort_values(ascending=False)
        )
        opts = [p for p in totals.index.tolist() if p != "Not Specified"]
        ui.update_selectize("program_name_filter", choices=opts, selected=[])

    @render.ui
    def program_trend_chart():
        try:
            metric_col = input.program_trend_metric()
        except Exception:
            metric_col = "total_inquiries"
        df = _apply_global_filters(Q6.copy())
        df = df[df["program_name"].notna() & (df["program_name"].str.strip() != "")].copy()
        df["program_display"] = df["program_name"].apply(_clean_program_name)

        # Apply program name filter if set
        sel = input.program_name_filter()
        if sel and len(sel) > 0:
            df = df[df["program_display"].isin(sel)]

        if df.empty:
            return ui.tags.div("No program data for the selected filters.", class_="empty-state")

        current_ty = int(input.term_year())
        metric_label = PRIMARY_LABELS.get(metric_col, metric_col)

        # Goal for this metric (institution-level flat target)
        goal_value = GOALS.get(metric_col)

        # Build monthly cumulative series for current year — grouped across all programs
        curr_df = df[df["term_year"] == current_ty].copy()
        if curr_df.empty:
            return ui.tags.div("No data for the selected term year.", class_="empty-state")

        curr_agg = (
            curr_df.groupby(["acad_pos", "month_label"], as_index=False)[metric_col].sum()
            .sort_values("acad_pos")
        )
        # Cap at current academic month
        current_acad_pos = ACAD_ORDER.get(date.today().month, 12)
        curr_agg = curr_agg[curr_agg["acad_pos"] <= current_acad_pos]
        curr_agg["cumulative"] = curr_agg[metric_col].cumsum()

        # Prior year for comparison
        prior_df = df[df["term_year"] == current_ty - 1].copy()
        prior_agg = None
        if not prior_df.empty:
            prior_agg = (
                prior_df.groupby(["acad_pos", "month_label"], as_index=False)[metric_col].sum()
                .sort_values("acad_pos")
            )
            prior_agg["cumulative"] = prior_agg[metric_col].cumsum()

        curr_label = f"{current_ty - 1}-{str(current_ty)[-2:]}"
        prior_label = f"{current_ty - 2}-{str(current_ty - 1)[-2:]}"

        fig = go.Figure()

        # Prior year line
        if prior_agg is not None and not prior_agg.empty:
            fig.add_trace(go.Scatter(
                x=prior_agg["month_label"], y=prior_agg["cumulative"],
                mode="lines+markers",
                name=prior_label,
                line=dict(color=CHART_COLORS[1], width=1.8, dash="dash"),
                marker=dict(color=CHART_COLORS[1], size=5),
                hovertemplate=f"<b>%{{x}} {prior_label}</b><br>{metric_label}: %{{y:,.0f}}<extra></extra>",
            ))

        # Current year line
        fig.add_trace(go.Scatter(
            x=curr_agg["month_label"], y=curr_agg["cumulative"],
            mode="lines+markers",
            name=curr_label,
            line=dict(color=CHART_COLORS[0], width=2.5),
            marker=dict(color=CHART_COLORS[0], size=7),
            hovertemplate=f"<b>%{{x}} {curr_label}</b><br>{metric_label}: %{{y:,.0f}}<extra></extra>",
        ))

        # Goal line — horizontal at goal_value across all 12 academic months
        if goal_value:
            fig.add_trace(go.Scatter(
                x=MONTH_ORDER,
                y=[goal_value] * len(MONTH_ORDER),
                mode="lines",
                name=f"{metric_label} Goal",
                line=dict(color=CARNEGIE_AMBER, width=2, dash="dot"),
                hovertemplate=f"Goal: {goal_value:,}<extra></extra>",
            ))

        layout = _base_chart_layout(360)
        layout["xaxis"] = dict(
            categoryorder="array", categoryarray=MONTH_ORDER,
            tickfont=dict(family="Manrope, sans-serif", size=10.5, color="#9B9893"),
            showgrid=False, title="",
        )
        fig.update_layout(**layout)
        return _plotly_html(fig)

    @render.ui
    def programs_bar_chart():
        df = filtered_programs()
        if df.empty:
            return ui.tags.div("No program data for the selected filters.", class_="empty-state")

        metric = input.program_metric()
        metric_label = PRIMARY_LABELS.get(metric, metric)

        # Current year aggregation
        curr = (
            df.groupby("program_display")[metric]
            .sum()
            .reset_index()
            .sort_values(metric, ascending=False)
            .head(15)
        )

        # Prior year for YoY colouring
        py_df = prior_programs()
        if not py_df.empty:
            py_agg = py_df.groupby("program_display")[metric].sum().reset_index()
            py_agg.columns = ["program_display", "metric_py"]
            curr = curr.merge(py_agg, on="program_display", how="left")
            curr["yoy"] = (
                (curr[metric] - curr["metric_py"]) / curr["metric_py"].replace(0, float("nan")) * 100
            )
        else:
            curr["yoy"] = float("nan")

        # Sort ascending for horizontal bar (plotly renders bottom-to-top)
        curr = curr.sort_values(metric, ascending=True)
        bar_colors = [
            CHART_COLORS[0] if (pd.isna(y) or y >= 0) else CHART_COLORS[1]
            for y in curr["yoy"]
        ]

        fig = go.Figure(go.Bar(
            x=curr[metric],
            y=curr["program_display"],
            orientation="h",
            marker_color=bar_colors,
            text=[f"{int(v):,}" for v in curr[metric]],
            textposition="outside",
            textfont=dict(family="Manrope, sans-serif", size=10, color=CARNEGIE_NAVY),
            hovertemplate="<b>%{y}</b><br>" + metric_label + ": %{x:,}<extra></extra>",
        ))

        max_val = int(curr[metric].max()) if not curr.empty else 1
        layout = _base_chart_layout(max(340, len(curr) * 28 + 60))
        layout["margin"] = dict(l=200, r=80, t=16, b=24)
        layout["xaxis"] = dict(
            range=[0, max_val * 1.25],
            tickfont=dict(family="Manrope, sans-serif", size=10, color="#9B9893"),
            showgrid=True, gridcolor="#F0EEEA", title="",
        )
        layout["yaxis"] = dict(
            tickfont=dict(family="Manrope, sans-serif", size=10.5, color=CARNEGIE_NAVY),
            showgrid=False, title="",
        )
        layout["hovermode"] = "y unified"
        fig.update_layout(**layout)
        return _plotly_html(fig)

    @render.ui
    def program_detail_table():
        df = filtered_programs()
        if df.empty:
            return ui.tags.div("No data available.", class_="empty-state")

        curr = df.groupby("program_display").agg(
            total_inquiries=("total_inquiries", "sum"),
            total_app_starts=("total_app_starts", "sum"),
            total_app_submits=("total_app_submits", "sum"),
            total_enrolled=("total_enrolled", "sum"),
            total_deposits=("total_deposits", "sum"),
            total_net_deposits=("total_net_deposits", "sum"),
        ).reset_index().sort_values("total_inquiries", ascending=False).head(20)

        total_inq = curr["total_inquiries"].sum()
        total_starts = curr["total_app_starts"].sum()
        total_submits = curr["total_app_submits"].sum()
        total_enrolled = curr["total_enrolled"].sum()

        curr["% Inquiries"] = curr["total_inquiries"].apply(
            lambda v: f"{v / total_inq * 100:.1f}%" if total_inq > 0 else "—"
        )
        curr["% App Starts"] = curr["total_app_starts"].apply(
            lambda v: f"{v / total_starts * 100:.1f}%" if total_starts > 0 else "—"
        )
        curr["Start Rate"] = curr.apply(
            lambda r: f"{r['total_app_starts'] / r['total_inquiries'] * 100:.1f}%"
            if r["total_inquiries"] > 0 else "—", axis=1
        )
        curr["% App Submits"] = curr["total_app_submits"].apply(
            lambda v: f"{v / total_submits * 100:.1f}%" if total_submits > 0 else "—"
        )
        curr["Submit Rate"] = curr.apply(
            lambda r: f"{r['total_app_submits'] / r['total_app_starts'] * 100:.1f}%"
            if r["total_app_starts"] > 0 else "—", axis=1
        )
        curr["% Enrolled"] = curr["total_enrolled"].apply(
            lambda v: f"{v / total_enrolled * 100:.1f}%" if total_enrolled > 0 else "—"
        )
        curr["Inq→Enroll Rate"] = curr.apply(
            lambda r: f"{r['total_enrolled'] / r['total_inquiries'] * 100:.1f}%"
            if r["total_inquiries"] > 0 else "—", axis=1
        )

        display = curr.rename(columns={
            "program_display": "Program",
            "total_inquiries": "Inquiries",
            "total_app_starts": "App Starts",
            "total_app_submits": "App Submits",
            "total_enrolled": "Enrolled",
            "total_deposits": "Deposits",
            "total_net_deposits": "Net Deposits",
        })
        cols = [
            "Program",
            "Inquiries", "% Inquiries",
            "App Starts", "% App Starts", "Start Rate",
            "App Submits", "% App Submits", "Submit Rate",
            "Enrolled", "% Enrolled", "Inq→Enroll Rate",
            "Deposits", "Net Deposits",
        ]
        return _plain_table(display[cols])

    # --- Geography Map + Top States (Q6 state data) ---

    _GEO_METRIC_LABELS = {
        "total_inquiries": "Student inquiries by state",
        "total_app_submits": "App submits by state",
        "total_admits": "Admits by state",
        "total_net_deposits": "Net deposits by state",
    }

    _GEO_METRIC_SHORT = {
        "total_inquiries": "Inquiries",
        "total_app_submits": "App Submits",
        "total_admits": "Admits",
        "total_net_deposits": "Net Deposits",
    }

    # Small states where text labels won't fit inside the state shape
    _SMALL_STATES = {"CT", "DE", "DC", "MA", "MD", "NH", "NJ", "RI", "VT"}

    # Approximate centroids for label placement (lat, lon)
    _STATE_CENTROIDS = {
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
    def geo_map_title():
        try:
            metric = input.geo_map_metric()
        except Exception:
            metric = "total_inquiries"
        label = _GEO_METRIC_LABELS.get(metric, "Student inquiries by state")
        return ui.tags.h2(label, class_="section-heading", style="margin:0;")

    @render.ui
    def geo_map_section():
        df = filtered_main()
        if df.empty:
            return ui.tags.div("No data available for the selected filters.", class_="empty-state")

        try:
            metric = input.geo_map_metric()
        except Exception:
            metric = "total_inquiries"
        metric_short = _GEO_METRIC_SHORT.get(metric, "Inquiries")

        # Aggregate by state + location_type from Q6
        funnel = ["total_inquiries", "total_app_starts", "total_app_submits",
                   "total_admits", "total_deposits", "total_net_deposits"]
        state_df = df.groupby(["student_state", "location_type"], as_index=False)[funnel].sum()

        # US-only for the map
        map_df = state_df[state_df["location_type"] == "US"].copy()
        if map_df.empty:
            return ui.tags.div("No mappable state data available.", class_="empty-state")

        import numpy as _np
        z_raw = map_df[metric].fillna(0)
        _POW = 0.3
        z_log = z_raw ** _POW
        # Build colorbar ticks in original scale
        _max_raw = z_raw.max()
        _tick_vals = [v ** _POW for v in [0, _max_raw * 0.1, _max_raw * 0.3, _max_raw * 0.6, _max_raw]]
        _tick_text = [f"{int(v):,}" for v in [0, _max_raw * 0.1, _max_raw * 0.3, _max_raw * 0.6, _max_raw]]

        fig = go.Figure(go.Choropleth(
            locations=map_df["student_state"],
            locationmode="USA-states",
            z=z_log,
            customdata=z_raw,
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
            font=dict(family="Inter, sans-serif", color=CARNEGIE_NAVY),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=8, b=8), height=420,
            geo=dict(
                bgcolor="rgba(0,0,0,0)", lakecolor=CARNEGIE_BG,
                landcolor="#eae6e1", showlakes=True, showframe=False,
                scope="usa", projection_type="albers usa",
            ),
        )

        # Overlay text labels for large states with data
        label_rows = map_df[
            map_df["student_state"].isin(_STATE_CENTROIDS) &
            ~map_df["student_state"].isin(_SMALL_STATES) &
            (map_df[metric] > 0)
        ]
        if not label_rows.empty:
            lats = [_STATE_CENTROIDS[s][0] for s in label_rows["student_state"]]
            lons = [_STATE_CENTROIDS[s][1] for s in label_rows["student_state"]]
            texts = [
                f"{s}<br>{int(v):,}"
                for s, v in zip(label_rows["student_state"], label_rows[metric])
            ]
            fig.add_scattergeo(
                lat=lats, lon=lons,
                text=texts,
                mode="text",
                textfont=dict(family="Manrope, sans-serif", size=9, color="#1A1A1A"),
                showlegend=False,
                hoverinfo="skip",
                geo="geo",
            )

        # Top 5 US states
        top_states = map_df.nlargest(5, metric)
        top_rows = [
            ui.tags.div(
                ui.tags.span(row["student_state"]),
                ui.tags.span(f"{int(row[metric]):,}", class_="count"),
                class_="top-state-row",
            )
            for _, row in top_states.iterrows()
        ]

        # International and Unknown summary
        total_all = state_df[metric].sum()
        intl_total = state_df.loc[state_df["location_type"] == "International", metric].sum()
        unknown_total = state_df.loc[state_df["location_type"] == "Unknown", metric].sum()
        intl_pct = (intl_total / total_all * 100) if total_all > 0 else 0
        unknown_pct = (unknown_total / total_all * 100) if total_all > 0 else 0

        summary_rows = []
        if intl_total > 0:
            summary_rows.append(ui.tags.div(
                ui.tags.span("International"),
                ui.tags.span(f"{int(intl_total):,}  ({intl_pct:.1f}%)", class_="count"),
                class_="top-state-row muted-row",
            ))
        if unknown_total > 0:
            summary_rows.append(ui.tags.div(
                ui.tags.span("Unknown"),
                ui.tags.span(f"{int(unknown_total):,}  ({unknown_pct:.1f}%)", class_="count"),
                class_="top-state-row muted-row",
            ))

        return ui.tags.div(
            ui.tags.div(_plotly_html(fig, no_toolbar=False)),
            ui.tags.div(
                ui.tags.div("TOP STATES", class_="top-states-title"),
                *top_rows,
                *(
                    [ui.tags.hr(class_="top-states-divider"), *summary_rows]
                    if summary_rows else []
                ),
                class_="top-states",
            ),
            class_="map-layout",
        )

    # --- Geography City Detail Table (Q3 — US only by default) ---

    @render.ui
    def geo_detail_table():
        df = filtered_q3()
        if df.empty:
            return ui.tags.div("No data available.", class_="empty-state")
        # Filter to US only by default; include_intl toggle if present
        include_all = getattr(input, "include_intl_unknown", lambda: False)()
        if not include_all:
            df = df[df["location_type"] == "US"]
        detail = compute_geo_detail(df)
        if detail.empty:
            return ui.tags.div("No data available.", class_="empty-state")
        display = detail.rename(columns={
            "student_state": "State",
            "student_city": "City",
            "total_inquiries": "Inquiries",
            "total_app_starts": "App Starts",
            "total_app_submits": "App Submits",
            "total_deposits": "Deposits",
            "total_net_deposits": "Net Deposits",
        })
        show_cols = ["State", "City", "Inquiries", "App Starts",
                     "App Submits", "Deposits", "Net Deposits"]
        heatmap_cols = [c for c in show_cols if c not in ("State", "City")]
        return _heatmap_table(display[show_cols], heatmap_cols, paginated=True)

    # ══════════════════════════════════════════════════════════
    # PAGE 4: DIGITAL PERFORMANCE
    # ══════════════════════════════════════════════════════════
    digital_server(input, output, session)
