"""Carnegie ROI Dashboard — Reactive server logic."""

from shiny import render, reactive, ui
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from data_loader import Q1, Q2, Q3
from metrics import (
    FUNNEL_COLS, COST_PER_DEFS,
    compute_funnel_kpis, compute_yoy_change,
    compute_cost_summary, compute_campaign_breakdown,
    compute_geo_state_summary, compute_geo_detail,
)
from formatters import fmt_number, fmt_pct, fmt_currency, fmt_yoy

# ── Carnegie brand colors for Plotly ─────────────────────────

CARNEGIE_RED = "#c8372d"
CARNEGIE_NAVY = "#1a2332"
CARNEGIE_GRAY_TEXT = "#6b7280"
CARNEGIE_GRAY_BORDER = "#e5e1dc"
CARNEGIE_BG = "#f8f4f0"
CARNEGIE_WHITE = "#ffffff"
CARNEGIE_RED_15 = "rgba(200, 55, 45, 0.15)"

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


def server_logic(input, output, session):

    # ── Reactive filtered DataFrames ─────────────────────────

    @reactive.calc
    def filtered_q1():
        df = Q1.copy()
        df = df[df["institution_name"] == input.institution()]
        years = [int(y) for y in input.term_year()]
        df = df[df["term_year"].isin(years)]
        df = df[df["term_semester"] == input.term_semester()]
        if input.student_type() != "All":
            df = df[df["student_type"] == input.student_type()]
        if not input.is_international():
            df = df[df["is_international"] == False]  # noqa: E712
        return df

    @reactive.calc
    def prior_q1():
        df = Q1.copy()
        df = df[df["institution_name"] == input.institution()]
        years = [int(y) - 1 for y in input.term_year()]
        df = df[df["term_year"].isin(years)]
        df = df[df["term_semester"] == input.term_semester()]
        if input.student_type() != "All":
            df = df[df["student_type"] == input.student_type()]
        if not input.is_international():
            df = df[df["is_international"] == False]  # noqa: E712
        return df

    @reactive.calc
    def trending_q1():
        """All years — ignores term_year and term_semester filters."""
        df = Q1.copy()
        df = df[df["institution_name"] == input.institution()]
        if input.student_type() != "All":
            df = df[df["student_type"] == input.student_type()]
        if not input.is_international():
            df = df[df["is_international"] == False]  # noqa: E712
        return df.groupby(
            ["term_year", "term_semester"], as_index=False
        )["total_inquiries"].sum()

    @reactive.calc
    def filtered_q2():
        df = Q2.copy()
        df = df[df["institution_name"] == input.institution()]
        years = [int(y) for y in input.term_year()]
        df = df[df["term_year"].isin(years)]
        df = df[df["term_semester"] == input.term_semester()]
        return df

    @reactive.calc
    def filtered_q3():
        df = Q3.copy()
        df = df[df["institution_name"] == input.institution()]
        years = [int(y) for y in input.term_year()]
        df = df[df["term_year"].isin(years)]
        df = df[df["term_semester"] == input.term_semester()]
        return df

    # ── Page 1: KPI Cards ────────────────────────────────────

    @reactive.calc
    def current_kpis():
        return compute_funnel_kpis(filtered_q1())

    @reactive.calc
    def yoy_changes():
        current = compute_funnel_kpis(filtered_q1())
        prior = compute_funnel_kpis(prior_q1())
        return compute_yoy_change(current, prior)

    # --- KPI value outputs ---

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

    @render.text
    def kpi_total_enrolled():
        return fmt_number(current_kpis()["total_enrolled"])

    @render.text
    def kpi_admitted_rate():
        return fmt_pct(current_kpis()["admitted_rate"])

    @render.text
    def kpi_yield_rate():
        return fmt_pct(current_kpis()["yield_rate"])

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
    def yoy_total_enrolled():
        return _yoy_badge("total_enrolled")

    @render.ui
    def yoy_admitted_rate():
        return _yoy_badge("admitted_rate")

    @render.ui
    def yoy_yield_rate():
        return _yoy_badge("yield_rate")

    # ── Page 1: Trending Chart ───────────────────────────────

    @render.ui
    def trending_chart():
        df = trending_q1()
        if df.empty:
            return ui.tags.div("No data available for the selected filters.", class_="empty-state")

        df_sorted = df.sort_values("term_year")
        semester_colors = {"Fall": CARNEGIE_RED, "Spring": CARNEGIE_NAVY, "Summer": CARNEGIE_GRAY_TEXT}

        fig = go.Figure()
        for semester in df_sorted["term_semester"].unique():
            sdf = df_sorted[df_sorted["term_semester"] == semester]
            color = semester_colors.get(semester, CARNEGIE_GRAY_TEXT)
            fig.add_trace(go.Scatter(
                x=sdf["term_year"], y=sdf["total_inquiries"],
                mode="lines+markers", name=semester,
                line=dict(color=color, width=2),
                marker=dict(color=color, size=7),
                hovertemplate="<b>%{x}</b><br>Inquiries: %{y:,}<extra></extra>",
            ))

        _apply_layout(fig, "Inquiry Volume by Term Year", height=400)
        fig.update_layout(xaxis=dict(dtick=1))
        return ui.HTML(fig.to_html(full_html=False, include_plotlyjs="cdn"))

    # ── Page 1: Cost Summary Table ───────────────────────────

    @render.ui
    def cost_summary_section():
        df = filtered_q2()
        summary = compute_cost_summary(df)
        if summary["total_cost"] == 0 and df.empty:
            return ui.tags.div(
                ui.tags.div("No cost data available for the selected filters.", class_="empty-state"),
                class_="cost-summary-card",
            )
        headers = [d[0] for d in COST_PER_DEFS]
        values = [fmt_currency(summary[d[1]]) for d in COST_PER_DEFS]
        return ui.tags.div(
            ui.tags.table(
                ui.tags.thead(
                    ui.tags.tr(*[ui.tags.th(h, class_="text-end") for h in headers]),
                ),
                ui.tags.tbody(
                    ui.tags.tr(*[ui.tags.td(v, class_="text-end") for v in values]),
                ),
                class_="carnegie-table",
            ),
            class_="cost-summary-card",
        )

    # ── Page 2: Campaign Bar Chart ───────────────────────────

    @render.ui
    def campaign_bar_chart():
        df = filtered_q2()
        if df.empty:
            return ui.tags.div("No data available for the selected filters.", class_="empty-state")

        breakdown = compute_campaign_breakdown(df)
        metric = input.campaign_metric()

        if metric.startswith("cost_per"):
            breakdown[metric] = breakdown[metric].fillna(0)

        label = metric.replace("_", " ").title()
        fig = px.bar(
            breakdown, x="lead_source", y=metric,
            labels={"lead_source": "Lead Source", metric: label},
            color_discrete_sequence=[CARNEGIE_RED],
        )
        fig.update_traces(
            hovertemplate="<b>%{x}</b><br>" + label + ": %{y:,.0f}<extra></extra>",
        )
        _apply_layout(fig, f"{label} by Lead Source", height=420)
        fig.update_layout(showlegend=False)
        return ui.HTML(fig.to_html(full_html=False, include_plotlyjs="cdn"))

    # ── Page 2: Campaign Detail Table ────────────────────────

    @render.data_frame
    def campaign_detail_table():
        df = filtered_q2()
        breakdown = compute_campaign_breakdown(df)
        if breakdown.empty:
            return render.DataGrid(pd.DataFrame({"No data available": []}))
        display = pd.DataFrame()
        display["Lead Source"] = breakdown["lead_source"]
        display["Total Spend"] = breakdown["total_cost"].apply(fmt_currency)
        for display_name, col_name, _ in COST_PER_DEFS:
            display[display_name] = breakdown[col_name].apply(
                lambda x: fmt_currency(x) if x is not None else "\u2014"
            )
        return render.DataGrid(display, filters=True)

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
        fig = px.choropleth(
            map_df,
            locations="student_state",
            locationmode="USA-states",
            color="total_inquiries",
            scope="usa",
            color_continuous_scale=[
                [0, "#fce4ec"],
                [0.3, "#ef9a9a"],
                [0.6, "#e57373"],
                [1, CARNEGIE_RED],
            ],
            labels={"student_state": "State", "total_inquiries": "Inquiries"},
        )
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
                projection_type="albers usa",
            ),
            coloraxis_colorbar=dict(
                title="Inquiries",
                thickness=12,
                len=0.6,
                tickfont=dict(size=11, color=CARNEGIE_GRAY_TEXT),
                title_font=dict(size=11, color=CARNEGIE_GRAY_TEXT),
            ),
        )
        fig.update_traces(
            hovertemplate="<b>%{location}</b><br>Inquiries: %{z:,}<extra></extra>",
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
            ui.tags.div(
                ui.HTML(fig.to_html(full_html=False, include_plotlyjs="cdn")),
            ),
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
            "total_enrolled": "Enrolled",
        })
        show_cols = ["State", "City", "Inquiries", "App Starts",
                     "App Submits", "Deposits", "Enrolled"]
        return render.DataGrid(display[show_cols], filters=True)
