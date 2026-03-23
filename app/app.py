"""Carnegie ROI Dashboard — UI layout and app entry point."""

from pathlib import Path
from shiny import App, ui

from data_loader import (
    get_institutions, get_term_years, get_term_semesters, get_student_types,
)
from server import server_logic

# --- Carnegie content width wrapper ---
_CW = (
    "width:100%; margin-left:auto; margin-right:auto; "
    "padding-left:clamp(3rem, 2.286rem + 1.905vw, 4rem); "
    "padding-right:clamp(3rem, 2.286rem + 1.905vw, 4rem); "
    "box-sizing:border-box;"
)


# --- Sidebar overlay (collapsible, left slide) ---

def _sidebar_overlay():
    """Filter sidebar that slides in from the left as an overlay."""
    return ui.tags.div(
        # Semi-transparent backdrop
        ui.tags.div(
            class_="sidebar-backdrop",
            onclick="document.body.classList.remove('sidebar-open');",
        ),
        # Sidebar panel
        ui.tags.div(
            # Header
            ui.tags.div(
                ui.tags.span("Filters", class_="sidebar-title"),
                ui.tags.button(
                    ui.tags.span("\u00d7"),
                    class_="sidebar-close",
                    onclick="document.body.classList.remove('sidebar-open');",
                ),
                class_="sidebar-header",
            ),
            # Filter controls
            ui.tags.div(
                ui.input_select(
                    "institution", "Institution",
                    choices=get_institutions(),
                    selected="Central Washington University",
                ),
                ui.input_select(
                    "term_year", "Term Year",
                    choices=get_term_years(),
                    selected="2026",
                ),
                ui.input_select(
                    "term_semester", "Term Semester",
                    choices=get_term_semesters(),
                    selected="Fall",
                ),
                ui.input_selectize(
                    "student_type", "Student Type",
                    choices=["All"] + get_student_types(),
                    selected=["All"],
                    multiple=True,
                ),
                ui.input_switch(
                    "is_international", "Include International",
                    value=True,
                ),
                class_="sidebar-filters",
            ),
            # Reset link
            ui.tags.div(
                ui.tags.a(
                    "Reset filters",
                    href="#",
                    class_="sidebar-reset",
                    onclick=(
                        "Shiny.setInputValue('institution','Central Washington University');"
                        "Shiny.setInputValue('term_year','2026');"
                        "Shiny.setInputValue('term_semester','Fall');"
                        "return false;"
                    ),
                ),
                class_="sidebar-footer",
            ),
            class_="sidebar-panel",
        ),
        class_="sidebar-overlay",
    )


# --- Funnel KPI card helper (6 primary cards in a strip) ---

PRIMARY_FUNNEL = [
    ("Inquiries", "total_inquiries"),
    ("App Starts", "total_app_starts"),
    ("App Submits", "total_app_submits"),
    ("Admits", "total_admits"),
    ("Deposits", "total_deposits"),
    ("Net Deposits", "total_net_deposits"),
]

SECONDARY_METRICS = [
    ("Admit Rate", "admitted_rate"),
    ("Yield Rate", "yield_rate"),
    ("Cost per Net Deposit", "cost_per_net_deposit"),
]


def _funnel_kpi_card(label: str, key: str):
    """Compact funnel KPI card with value, YoY delta, and progress bar."""
    return ui.tags.div(
        ui.tags.div(label, class_="funnel-label"),
        ui.tags.div(ui.output_text(f"kpi_{key}"), class_="funnel-value"),
        ui.output_ui(f"yoy_{key}"),
        ui.output_ui(f"progress_{key}"),
        class_="funnel-card",
    )


def _secondary_badge(label: str, key: str):
    """Small muted badge for secondary metrics."""
    return ui.tags.div(
        ui.tags.div(label, class_="secondary-label"),
        ui.tags.div(ui.output_text(f"kpi_{key}"), class_="secondary-value"),
        ui.output_ui(f"yoy_{key}"),
        class_="secondary-badge",
    )


# --- Metric choices for campaign bar chart ---
CAMPAIGN_METRIC_CHOICES = {
    "total_inquiries": "Inquiries",
    "total_app_starts": "App Starts",
    "total_app_submits": "App Submits",
    "total_admits": "Admits",
    "total_deposits": "Deposits",
    "total_net_deposits": "Net Deposits",
}


# --- Page 1: ROI Overview ---

page_overview = ui.nav_panel(
    "ROI Overview",
    ui.tags.div(
        # Section 1: Page header
        ui.tags.div(
            ui.tags.div(
                ui.tags.h1("ROI overview", class_="page-title"),
                ui.output_ui("page_subtitle"),
                class_="page-header-left",
            ),
            ui.output_ui("period_badge"),
            class_="page-header",
        ),

        # Section 2: Funnel health strip (6 cards)
        ui.tags.div(
            *[_funnel_kpi_card(label, key) for label, key in PRIMARY_FUNNEL],
            class_="funnel-strip",
        ),

        # Section 3: Secondary metrics row
        ui.tags.div(
            *[_secondary_badge(label, key) for label, key in SECONDARY_METRICS],
            class_="secondary-row",
        ),

        # Section 4: Main content (side by side)
        ui.tags.div(
            # Left: Trending chart
            ui.tags.div(
                ui.tags.div(
                    ui.tags.span("Trending performance", class_="card-heading"),
                    ui.tags.div(
                        ui.tags.div(
                            ui.input_radio_buttons(
                                "trending_metric", None,
                                choices={
                                    "net_deposits": "Net Deposits",
                                    "inquiries": "Inquiries",
                                    "admits": "Admits",
                                },
                                selected="net_deposits",
                                inline=True,
                            ),
                            class_="pill-toggle",
                        ),
                        ui.tags.div(
                            ui.input_radio_buttons(
                                "trending_mode", None,
                                choices={
                                    "cumulative": "Cumulative",
                                    "monthly": "Monthly",
                                },
                                selected="cumulative",
                                inline=True,
                            ),
                            class_="pill-toggle pill-toggle--secondary",
                        ),
                        class_="toggle-group",
                    ),
                    class_="card-header-row",
                ),
                ui.output_ui("trending_chart"),
                class_="chart-card",
            ),
            # Right: Progress to goal
            ui.tags.div(
                ui.tags.span("Progress to goal", class_="card-heading"),
                ui.output_ui("progress_to_goal"),
                class_="chart-card",
            ),
            class_="main-content-row",
        ),

        style=_CW,
    ),
)


# --- Page 2: Funnel Deep Dive ---

page_funnel = ui.nav_panel(
    "Funnel Deep Dive",
    ui.tags.div(
        # Page-specific filters
        ui.tags.div(
            ui.tags.div(
                ui.input_selectize(
                    "source_filter", "Lead Source",
                    choices=[],
                    multiple=True,
                ),
                class_="inline-filter",
            ),
            # Advanced filters (collapsible)
            ui.tags.div(
                ui.tags.a(
                    "+ Advanced filters",
                    href="#",
                    class_="advanced-toggle",
                    onclick=(
                        "var panel=this.nextElementSibling;"
                        "panel.style.display=panel.style.display==='none'?'flex':'none';"
                        "this.textContent=panel.style.display==='none'?'+ Advanced filters':'− Advanced filters';"
                        "return false;"
                    ),
                ),
                ui.tags.div(
                    ui.tags.div(
                        ui.input_selectize(
                            "program_level_adv", "Program Level",
                            choices=[],
                            multiple=True,
                        ),
                        class_="inline-filter",
                    ),
                    class_="advanced-filters-panel",
                    style="display:none;",
                ),
                class_="advanced-filters-wrap",
            ),
            class_="page-filter-bar",
        ),

        # Section 1: Funnel waterfall
        ui.tags.h2("Enrollment funnel", class_="section-heading"),
        ui.tags.div(
            ui.output_ui("funnel_waterfall"),
            class_="chart-card",
        ),

        # Section 2: Source performance (two columns)
        ui.tags.h2("Source performance", class_="section-heading"),
        ui.tags.div(
            # Left: table
            ui.tags.div(
                ui.output_data_frame("source_table"),
                class_="source-table-wrap",
            ),
            # Right: source trend chart
            ui.tags.div(
                ui.tags.div(
                    ui.tags.span("Source trend", class_="card-heading"),
                    ui.tags.div(
                        ui.input_radio_buttons(
                            "source_trend_metric", None,
                            choices={
                                "total_inquiries": "Inquiries",
                                "total_net_deposits": "Net Deposits",
                                "total_admits": "Admits",
                            },
                            selected="total_inquiries",
                            inline=True,
                        ),
                        class_="pill-toggle",
                    ),
                    class_="card-header-row",
                ),
                ui.output_ui("source_trend_chart"),
                class_="chart-card",
            ),
            class_="source-row",
        ),

        # Section 3: Conversion rates by source
        ui.tags.h2("Conversion rates by source", class_="section-heading"),
        ui.tags.div(
            ui.output_ui("conversion_by_source_chart"),
            class_="chart-card",
        ),

        style=_CW,
    ),
)


# --- Page 3: Geography (tabs: Programs + Geographic Markets) ---

page_geography = ui.nav_panel(
    "Geography",
    ui.tags.div(
        ui.navset_pill(
            # Tab 1: Programs
            ui.nav_panel(
                "Programs",
                ui.tags.div(
                    # Program filter bar
                    ui.tags.div(
                        ui.input_selectize(
                            "program_level_filter", "Program Level",
                            choices=[],
                            multiple=True,
                        ),
                        ui.tags.div(
                            ui.input_radio_buttons(
                                "program_metric", None,
                                choices={
                                    "total_net_deposits": "Net Deposits",
                                    "total_inquiries": "Inquiries",
                                    "total_admits": "Admits",
                                },
                                selected="total_net_deposits",
                                inline=True,
                            ),
                            class_="pill-toggle",
                        ),
                        class_="page-filter-bar",
                    ),
                    # Top programs bar chart
                    ui.tags.h2("Top programs", class_="section-heading"),
                    ui.tags.div(
                        ui.output_ui("programs_bar_chart"),
                        class_="chart-card",
                    ),
                    # Program detail table
                    ui.tags.h2("Program detail", class_="section-heading"),
                    ui.tags.div(
                        ui.output_data_frame("program_detail_table"),
                        class_="carnegie-table-card",
                    ),
                ),
            ),
            # Tab 2: Geographic markets
            ui.nav_panel(
                "Geographic markets",
                ui.tags.div(
                    # Map section heading + metric toggle
                    ui.tags.div(
                        ui.output_ui("geo_map_title"),
                        ui.tags.div(
                            ui.input_radio_buttons(
                                "geo_map_metric", None,
                                choices={
                                    "total_inquiries": "Inquiries",
                                    "total_app_submits": "App Submits",
                                    "total_admits": "Admits",
                                    "total_net_deposits": "Net Deposits",
                                },
                                selected="total_inquiries",
                                inline=True,
                            ),
                            class_="pill-toggle",
                        ),
                        class_="card-header-row",
                        style="margin-bottom:12px;",
                    ),
                    ui.tags.div(
                        ui.output_ui("geo_map_section"),
                        class_="chart-card",
                    ),
                    ui.tags.h2("State / City detail", class_="section-heading"),
                    ui.tags.div(
                        ui.input_switch(
                            "include_intl_unknown",
                            "Include international & unknown",
                            value=False,
                        ),
                        style="margin-bottom:12px;",
                    ),
                    ui.tags.div(
                        ui.output_data_frame("geo_detail_table"),
                        class_="carnegie-table-card",
                    ),
                ),
            ),
            id="geo_tabs",
        ),
        style=_CW,
    ),
)


# --- Page 4: Digital Performance (placeholder) ---

page_digital = ui.nav_panel(
    "Digital Performance",
    ui.tags.div(
        ui.tags.div(
            ui.tags.div(
                ui.tags.h2("Digital performance analytics are coming soon.",
                           style="font-weight:400; color:var(--carnegie-navy); margin-bottom:8px;"),
                ui.tags.p(
                    "Campaign, channel, and interaction data will be available in a future update.",
                    style="color:var(--carnegie-gray-text); font-size:14px;",
                ),
                style="text-align:center; padding:80px 24px;",
            ),
            class_="chart-card",
        ),
        style=_CW,
    ),
)


# --- Navbar title (hamburger + logo + dashboard name) ---

navbar_title = ui.tags.div(
    # Hamburger button
    ui.tags.button(
        ui.tags.span(class_="hamburger-line"),
        ui.tags.span(class_="hamburger-line"),
        ui.tags.span(class_="hamburger-line"),
        class_="hamburger-btn",
        onclick="document.body.classList.toggle('sidebar-open');",
        title="Toggle filters",
    ),
    # Logo
    ui.tags.img(
        src="img/Carnegie-Logo-Black.png",
        height="18",
        style="width: 139px; vertical-align: middle; margin-right: 16px;",
    ),
    # Title
    ui.tags.span("ROI Report", class_="navbar-title-text"),
    style="display: flex; align-items: center;",
)


# --- Main layout ---

app_ui = ui.page_navbar(
    ui.nav_spacer(),
    page_overview,
    page_funnel,
    page_geography,
    page_digital,
    title=navbar_title,
    id="nav",
    header=[
        ui.head_content(
            ui.tags.link(rel="stylesheet", href="styles.css?v=5"),
        ),
        _sidebar_overlay(),
    ],
)

app = App(app_ui, server_logic, static_assets=str(Path(__file__).parent / "www"))
