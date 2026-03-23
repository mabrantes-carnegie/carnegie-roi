"""Digital Performance page — reactive server logic (all 5 sub-tabs)."""

import pandas as pd
from shiny import render, reactive, ui, req
import plotly.graph_objects as go

from digital_data import Q8, Q9, Q10, Q11_CREATIVE, Q11_KEYWORDS, Q12
from formatters import fmt_number, fmt_currency

# ── Carnegie brand colors ────────────────────────────────────
CARNEGIE_RED = "#FA3320"
CARNEGIE_NAVY = "#021324"
CARNEGIE_GRAY_TEXT = "#6b7280"
CARNEGIE_GRAY_BORDER = "#e5e1dc"
CARNEGIE_BG = "#f8f4f0"
CARNEGIE_WHITE = "#ffffff"
CARNEGIE_GREEN = "#2d8a4e"

# Palette for multi-line charts
STRATEGY_COLORS = [
    "#EA332D", "#021326", "#C99D44", "#4A90D9", "#E8B9A4",
    "#6B4C9A", "#2D8A4E", "#D4A574", "#7FB3D3", "#C97B84",
]


def _plotly_html(fig, no_toolbar=True):
    config = {"displayModeBar": False} if no_toolbar else {}
    return ui.HTML(fig.to_html(full_html=False, include_plotlyjs="cdn", config=config))


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
        return ui.tags.span("N/A", class_="yoy-badge neutral")
    pct = (curr - prev) / abs(prev) * 100
    rounded = round(pct, 1)
    if rounded > 0:
        arrow, sentiment = "\u25b2", ("negative" if invert else "positive")
    elif rounded < 0:
        arrow, sentiment = "\u25bc", ("positive" if invert else "negative")
    else:
        arrow, sentiment = "", "neutral"
    return ui.tags.span(
        f"{arrow} {abs(rounded):.1f}% vs. prior",
        class_=f"yoy-badge {sentiment}",
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

        # Monthly aggregation
        curr_monthly = df_curr.groupby(df_curr["day"].dt.to_period("M"))["total_interactions"].sum().reset_index()
        curr_monthly["day"] = curr_monthly["day"].dt.to_timestamp()
        curr_monthly["label"] = curr_monthly["day"].dt.strftime("%b %Y")

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=curr_monthly["label"], y=curr_monthly["total_interactions"],
            mode="lines+markers", name="Current",
            line=dict(color=CARNEGIE_RED, width=2),
            marker=dict(size=5),
            hovertemplate="%{x}<br>Interactions: %{y:,.1f}<extra></extra>",
        ))

        if not df_prior.empty:
            prior_monthly = df_prior.groupby(df_prior["day"].dt.to_period("M"))["total_interactions"].sum().reset_index()
            prior_monthly["day"] = prior_monthly["day"].dt.to_timestamp()
            prior_monthly["label"] = prior_monthly["day"].dt.strftime("%b %Y")
            fig.add_trace(go.Scatter(
                x=prior_monthly["label"], y=prior_monthly["total_interactions"],
                mode="lines+markers", name="Prior",
                line=dict(color="#9B9893", width=2, dash="dash"),
                marker=dict(size=4),
                hovertemplate="%{x}<br>Interactions: %{y:,.1f}<extra></extra>",
            ))

        fig.update_layout(**_base_layout(320))
        return _plotly_html(fig)

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

        fig = go.Figure(go.Bar(
            x=strat["impressions"], y=strat["product_name"],
            orientation="h", marker_color=CARNEGIE_RED,
            text=[f"{p:.1f}%" for p in strat["pct"]],
            textposition="outside",
            textfont=dict(family="Manrope, sans-serif", size=10, color=CARNEGIE_NAVY),
            hovertemplate="<b>%{y}</b><br>Impressions: %{x:,}<extra></extra>",
        ))
        layout = _base_layout(max(260, len(strat) * 28 + 60))
        layout["margin"] = dict(l=140, r=60, t=8, b=24)
        layout["xaxis"] = dict(showgrid=True, gridcolor="#F0EEEA", title="")
        layout["yaxis"] = dict(showgrid=False, title="")
        fig.update_layout(**layout)
        return _plotly_html(fig)

    # --- Strategy trend ---

    @render.ui
    def dig_strategy_trend():
        df = _dig_q8()
        if df.empty:
            return ui.tags.div("No data available.", class_="empty-state")

        top5 = df.groupby("product_name")["impressions"].sum().nlargest(5).index.tolist()
        df_top = df[df["product_name"].isin(top5)].copy()
        monthly = df_top.groupby([df_top["day"].dt.to_period("M"), "product_name"])["impressions"].sum().reset_index()
        monthly["day"] = monthly["day"].dt.to_timestamp()
        monthly["label"] = monthly["day"].dt.strftime("%b %Y")

        fig = go.Figure()
        for i, prod in enumerate(top5):
            sub = monthly[monthly["product_name"] == prod]
            fig.add_trace(go.Scatter(
                x=sub["label"], y=sub["impressions"],
                mode="lines+markers", name=prod,
                line=dict(color=STRATEGY_COLORS[i % len(STRATEGY_COLORS)], width=2),
                marker=dict(size=4),
                hovertemplate=f"<b>{prod}</b><br>%{{x}}<br>Impressions: %{{y:,}}<extra></extra>",
            ))
        fig.update_layout(**_base_layout(320))
        return _plotly_html(fig)

    # --- Subgroup performance table ---

    @render.data_frame
    def dig_subgroup_table():
        df_c = _dig_q8()
        df_p = _dig_q8_prior()
        if df_c.empty:
            return render.DataGrid(pd.DataFrame({"No data available": []}))

        metrics = ["impressions", "clicks", "direct_conversions",
                   "view_through_conversions", "in_platform_leads", "total_interactions"]
        curr = df_c.groupby("subgroup_name")[metrics].sum().reset_index()
        curr["CTR"] = (curr["clicks"] / curr["impressions"].replace(0, float("nan")) * 100).round(2)

        if not df_p.empty:
            prev = df_p.groupby("subgroup_name")[metrics].sum().reset_index()
            for m in metrics:
                prev_map = prev.set_index("subgroup_name")[m]
                curr[f"{m}_delta"] = curr.apply(
                    lambda r: _pct_change(r[m], prev_map.get(r["subgroup_name"], 0)), axis=1
                )
        else:
            for m in metrics:
                curr[f"{m}_delta"] = "N/A"

        display = curr.sort_values("impressions", ascending=False)
        cols = {"subgroup_name": "Subgroup", "impressions": "Impressions",
                "clicks": "Clicks", "CTR": "CTR %",
                "direct_conversions": "Direct Conv.", "view_through_conversions": "View-through",
                "in_platform_leads": "In-Platform Leads", "total_interactions": "Total Interactions"}
        display = display.rename(columns=cols)
        show = list(cols.values())
        return render.DataGrid(display[[c for c in show if c in display.columns]], filters=False)

    # --- Strategy performance table ---

    @render.data_frame
    def dig_strategy_table():
        df_c = _dig_q8()
        if df_c.empty:
            return render.DataGrid(pd.DataFrame({"No data available": []}))

        metrics = ["impressions", "clicks", "direct_conversions",
                   "view_through_conversions", "in_platform_leads", "total_interactions"]
        curr = df_c.groupby("product_name")[metrics].sum().reset_index()
        curr["CTR"] = (curr["clicks"] / curr["impressions"].replace(0, float("nan")) * 100).round(2)
        display = curr.sort_values("impressions", ascending=False).rename(columns={
            "product_name": "Strategy", "impressions": "Impressions",
            "clicks": "Clicks", "CTR": "CTR %",
            "direct_conversions": "Direct Conv.", "view_through_conversions": "View-through",
            "in_platform_leads": "In-Platform Leads", "total_interactions": "Total Interactions",
        })
        show = ["Strategy", "Impressions", "Clicks", "CTR %", "Direct Conv.",
                "View-through", "In-Platform Leads", "Total Interactions"]
        return render.DataGrid(display[[c for c in show if c in display.columns]], filters=False)

    # --- Interactions by month & year ---

    @render.data_frame
    def dig_interactions_by_month():
        df = _dig_q8()
        if df.empty:
            return render.DataGrid(pd.DataFrame({"No data available": []}))

        df = df.copy()
        df["year"] = df["day"].dt.year
        df["month_name"] = df["day"].dt.strftime("%b")
        pivot = df.groupby(["year", "month_name"])["total_interactions"].sum().reset_index()
        pivot_wide = pivot.pivot(index="year", columns="month_name", values="total_interactions").fillna(0)
        month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                       "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        cols = [m for m in month_order if m in pivot_wide.columns]
        pivot_wide = pivot_wide[cols]
        pivot_wide["Grand Total"] = pivot_wide.sum(axis=1)
        pivot_wide = pivot_wide.reset_index().rename(columns={"year": "Year"})
        # Format
        for c in cols + ["Grand Total"]:
            pivot_wide[c] = pivot_wide[c].apply(lambda v: f"{v:,.1f}")
        return render.DataGrid(pivot_wide, filters=False)

    # --- Interactions by strategy & month ---

    @render.data_frame
    def dig_interactions_by_strategy_month():
        df = _dig_q8()
        if df.empty:
            return render.DataGrid(pd.DataFrame({"No data available": []}))

        df = df.copy()
        df["ym"] = df["day"].dt.strftime("%Y-%m")
        pivot = df.groupby(["product_name", "ym"])["total_interactions"].sum().reset_index()
        pivot_wide = pivot.pivot(index="product_name", columns="ym", values="total_interactions").fillna(0)
        pivot_wide = pivot_wide[sorted(pivot_wide.columns)]
        pivot_wide["Grand Total"] = pivot_wide.sum(axis=1)
        pivot_wide = pivot_wide.sort_values("Grand Total", ascending=False).reset_index()
        pivot_wide = pivot_wide.rename(columns={"product_name": "Strategy"})
        for c in pivot_wide.columns[1:]:
            pivot_wide[c] = pivot_wide[c].apply(lambda v: f"{v:,.1f}" if isinstance(v, (int, float)) else v)
        return render.DataGrid(pivot_wide, filters=False)

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
        monthly = df.groupby([df["day"].dt.to_period("M"), "interaction_category"])["total_interactions"].sum().reset_index()
        monthly["day"] = monthly["day"].dt.to_timestamp()
        monthly["label"] = monthly["day"].dt.strftime("%b %Y")

        fig = go.Figure()
        for i, cat in enumerate(cats):
            sub = monthly[monthly["interaction_category"] == cat]
            if sub.empty:
                continue
            fig.add_trace(go.Scatter(
                x=sub["label"], y=sub["total_interactions"],
                mode="lines+markers", name=cat,
                line=dict(color=STRATEGY_COLORS[i % len(STRATEGY_COLORS)], width=2),
                marker=dict(size=4),
            ))
        fig.update_layout(**_base_layout(340))
        return _plotly_html(fig)

    # --- Category × Strategy chart ---

    @render.ui
    def dig_cat_strategy_chart():
        df = _dig_q9_filtered()
        if df.empty:
            return ui.tags.div("No data available.", class_="empty-state")

        grouped = df.groupby(["interaction_category", "product_name"])["total_interactions"].sum().reset_index()
        cats = ["RFI/Lead Gen", "Visit/Event", "Apply", "Enroll/Deposit", "Other"]
        products = grouped.groupby("product_name")["total_interactions"].sum().nlargest(8).index.tolist()

        fig = go.Figure()
        for i, prod in enumerate(products):
            sub = grouped[grouped["product_name"] == prod]
            sub = sub.set_index("interaction_category").reindex(cats).fillna(0).reset_index()
            fig.add_trace(go.Bar(
                x=sub["interaction_category"], y=sub["total_interactions"],
                name=prod, marker_color=STRATEGY_COLORS[i % len(STRATEGY_COLORS)],
            ))
        layout = _base_layout(380)
        layout["barmode"] = "group"
        layout["bargap"] = 0.25
        fig.update_layout(**layout)
        return _plotly_html(fig)

    # --- Interaction breakdown table ---

    @render.data_frame
    def dig_interaction_breakdown_table():
        df = _dig_q9_filtered()
        if df.empty:
            return render.DataGrid(pd.DataFrame({"No data available": []}))

        agg = df.groupby(["interaction_category", "conversion_name"]).agg(
            direct=("direct_conversions", "sum"),
            vt=("view_through_conversions", "sum"),
            total=("total_interactions", "sum"),
        ).reset_index().sort_values("total", ascending=False)

        agg = agg.rename(columns={
            "interaction_category": "Category", "conversion_name": "Conversion Type",
            "direct": "Direct Conv.", "vt": "View-through", "total": "Total Interactions",
        })
        for c in ["Direct Conv.", "View-through", "Total Interactions"]:
            agg[c] = agg[c].apply(lambda v: f"{v:,.1f}")
        return render.DataGrid(agg, filters=False)

    # --- Interactions by campaign name ---

    @render.data_frame
    def dig_interactions_campaign_table():
        df = _dig_q9_filtered()
        if df.empty:
            return render.DataGrid(pd.DataFrame({"No data available": []}))

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
        for c in wide.columns[2:]:
            wide[c] = wide[c].apply(lambda v: f"{v:,.1f}" if isinstance(v, (int, float)) else v)
        return render.DataGrid(wide, filters=False)

    # --- Interactions by month pivot ---

    @render.data_frame
    def dig_interactions_month_table():
        df = _dig_q9_filtered()
        if df.empty:
            return render.DataGrid(pd.DataFrame({"No data available": []}))

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
        for c in num_cols + ["Grand Total"]:
            wide[c] = wide[c].apply(lambda v: f"{v:,.1f}" if isinstance(v, (int, float)) else v)
        return render.DataGrid(wide, filters=False)

    # --- Interactions detail table ---

    @render.data_frame
    def dig_interactions_detail_table():
        df = _dig_q9_filtered()
        if df.empty:
            return render.DataGrid(pd.DataFrame({"No data available": []}))

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
        for c in ["Total Conv.", "Direct Conv.", "View-through Conv."]:
            agg[c] = agg[c].apply(lambda v: f"{v:,.1f}")
        return render.DataGrid(agg, filters=False)

    # ══════════════════════════════════════════════════════════
    # TAB 3: GEOGRAPHY
    # ══════════════════════════════════════════════════════════

    @render.data_frame
    def dig_geo_table():
        df = _apply_dig_filters_monthly(Q10.copy())
        if df.empty:
            return render.DataGrid(pd.DataFrame({"No data available": []}))

        metric = input.dig_geo_metric() if hasattr(input, "dig_geo_metric") else "impressions"
        metrics = ["impressions", "clicks", "direct_conversions",
                   "view_through_conversions", "total_conversions"]
        agg = df.groupby("region")[metrics].sum().reset_index()
        agg["CTR"] = (agg["clicks"] / agg["impressions"].replace(0, float("nan")) * 100).round(2)
        agg = agg.sort_values(metric, ascending=False)
        agg = agg.rename(columns={
            "region": "Region", "impressions": "Impressions", "clicks": "Clicks",
            "direct_conversions": "Direct Conv.", "view_through_conversions": "View-through",
            "total_conversions": "Total Conversions",
        })
        show = ["Region", "Impressions", "Clicks", "CTR", "Direct Conv.",
                "View-through", "Total Conversions"]
        return render.DataGrid(agg[[c for c in show if c in agg.columns]], filters=False)

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

    @render.data_frame
    def dig_perf_notes_table():
        df = _dig_notes()
        df = df[df["note_type"].isin(["Performance", "Performance with Recommendation"])]
        if df.empty:
            return render.DataGrid(pd.DataFrame({"No data available": []}))
        df = df.sort_values("day", ascending=False).copy()
        df["Date"] = df["day"].dt.strftime("%b %d, %Y")
        display = df[["Date", "notes"]].rename(columns={"notes": "Performance Insight Notes"})
        return render.DataGrid(display, filters=False)

    @render.data_frame
    def dig_optim_table():
        df = _dig_notes()
        df = df[df["note_type"] == "Optimization"]
        if df.empty:
            return render.DataGrid(pd.DataFrame({"No data available": []}))
        df = df.sort_values("day", ascending=False).copy()
        df["Date"] = df["day"].dt.strftime("%b %d, %Y")
        display = df[["Date", "campaign_name", "notes"]].rename(columns={
            "campaign_name": "Campaign", "notes": "Optimization Notes",
        })
        return render.DataGrid(display, filters=False)


def _pct_change(curr, prev):
    """Format percentage change."""
    if not prev or prev == 0:
        return "N/A"
    pct = (curr - prev) / abs(prev) * 100
    return f"{pct:+.1f}%"


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
