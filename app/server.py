"""Carnegie ROI Dashboard — Reactive server logic."""

from shiny import render, reactive, ui, req
import plotly.graph_objects as go
import pandas as pd

from data_loader import Q1, Q2, Q3, Q4, GOALS
from metrics import (
    FUNNEL_COLS, COST_PER_DEFS,
    compute_funnel_kpis, compute_yoy_change,
    compute_cost_summary, compute_campaign_breakdown,
    compute_geo_state_summary, compute_geo_detail,
)
from formatters import fmt_number, fmt_pct, fmt_currency, fmt_yoy

# ── Carnegie brand colors for Plotly ─────────────────────────

CARNEGIE_RED = "#FA3320"
CARNEGIE_NAVY = "#021324"
CARNEGIE_GRAY_TEXT = "#6b7280"
CARNEGIE_GRAY_BORDER = "#e5e1dc"
CARNEGIE_BG = "#f8f4f0"
CARNEGIE_WHITE = "#ffffff"
CARNEGIE_GREEN = "#2d8a4e"
CARNEGIE_AMBER = "#c8962d"

# Secondary chart palette
CHART_PALETTE = [
    CARNEGIE_RED, CARNEGIE_NAVY, "#A8BDD6", "#C9D444", "#E8D9B8",
    "#E8D8F6", "#B3C78D",
]

# Shared Plotly layout overrides
PLOTLY_LAYOUT = dict(
    font=dict(family="Inter, sans-serif", color=CARNEGIE_NAVY, size=12),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor=CARNEGIE_WHITE,
    margin=dict(l=48, r=24, t=40, b=48),
    xaxis=dict(
        gridcolor=CARNEGIE_GRAY_BORDER, gridwidth=1, griddash="dash",
        tickfont=dict(size=12, color=CARNEGIE_GRAY_TEXT),
        title_font=dict(size=12, color=CARNEGIE_GRAY_TEXT),
    ),
    yaxis=dict(
        gridcolor=CARNEGIE_GRAY_BORDER, gridwidth=1, griddash="dash",
        tickfont=dict(size=12, color=CARNEGIE_GRAY_TEXT),
        title_font=dict(size=12, color=CARNEGIE_GRAY_TEXT),
    ),
    legend=dict(
        orientation="h", yanchor="top", y=-0.18, xanchor="center", x=0.5,
        font=dict(size=12),
    ),
    hoverlabel=dict(
        bgcolor=CARNEGIE_WHITE, bordercolor=CARNEGIE_GRAY_BORDER,
        font=dict(family="Inter, sans-serif", size=13, color=CARNEGIE_NAVY),
    ),
)


def _apply_layout(fig, title: str = "", height: int = 400):
    """Apply Carnegie brand layout to a Plotly figure."""
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text=title, font=dict(size=14, color=CARNEGIE_NAVY), x=0, xanchor="left"),
        height=height,
    )
    return fig


def _plotly_html(fig):
    """Convert plotly figure to HTML widget."""
    return ui.HTML(fig.to_html(full_html=False, include_plotlyjs="cdn"))


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

# GOALS imported from data_loader — institution-level aggregated from roi_goals.csv


def server_logic(input, output, session):

    # ── Reactive filtered DataFrames ─────────────────────────

    @reactive.calc
    def filtered_q1():
        df = Q1.copy()
        df = df[df["institution_name"] == input.institution()]
        df = df[df["term_year"] == int(input.term_year())]
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
    def prior_q1():
        df = Q1.copy()
        df = df[df["institution_name"] == input.institution()]
        df = df[df["term_year"] == int(input.term_year()) - 1]
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
    def trending_q4():
        """Filtered Q4 monthly trending data for the chart."""
        df = Q4.copy()
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
    def filtered_q2():
        df = Q2.copy()
        df = df[df["institution_name"] == input.institution()]
        df = df[df["term_year"] == int(input.term_year())]
        df = df[df["term_semester"] == input.term_semester()]
        # Page-specific source filter
        src = input.source_filter()
        if src and len(src) > 0:
            df = df[df["lead_source"].isin(src)]
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
        df = Q3.copy()
        df = df[df["institution_name"] == input.institution()]
        df = df[df["term_year"] == int(input.term_year())]
        df = df[df["term_semester"] == input.term_semester()]
        return df

    # ── Update source filter choices ─────────────────────────

    @reactive.effect
    def _update_source_choices():
        df = Q2.copy()
        df = df[df["institution_name"] == input.institution()]
        sources = sorted(df["lead_source"].dropna().unique().tolist())
        ui.update_selectize("source_filter", choices=sources, selected=[])

    # ── KPI Calculations ─────────────────────────────────────

    @reactive.calc
    def current_kpis():
        return compute_funnel_kpis(filtered_q1())

    @reactive.calc
    def prior_kpis():
        return compute_funnel_kpis(prior_q1())

    @reactive.calc
    def yoy_changes():
        return compute_yoy_change(current_kpis(), prior_kpis())

    @reactive.calc
    def cost_data():
        return compute_cost_summary(filtered_q2())

    # ── Page 1: ROI Overview ─────────────────────────────────

    # Page subtitle
    @render.ui
    def page_subtitle():
        inst = input.institution()
        return ui.tags.span(f"\u2014 {inst}", class_="page-subtitle")

    # Period badge
    @render.ui
    def period_badge():
        sem = input.term_semester()
        yr = input.term_year()
        return ui.tags.span(
            f"{sem} {yr} \u00b7 as of Mar 18, 2026",
            class_="period-badge",
        )

    # --- Primary KPI outputs (6 funnel stages) ---

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
        badge_class = {
            "positive": "kpi-badge kpi-badge--positive",
            "negative": "kpi-badge kpi-badge--negative",
            "neutral": "kpi-badge kpi-badge--neutral",
            "na": "kpi-badge kpi-badge--na",
        }.get(sentiment, "kpi-badge kpi-badge--na")
        return ui.tags.span(text, class_=badge_class)

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
        return _yoy_badge("admitted_rate")

    @render.ui
    def yoy_yield_rate():
        return _yoy_badge("yield_rate")

    @render.ui
    def yoy_cost_per_net_deposit():
        # Cost per Net Deposit = total spend (Q2) / net deposits (Q1)
        curr_spend = filtered_q2()["total_cost"].sum()
        curr_nd = current_kpis().get("total_net_deposits", 0)
        curr_cpnd = (curr_spend / curr_nd) if curr_nd > 0 and curr_spend > 0 else None

        prior_spend = prior_q2()["total_cost"].sum()
        prior_nd = prior_kpis().get("total_net_deposits", 0)
        prior_cpnd = (prior_spend / prior_nd) if prior_nd > 0 and prior_spend > 0 else None

        if curr_cpnd is None or prior_cpnd is None or prior_cpnd == 0:
            return ui.tags.span("N/A", class_="kpi-badge kpi-badge--na")

        pct = ((curr_cpnd - prior_cpnd) / abs(prior_cpnd)) * 100
        # For cost, lower is better — invert sentiment
        text, _ = fmt_yoy(pct)
        sentiment = "positive" if pct < 0 else "negative" if pct > 0 else "neutral"
        badge_class = f"kpi-badge kpi-badge--{sentiment}"
        return ui.tags.span(text, class_=badge_class)

    # --- Micro progress bars (KPI funnel strip cards) ---

    def _goal_color(pct: float) -> str:
        """Green >= 95%, Amber 80-95%, Red < 80%."""
        if pct >= 95:
            return "#0D7A4A"
        elif pct >= 80:
            return "#C48A1A"
        return "#C93030"

    def _progress_bar(key: str):
        goal = GOALS.get(key)
        if not goal or goal <= 0:
            return ui.tags.div()  # No goal — hide bar
        actual = current_kpis().get(key, 0)
        pct = (actual / goal) * 100
        bar_width = min(pct, 100)
        color = _goal_color(pct)
        return ui.tags.div(
            ui.tags.div(
                style=f"width:{bar_width:.0f}%; height:4px; background:{color}; border-radius:2px;",
            ),
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

    # ── Page 1: Trending Chart ───────────────────────────────

    @render.ui
    def trending_chart():
        stage = input.trending_metric()  # e.g. "net_deposits"
        mode = input.trending_mode()     # "cumulative" or "monthly"
        df = trending_q4()
        if df.empty:
            return ui.tags.div("No data available for the selected filters.", class_="empty-state")

        # Filter to selected stage
        df = df[df["stage"] == stage].copy()
        if df.empty:
            return ui.tags.div("No data available for this stage.", class_="empty-state")

        current_ty = int(input.term_year())
        prior_ty = current_ty - 1

        # Aggregate by term_year + acad_pos + month_label (sum across student_type etc.)
        agg = df.groupby(["term_year", "acad_pos", "month_label"], as_index=False)["stage_count"].sum()

        curr = agg[agg["term_year"] == current_ty].sort_values("acad_pos").copy()
        prior = agg[agg["term_year"] == prior_ty].sort_values("acad_pos").copy()

        if curr.empty and prior.empty:
            return ui.tags.div("No data available for the selected filters.", class_="empty-state")

        # Apply cumulative if needed
        y_col = "stage_count"
        if mode == "cumulative":
            if not curr.empty:
                curr["cumulative"] = curr["stage_count"].cumsum()
            if not prior.empty:
                prior["cumulative"] = prior["stage_count"].cumsum()
            y_col = "cumulative"

        # Build figure
        stage_label = PRIMARY_LABELS.get(f"total_{stage}", stage.replace("_", " ").title())
        fig = go.Figure()

        # Prior year line (dashed gray)
        if not prior.empty:
            fig.add_trace(go.Scatter(
                x=prior["month_label"], y=prior[y_col],
                mode="lines+markers",
                name=f"{prior_ty - 1}-{str(prior_ty)[-2:]}",
                line=dict(color="#B5B2AA", width=1.8, dash="dash"),
                marker=dict(color="#B5B2AA", size=5),
                hovertemplate="<b>%{x}</b><br>" + stage_label + ": %{y:,}<extra></extra>",
            ))

        # Current year line (solid red)
        if not curr.empty:
            fig.add_trace(go.Scatter(
                x=curr["month_label"], y=curr[y_col],
                mode="lines+markers",
                name=f"{current_ty - 1}-{str(current_ty)[-2:]}",
                line=dict(color="#EA332D", width=2.5),
                marker=dict(color="#EA332D", size=7),
                hovertemplate="<b>%{x}</b><br>" + stage_label + ": %{y:,}<extra></extra>",
            ))

            # 3-month moving average trend line on current year
            if len(curr) >= 3:
                curr["trend"] = curr[y_col].rolling(window=3).mean()
                trend_df = curr.dropna(subset=["trend"])
                if not trend_df.empty:
                    fig.add_trace(go.Scatter(
                        x=trend_df["month_label"], y=trend_df["trend"],
                        mode="lines",
                        name="3-mo trend",
                        line=dict(color="#E8A099", width=1.5, dash="dash"),
                        hovertemplate="<b>%{x}</b><br>3-mo avg: %{y:,.0f}<extra></extra>",
                    ))

        # Academic month order for x-axis
        month_order = ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
                       "Jan", "Feb", "Mar", "Apr", "May", "Jun"]

        fig.update_layout(
            font=dict(family="Manrope, sans-serif", color=CARNEGIE_NAVY, size=10.5),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=48, r=16, t=8, b=40),
            height=360,
            xaxis=dict(
                categoryorder="array",
                categoryarray=month_order,
                tickfont=dict(family="Manrope, sans-serif", size=10.5, color="#9B9893"),
                showgrid=False,
                title="",
            ),
            yaxis=dict(
                tickfont=dict(family="Manrope, sans-serif", size=10.5, color="#9B9893"),
                gridcolor="#F0EEEA",
                gridwidth=0.8,
                showline=False,
                nticks=5,
                title="",
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

        return ui.HTML(
            fig.to_html(full_html=False, include_plotlyjs="cdn",
                        config={"displayModeBar": False})
        )

    # ── Page 1: Progress to Goal ─────────────────────────────

    @render.ui
    def progress_to_goal():
        kpis = current_kpis()
        bars = []
        for key in PRIMARY_KEYS:
            label = PRIMARY_LABELS[key]
            goal = GOALS.get(key)
            if not goal or goal <= 0:
                # No goal for this stage
                bars.append(
                    ui.tags.div(
                        ui.tags.div(
                            ui.tags.span(label, class_="goal-label"),
                            ui.tags.span("No goal set", class_="goal-pct muted"),
                            class_="goal-header",
                        ),
                        ui.tags.div(
                            ui.tags.div(style="width:0%; height:8px; background:#ddd; border-radius:4px;"),
                            class_="goal-bar-bg",
                        ),
                        class_="goal-row",
                    )
                )
                continue

            actual = kpis.get(key, 0)
            pct = (actual / goal) * 100
            bar_width = min(pct, 100)  # Cap visual fill at 100%
            color = _goal_color(pct)
            bars.append(
                ui.tags.div(
                    ui.tags.div(
                        ui.tags.span(label, class_="goal-label"),
                        ui.tags.span(f"{pct:.0f}%", class_="goal-pct"),
                        class_="goal-header",
                    ),
                    ui.tags.div(
                        ui.tags.div(style=f"width:{bar_width:.0f}%; height:8px; background:{color}; border-radius:4px;"),
                        class_="goal-bar-bg",
                    ),
                    class_="goal-row",
                )
            )
        return ui.tags.div(*bars, class_="goal-bars")

    # ── Page 2: Funnel Waterfall ─────────────────────────────

    @render.ui
    def funnel_waterfall():
        df_curr = filtered_q2()
        df_prior = prior_q2()
        if df_curr.empty:
            return ui.tags.div("No data available for the selected filters.", class_="empty-state")

        curr_kpis = compute_funnel_kpis(filtered_q1())
        prior_kpi = compute_funnel_kpis(prior_q1())

        stages = PRIMARY_KEYS
        labels = [PRIMARY_LABELS[k] for k in stages]
        curr_vals = [curr_kpis.get(k, 0) for k in stages]
        prior_vals = [prior_kpi.get(k, 0) for k in stages]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=labels, y=curr_vals, name="Current Year",
            marker_color=CARNEGIE_RED,
            text=[f"{v:,}" for v in curr_vals], textposition="outside",
            hovertemplate="<b>%{x}</b><br>Current: %{y:,}<extra></extra>",
        ))
        fig.add_trace(go.Bar(
            x=labels, y=prior_vals, name="Prior Year",
            marker_color="#A8BDD6",
            text=[f"{v:,}" for v in prior_vals], textposition="outside",
            hovertemplate="<b>%{x}</b><br>Prior: %{y:,}<extra></extra>",
            opacity=0.5,
        ))

        # Add conversion rate annotations between stages
        for i in range(len(stages) - 1):
            if curr_vals[i] > 0:
                rate = (curr_vals[i + 1] / curr_vals[i]) * 100
                fig.add_annotation(
                    x=(i + i + 1) / 2, y=max(curr_vals[i], curr_vals[i + 1]) * 1.05,
                    text=f"{rate:.1f}%", showarrow=False,
                    font=dict(size=11, color=CARNEGIE_GRAY_TEXT),
                )

        _apply_layout(fig, "", height=380)
        fig.update_layout(
            barmode="group",
            xaxis=dict(title=""),
            yaxis=dict(title=""),
        )
        return _plotly_html(fig)

    # ── Page 2: Source Performance Table ──────────────────────

    @render.data_frame
    def source_table():
        df = filtered_q2()
        breakdown = compute_campaign_breakdown(df)
        if breakdown.empty:
            return render.DataGrid(pd.DataFrame({"No data available": []}))

        # Prior year for YoY
        prior_bd = compute_campaign_breakdown(prior_q2())

        display = pd.DataFrame()
        display["Source"] = breakdown["lead_source"]
        display["Inquiries"] = breakdown["total_inquiries"].apply(lambda x: f"{int(x):,}")
        display["App Submits"] = breakdown["total_app_submits"].apply(lambda x: f"{int(x):,}")
        display["Admits"] = breakdown["total_admits"].apply(lambda x: f"{int(x):,}")
        display["Net Deposits"] = breakdown["total_net_deposits"].apply(lambda x: f"{int(x):,}")

        # YoY delta on net deposits
        yoy_col = []
        for _, row in breakdown.iterrows():
            src = row["lead_source"]
            curr_nd = row["total_net_deposits"]
            prior_row = prior_bd[prior_bd["lead_source"] == src]
            if prior_row.empty or prior_row.iloc[0]["total_net_deposits"] == 0:
                yoy_col.append("\u2014")
            else:
                prev_nd = prior_row.iloc[0]["total_net_deposits"]
                pct = ((curr_nd - prev_nd) / abs(prev_nd)) * 100
                yoy_col.append(f"{pct:+.1f}%")
        display["YoY \u0394"] = yoy_col

        return render.DataGrid(
            display.sort_values("Net Deposits", ascending=False, key=lambda x: x.str.replace(",", "").astype(int)),
            filters=False,
        )

    # ── Page 2: Source Trend Chart ───────────────────────────

    @render.ui
    def source_trend_chart():
        # Show top sources across all years
        df = Q2.copy()
        df = df[df["institution_name"] == input.institution()]
        df = df[df["term_semester"] == input.term_semester()]
        metric = input.source_trend_metric()

        if df.empty:
            return ui.tags.div("No data available.", class_="empty-state")

        # Get top 5 sources by current year volume
        curr_year = int(input.term_year())
        curr_df = df[df["term_year"] == curr_year]
        top_sources = (
            curr_df.groupby("lead_source")[metric].sum()
            .nlargest(5).index.tolist()
        )
        if not top_sources:
            return ui.tags.div("No source data available.", class_="empty-state")

        fig = go.Figure()
        for i, src in enumerate(top_sources):
            sdf = df[df["lead_source"] == src].groupby("term_year", as_index=False)[metric].sum()
            sdf = sdf.sort_values("term_year")
            color = CHART_PALETTE[i % len(CHART_PALETTE)]
            fig.add_trace(go.Scatter(
                x=sdf["term_year"], y=sdf[metric],
                mode="lines+markers", name=src,
                line=dict(color=color, width=2),
                marker=dict(size=6),
                hovertemplate=f"<b>{src}</b><br>%{{x}}: %{{y:,}}<extra></extra>",
            ))

        _apply_layout(fig, "", height=320)
        fig.update_layout(xaxis=dict(dtick=1, title=""), yaxis=dict(title=""))
        return _plotly_html(fig)

    # ── Page 2: Conversion Rates by Source ────────────────────

    @render.ui
    def conversion_by_source_chart():
        df = filtered_q2()
        if df.empty:
            return ui.tags.div("No data available.", class_="empty-state")

        breakdown = compute_campaign_breakdown(df)
        if breakdown.empty:
            return ui.tags.div("No data available.", class_="empty-state")

        # Compute admit rate and yield rate per source
        breakdown["admit_rate"] = breakdown.apply(
            lambda r: (r["total_admits"] / r["total_app_submits"] * 100)
            if r["total_app_submits"] > 0 else 0, axis=1
        )
        breakdown["yield_rate"] = breakdown.apply(
            lambda r: (r["total_net_deposits"] / r["total_admits"] * 100)
            if r["total_admits"] > 0 else 0, axis=1
        )

        bd = breakdown.nlargest(6, "total_inquiries")

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=bd["lead_source"], y=bd["admit_rate"],
            name="Admit Rate", marker_color=CARNEGIE_NAVY,
            hovertemplate="<b>%{x}</b><br>Admit Rate: %{y:.1f}%<extra></extra>",
        ))
        fig.add_trace(go.Bar(
            x=bd["lead_source"], y=bd["yield_rate"],
            name="Yield Rate", marker_color=CARNEGIE_RED,
            hovertemplate="<b>%{x}</b><br>Yield Rate: %{y:.1f}%<extra></extra>",
        ))

        _apply_layout(fig, "", height=340)
        fig.update_layout(
            barmode="group",
            xaxis=dict(title=""),
            yaxis=dict(title="", ticksuffix="%"),
        )
        return _plotly_html(fig)

    # ── Page 3: Programs (placeholder — Q3 has geo but no program data) ──

    @render.ui
    def programs_bar_chart():
        # Q3 does not have program data, show placeholder
        return ui.tags.div(
            "Program-level data is not available in the current dataset. "
            "This view will populate when program data is connected.",
            class_="empty-state",
        )

    @render.data_frame
    def program_detail_table():
        return render.DataGrid(pd.DataFrame({
            "Program data is not available": ["Connect program data source to enable this view."]
        }))

    # ── Page 3: Geography Map + Top States ───────────────────

    @render.ui
    def geo_map_section():
        df = filtered_q3()
        if df.empty:
            return ui.tags.div("No data available for the selected filters.", class_="empty-state")

        state_df = compute_geo_state_summary(df)
        map_df = state_df[~state_df["student_state"].isin(["Unknown", "International"])].copy()

        if map_df.empty:
            return ui.tags.div("No mappable state data available.", class_="empty-state")

        # Choropleth with Carnegie red gradient
        fig = go.Figure(go.Choropleth(
            locations=map_df["student_state"],
            locationmode="USA-states",
            z=map_df["total_inquiries"],
            colorscale=[
                [0, "#fce4ec"],
                [0.3, "#ef9a9a"],
                [0.6, "#e57373"],
                [1, CARNEGIE_RED],
            ],
            hovertemplate="<b>%{location}</b><br>Inquiries: %{z:,}<extra></extra>",
            colorbar=dict(
                title="Inquiries",
                thickness=12, len=0.6,
                tickfont=dict(size=11, color=CARNEGIE_GRAY_TEXT),
                title_font=dict(size=11, color=CARNEGIE_GRAY_TEXT),
            ),
        ))
        fig.update_layout(
            font=dict(family="Inter, sans-serif", color=CARNEGIE_NAVY),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=8, b=8),
            height=420,
            geo=dict(
                bgcolor="rgba(0,0,0,0)",
                lakecolor=CARNEGIE_BG,
                landcolor="#eae6e1",
                showlakes=True,
                showframe=False,
                scope="usa",
                projection_type="albers usa",
            ),
        )

        # Top states sidebar
        top_states = map_df.nlargest(5, "total_inquiries")
        top_rows = [
            ui.tags.div(
                ui.tags.span(row["student_state"]),
                ui.tags.span(f"{int(row['total_inquiries']):,}", class_="count"),
                class_="top-state-row",
            )
            for _, row in top_states.iterrows()
        ]

        return ui.tags.div(
            ui.tags.div(_plotly_html(fig)),
            ui.tags.div(
                ui.tags.div("TOP STATES", class_="top-states-title"),
                *top_rows,
                class_="top-states",
            ),
            class_="map-layout",
        )

    # ── Page 3: Geography Detail Table ───────────────────────

    @render.data_frame
    def geo_detail_table():
        df = filtered_q3()
        detail = compute_geo_detail(df)
        if detail.empty:
            return render.DataGrid(pd.DataFrame({"No data available": []}))
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
        return render.DataGrid(display[show_cols], filters=False)
