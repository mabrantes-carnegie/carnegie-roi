"""Carnegie ROI Dashboard — UI layout and app entry point."""

from pathlib import Path
from shiny import App, ui

from data_loader import (
    get_institutions, get_term_years, get_term_semesters, get_student_types,
)
from server import server_logic

# --- KPI card definitions ---
KPI_CARDS = [
    ("Inquiries", "total_inquiries"),
    ("App Starts", "total_app_starts"),
    ("App Submits", "total_app_submits"),
    ("Admits", "total_admits"),
    ("Deposits", "total_deposits"),
    ("Net Deposits", "total_net_deposits"),
    ("Enrolled", "total_enrolled"),
    ("Admitted Rate", "admitted_rate"),
    ("Yield Rate", "yield_rate"),
]

# --- Metric choices for campaign bar chart ---
CAMPAIGN_METRIC_CHOICES = {
    "total_inquiries": "Inquiries",
    "total_app_starts": "App Starts",
    "total_app_submits": "App Submits",
    "total_admits": "Admits",
    "total_deposits": "Deposits",
    "total_enrolled": "Enrolled",
    "cost_per_inquiry": "Cost per Inquiry",
    "cost_per_deposit": "Cost per Deposit",
    "cost_per_enrolled": "Cost per Enrolled",
}


def _kpi_card(title: str, key: str):
    """Build a custom KPI card matching Carnegie design."""
    return ui.tags.div(
        ui.tags.div(title, class_="kpi-label"),
        ui.tags.div(ui.output_text(f"kpi_{key}"), class_="kpi-value"),
        ui.output_ui(f"yoy_{key}"),
        class_="kpi-card",
    )


# --- Filter bar (horizontal, inside a card) ---

def _filter_bar():
    return ui.tags.div(
        ui.tags.div(
            ui.input_select(
                "institution", "Institution",
                choices=get_institutions(),
                selected="Central Washington University",
            ),
            ui.input_selectize(
                "term_year", "Term Year",
                choices=get_term_years(),
                selected=["2026"],
                multiple=True,
            ),
            ui.input_select(
                "term_semester", "Term Semester",
                choices=get_term_semesters(),
                selected="Fall",
            ),
            ui.input_select(
                "student_type", "Student Type",
                choices=["All"] + get_student_types(),
                selected="First Year",
            ),
            ui.input_switch(
                "is_international", "Include International",
                value=False,
            ),
            class_="filter-bar",
        ),
        ui.tags.div(
            "Student Type and International filters apply to Funnel data only.",
            class_="filter-note",
        ),
        class_="carnegie-card mb-32",
    )


# --- Carnegie content width wrapper ---
_CW = (
    "width:100%; margin-left:auto; margin-right:auto; "
    "padding-left:clamp(3rem, 2.286rem + 1.905vw, 4rem); "
    "padding-right:clamp(3rem, 2.286rem + 1.905vw, 4rem); "
    "box-sizing:border-box;"
)


# --- Page layouts ---

page_funnel = ui.nav_panel(
    "ROI Overview",
    ui.tags.div(
        ui.tags.h2("Enrollment Funnel KPIs", class_="section-heading"),
        ui.tags.div(
            *[_kpi_card(title, key) for title, key in KPI_CARDS],
            class_="kpi-grid",
        ),
        ui.tags.h2("Inquiry Trending", class_="section-heading"),
        ui.tags.div(
            ui.output_ui("trending_chart"),
            class_="chart-card",
        ),
        ui.tags.h2("Inquiry-to-Enrollment Cost Summary", class_="section-heading"),
        ui.output_ui("cost_summary_section"),
        style=_CW,
    ),
)

page_campaign = ui.nav_panel(
    "Funnel Deep Dive",
    ui.tags.div(
        ui.tags.h2("Lead Source Breakdown", class_="section-heading"),
        ui.tags.div(
            ui.tags.div(
                ui.input_select(
                    "campaign_metric", "Select Metric",
                    choices=CAMPAIGN_METRIC_CHOICES,
                    selected="total_inquiries",
                ),
                class_="metric-selector",
            ),
            ui.output_ui("campaign_bar_chart"),
            class_="chart-card",
        ),
        ui.tags.h2("Cost per Lead Source", class_="section-heading"),
        ui.tags.div(
            ui.output_data_frame("campaign_detail_table"),
            class_="carnegie-table-card",
        ),
        style=_CW,
    ),
)

page_geography = ui.nav_panel(
    "Geography",
    ui.tags.div(
        ui.tags.h2("Student Inquiries by State", class_="section-heading"),
        ui.tags.div(
            ui.output_ui("geo_map_section"),
            class_="chart-card",
        ),
        ui.tags.h2("State / City Detail", class_="section-heading"),
        ui.tags.div(
            ui.output_data_frame("geo_detail_table"),
            class_="carnegie-table-card",
        ),
        style=_CW,
    ),
)


# --- Navbar title (logo + dashboard name) ---

navbar_title = ui.tags.div(
    ui.tags.img(
        src="img/Carnegie-Logo-Black.png",
        height="18",
        style="width: 139px; vertical-align: middle; margin-right: 20px;",
    ),
    ui.tags.span(
        "ROI Report",
        class_="navbar-title-text",
    ),
    style="display: flex; align-items: center;",
)


# --- Main layout ---

app_ui = ui.page_navbar(
    ui.nav_spacer(),
    page_funnel,
    page_campaign,
    page_geography,
    title=navbar_title,
    id="nav",
    header=[
        ui.head_content(
            ui.tags.link(rel="stylesheet", href="styles.css?v=3"),
        ),
        ui.tags.div(
            _filter_bar(),
            style="padding-top:24px; padding-bottom:0; " + _CW,
        ),
    ],
)

app = App(app_ui, server_logic, static_assets=str(Path(__file__).parent / "www"))
