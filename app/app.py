"""Carnegie ROI Dashboard — UI layout and app entry point."""

from pathlib import Path
from shiny import App, ui

from datetime import date


def _pill_dropdown(input_id: str, choices: dict, selected: str):
    """Reusable iOS-style pill dropdown that sets a hidden Shiny input."""
    default_label = choices[selected]
    return ui.tags.div(
        # Hidden Shiny input — provides default value at session start
        ui.tags.div(
            ui.input_radio_buttons(
                input_id, None,
                choices=choices,
                selected=selected,
                inline=True,
            ),
            style="display:none;",
        ),
        # Visible pill button + menu
        ui.tags.div(
            ui.tags.button(
                ui.tags.span(default_label),
                ui.tags.span("▾", class_="pill-dropdown-arrow"),
                class_="pill-dropdown-btn",
                onclick=(
                    "var m=this.nextElementSibling;"
                    "m.style.display=m.style.display==='block'?'none':'block';"
                    "event.stopPropagation();"
                ),
            ),
            ui.tags.div(
                *[
                    ui.tags.div(
                        label,
                        class_="pill-dropdown-option" + (" active" if value == selected else ""),
                        **{
                            "data-value": value,
                            "onclick": (
                                "var pd=this.closest('.pill-dropdown');"
                                "pd.querySelector('.pill-dropdown-btn span:first-child').textContent=this.textContent;"
                                "pd.querySelector('.pill-dropdown-menu').style.display='none';"
                                f"Shiny.setInputValue('{input_id}','{value}',{{priority:'event'}});"
                                "pd.querySelectorAll('.pill-dropdown-option').forEach(function(el){el.classList.remove('active')});"
                                "this.classList.add('active');"
                            ),
                        },
                    )
                    for value, label in choices.items()
                ],
                class_="pill-dropdown-menu",
            ),
            class_="pill-dropdown",
        ),
    )

from data_loader import (
    get_institutions, get_term_years, get_term_semesters, get_student_types,
)
from digital_data import (
    get_digital_date_range, get_digital_groups, get_digital_subgroups,
    get_digital_products, get_digital_campaigns,
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

_COST_METRICS = [
    ("Cost/Inquiry", "cost_per_inquiry"),
    ("Cost/App Start", "cost_per_app_start"),
    ("Cost/App Submit", "cost_per_app_submit"),
    ("Cost/Admit", "cost_per_admit"),
    ("Cost/Deposit", "cost_per_deposit"),
]


def _funnel_kpi_card(label: str, key: str):
    """Compact funnel KPI card with value, YoY delta, goal text, and progress bar."""
    return ui.tags.div(
        ui.tags.div(label, class_="funnel-label"),
        ui.tags.div(ui.output_text(f"kpi_{key}"), class_="funnel-value"),
        ui.output_ui(f"yoy_{key}"),
        ui.output_ui(f"goal_text_{key}"),
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
            _secondary_badge("Admit Rate", "admitted_rate"),
            _secondary_badge("Yield Rate", "yield_rate"),
            # Enrolled badge with tooltip
            ui.tags.div(
                ui.tags.div("Enrolled", class_="secondary-label"),
                ui.tags.div(ui.output_text("kpi_total_enrolled"), class_="secondary-value"),
                ui.output_ui("yoy_total_enrolled"),
                title="Students who completed enrollment. May differ from Net Deposits due to enrollment timing and process variations.",
                class_="secondary-badge",
            ),
            # Melt Rate badge
            ui.output_ui("melt_rate_secondary"),
            # Cost/Net Deposit badge with inline expand link
            ui.tags.div(
                ui.tags.div("Cost per Net Deposit", class_="secondary-label"),
                ui.tags.div(ui.output_text("kpi_cost_per_net_deposit"), class_="secondary-value"),
                ui.tags.div(
                    ui.output_ui("yoy_cost_per_net_deposit"),
                    ui.tags.a(
                        "View all costs \u2197",
                        href="#",
                        class_="cost-expand-link",
                        onclick=(
                            "var p=document.getElementById('cost-expand-inner');"
                            "if(!p)return false;"
                            "p.style.display=p.style.display==='none'?'flex':'none';"
                            "this.textContent=p.style.display==='none'?'View all costs \u2197':'Hide costs \u2197';"
                            "return false;"
                        ),
                    ),
                    class_="cost-badge-footer",
                ),
                class_="secondary-badge",
            ),
            class_="secondary-row",
        ),
        # Expandable cost detail panel — single server-rendered output, toggled by CSS class
        ui.output_ui("cost_detail_panel"),

        # Section 4: Main content (side by side)
        ui.tags.div(
            # Left: Trending chart
            ui.tags.div(
                ui.tags.div(
                    ui.tags.span("Trending performance", class_="card-heading"),
                    ui.tags.div(
                        _pill_dropdown(
                            "trending_metric",
                            {
                                "inquiries": "Inquiries",
                                "app_starts": "App Starts",
                                "app_submits": "App Submits",
                                "admits": "Admits",
                                "deposits": "Deposits",
                                "net_deposits": "Net Deposits",
                            },
                            "inquiries",
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
            # Right: Funnel at a glance
            ui.tags.div(
                ui.tags.span("Funnel at a glance", class_="card-heading"),
                ui.output_ui("funnel_at_glance"),
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
                    _pill_dropdown(
                        "source_trend_metric",
                        {
                            "total_inquiries": "Inquiries",
                            "total_net_deposits": "Net Deposits",
                            "total_admits": "Admits",
                        },
                        "total_inquiries",
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


# --- Page 3: Programs ---

PROGRAM_TREND_METRICS = {
    "total_inquiries": "Inquiries",
    "total_app_starts": "App Starts",
    "total_app_submits": "App Submits",
    "total_deposits": "Deposits",
    "total_net_deposits": "Net Deposits",
}

page_programs = ui.nav_panel(
    "Programs",
    ui.tags.div(
        # Program filter bar
        ui.tags.div(
            ui.input_selectize(
                "program_name_filter", "Program",
                choices=[],
                multiple=True,
            ),
            class_="page-filter-bar",
        ),
        # Program trending vs goal
        ui.tags.div(
            ui.tags.div(
                ui.tags.span("Program trending vs. goal", class_="card-heading"),
                _pill_dropdown("program_trend_metric", PROGRAM_TREND_METRICS, "total_inquiries"),
                class_="card-header-row",
            ),
            ui.output_ui("program_trend_chart"),
            class_="chart-card",
        ),
        # Top programs bar chart
        ui.tags.div(
            ui.tags.div(
                ui.tags.span("Top programs", class_="card-heading"),
                _pill_dropdown("program_metric", PROGRAM_TREND_METRICS, "total_inquiries"),
                class_="card-header-row",
            ),
            ui.output_ui("programs_bar_chart"),
            class_="chart-card",
        ),
        # Program detail table
        ui.tags.h2("Program detail", class_="section-heading"),
        ui.tags.div(
            ui.output_data_frame("program_detail_table"),
            class_="carnegie-table-card",
        ),
        style=_CW,
    ),
)


# --- Page 4: Geography ---

page_geography = ui.nav_panel(
    "Geography",
    ui.tags.div(
        # Map section heading + metric toggle
        ui.tags.div(
            ui.output_ui("geo_map_title"),
            _pill_dropdown(
                "geo_map_metric",
                {
                    "total_inquiries": "Inquiries",
                    "total_app_submits": "App Submits",
                    "total_admits": "Admits",
                    "total_net_deposits": "Net Deposits",
                },
                "total_inquiries",
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
        style=_CW,
    ),
)


# --- Page 5: Digital Performance (5 sub-tabs) ---

_dig_min, _dig_max = get_digital_date_range()

def _digital_filters():
    """Shared filter bar for digital performance page."""
    return ui.tags.div(
        ui.tags.div(
            ui.input_date_range(
                "dig_period", "Period",
                start=date(2025, 7, 1),
                end=_dig_max.date(),
                min=_dig_min.date(),
                max=_dig_max.date(),
            ),
            class_="inline-filter",
            style="min-width:220px;",
        ),
        ui.tags.div(
            ui.input_selectize(
                "dig_group", "Group",
                choices=get_digital_groups(),
                multiple=True,
            ),
            class_="inline-filter",
        ),
        ui.tags.div(
            ui.input_selectize(
                "dig_subgroup", "Subgroup",
                choices=get_digital_subgroups(),
                multiple=True,
            ),
            class_="inline-filter",
        ),
        ui.tags.div(
            ui.input_selectize(
                "dig_product", "Product",
                choices=get_digital_products(),
                multiple=True,
            ),
            class_="inline-filter",
        ),
        ui.tags.div(
            ui.tags.a(
                "+ Campaign",
                href="#",
                class_="advanced-toggle",
                onclick=(
                    "var panel=this.nextElementSibling;"
                    "panel.style.display=panel.style.display==='none'?'block':'none';"
                    "this.textContent=panel.style.display==='none'?'+ Campaign':'− Campaign';"
                    "return false;"
                ),
            ),
            ui.tags.div(
                ui.input_selectize(
                    "dig_campaign", "Campaign",
                    choices=get_digital_campaigns(),
                    multiple=True,
                ),
                style="display:none; margin-top:6px;",
            ),
            class_="inline-filter",
        ),
        class_="page-filter-bar",
        style="flex-wrap:wrap; gap:12px;",
    )


def _dig_kpi_card(label, output_id, border_color="#EA332D"):
    """Digital KPI card with colored top border."""
    return ui.tags.div(
        ui.tags.div(label, class_="funnel-label"),
        ui.tags.div(ui.output_text(f"dig_{output_id}"), class_="funnel-value"),
        ui.output_ui(f"dig_{output_id}_delta"),
        class_="funnel-card",
        style=f"border-top:3px solid {border_color};",
    )


def _dig_metric_card(label, output_id):
    """Small metric card for engagement grid."""
    return ui.tags.div(
        ui.tags.div(label, class_="secondary-label"),
        ui.tags.div(ui.output_text(f"dig_{output_id}"), class_="secondary-value"),
        ui.output_ui(f"dig_{output_id}_delta"),
        class_="secondary-badge",
    )


_dig_tab_overview = ui.nav_panel(
    "Overview",
    ui.tags.div(
        # KPI strip
        ui.tags.div(
            _dig_kpi_card("Key Interactions", "key_interactions", "#EA332D"),
            _dig_kpi_card("Cost per Interaction", "cpi", "#021326"),
            _dig_kpi_card("Inquiry Interactions", "inquiry_int", "#C99D44"),
            _dig_kpi_card("Visit Interactions", "visit_int", "#E8B9A4"),
            _dig_kpi_card("Apply Interactions", "apply_int", "#8B1A1A"),
            class_="funnel-strip",
        ),

        # Trending + engagement grid
        ui.tags.div(
            # Left: trending
            ui.tags.div(
                ui.tags.span("Trending performance", class_="card-heading"),
                ui.output_ui("dig_trending_chart"),
                class_="chart-card",
                style="flex:3;",
            ),
            # Right: engagement metrics (2×4 grid)
            ui.tags.div(
                ui.tags.span("Engagement & spend", class_="card-heading"),
                ui.tags.div(
                    _dig_metric_card("Budget", "budget"),
                    _dig_metric_card("Cost per Click", "cpc"),
                    _dig_metric_card("Direct Conversions", "direct_conv"),
                    _dig_metric_card("Cost per Direct Conv.", "cpdc"),
                    _dig_metric_card("In-Platform Leads", "ipl"),
                    _dig_metric_card("Cost per In-Plat. Lead", "cpipl"),
                    _dig_metric_card("View-through Conv.", "vtc"),
                    _dig_metric_card("Cost per Total Conv.", "cptc"),
                    class_="dig-metric-grid",
                ),
                class_="chart-card",
                style="flex:2;",
            ),
            class_="main-content-row",
        ),

        # Strategy section
        ui.tags.div(
            ui.tags.div(
                ui.tags.span("Performance by strategy", class_="card-heading"),
                ui.output_ui("dig_strategy_bar"),
                class_="chart-card",
                style="flex:1;",
            ),
            ui.tags.div(
                ui.tags.span("Strategy trend", class_="card-heading"),
                ui.output_ui("dig_strategy_trend"),
                class_="chart-card",
                style="flex:1;",
            ),
            class_="main-content-row",
        ),

        # Subgroup table
        ui.tags.h2("Performance by subgroup", class_="section-heading"),
        ui.tags.div(
            ui.output_data_frame("dig_subgroup_table"),
            class_="carnegie-table-card",
        ),

        # Strategy table
        ui.tags.h2("Performance by strategy", class_="section-heading"),
        ui.tags.div(
            ui.output_data_frame("dig_strategy_table"),
            class_="carnegie-table-card",
        ),

        # Interactions by month pivot
        ui.tags.h2("Interactions by month & year", class_="section-heading"),
        ui.tags.div(
            ui.output_data_frame("dig_interactions_by_month"),
            class_="carnegie-table-card",
        ),

        # Interactions by strategy & month pivot
        ui.tags.h2("Interactions by strategy & month", class_="section-heading"),
        ui.tags.div(
            ui.output_data_frame("dig_interactions_by_strategy_month"),
            class_="carnegie-table-card",
        ),
    ),
)


_dig_tab_interactions = ui.nav_panel(
    "Interactions",
    ui.tags.div(
        # Tab-specific filters
        ui.tags.div(
            ui.tags.div(
                ui.input_selectize(
                    "dig_interaction_cat", "Interaction Category",
                    choices=[], multiple=True,
                ),
                class_="inline-filter",
            ),
            ui.tags.div(
                ui.input_selectize(
                    "dig_conversion_name", "Paid Key Interaction",
                    choices=[], multiple=True,
                ),
                class_="inline-filter",
            ),
            class_="page-filter-bar",
            style="flex-wrap:wrap; gap:12px;",
        ),

        # Category KPI cards
        ui.tags.div(
            _dig_kpi_card("RFI / Lead Gen", "cat_rfi", "#EA332D"),
            _dig_kpi_card("Visit / Events", "cat_visit", "#021326"),
            _dig_kpi_card("Apply", "cat_apply", "#C99D44"),
            _dig_kpi_card("Enroll / Deposit", "cat_enroll", "#E8B9A4"),
            _dig_kpi_card("Other", "cat_other", "#8B1A1A"),
            class_="funnel-strip",
        ),

        # Category trending
        ui.tags.h2("Key interaction category trending", class_="section-heading"),
        ui.tags.div(
            ui.output_ui("dig_cat_trend_chart"),
            class_="chart-card",
        ),

        # Category × strategy bar
        ui.tags.h2("Key interactions by category & strategy", class_="section-heading"),
        ui.tags.div(
            ui.output_ui("dig_cat_strategy_chart"),
            class_="chart-card",
        ),

        # Tables
        ui.tags.h2("Breakdown by interaction category & name", class_="section-heading"),
        ui.tags.div(
            ui.output_data_frame("dig_interaction_breakdown_table"),
            class_="carnegie-table-card",
        ),

        ui.tags.h2("Key interactions by campaign name", class_="section-heading"),
        ui.tags.div(
            ui.output_data_frame("dig_interactions_campaign_table"),
            class_="carnegie-table-card",
        ),

        ui.tags.h2("Key interactions by month", class_="section-heading"),
        ui.tags.div(
            ui.output_data_frame("dig_interactions_month_table"),
            class_="carnegie-table-card",
        ),

        ui.tags.h2("Key interactions by campaign & interaction name", class_="section-heading"),
        ui.tags.div(
            ui.output_data_frame("dig_interactions_detail_table"),
            class_="carnegie-table-card",
        ),
    ),
)


_dig_tab_geography = ui.nav_panel(
    "Geography",
    ui.tags.div(
        ui.tags.div(
            ui.tags.span("Regional performance", class_="card-heading"),
            ui.tags.div(
                ui.input_radio_buttons(
                    "dig_geo_metric", None,
                    choices={
                        "impressions": "Impressions",
                        "clicks": "Clicks",
                        "total_conversions": "Total Conversions",
                    },
                    selected="impressions",
                    inline=True,
                ),
                class_="pill-toggle",
            ),
            class_="card-header-row",
        ),
        ui.tags.h2("Region performance", class_="section-heading"),
        ui.tags.div(
            ui.output_data_frame("dig_geo_table"),
            class_="carnegie-table-card",
        ),
    ),
)


_dig_tab_creative = ui.nav_panel(
    "Creative",
    ui.tags.div(
        ui.tags.div(
            ui.input_selectize(
                "dig_platform_campaign", "Platform Campaign",
                choices=[], multiple=True,
            ),
            class_="page-filter-bar",
        ),
        ui.output_ui("dig_creative_sections"),
    ),
)


_dig_tab_insights = ui.nav_panel(
    "Insights",
    ui.tags.div(
        # Tab-specific filters
        ui.tags.div(
            ui.tags.div(
                ui.input_switch("dig_milestone_only", "Milestones only", value=False),
                class_="inline-filter",
            ),
            ui.tags.div(
                ui.input_selectize(
                    "dig_note_type", "Note Type",
                    choices=["Performance", "Performance with Recommendation",
                             "Optimization", "Campaign Launch", "Budget", "Key Dates"],
                    multiple=True,
                ),
                class_="inline-filter",
            ),
            class_="page-filter-bar",
            style="flex-wrap:wrap; gap:12px;",
        ),

        ui.tags.h2("Performance insights & analysis", class_="section-heading"),
        ui.tags.div(
            ui.output_data_frame("dig_perf_notes_table"),
            class_="carnegie-table-card",
        ),

        ui.tags.h2("Campaign optimization history", class_="section-heading"),
        ui.tags.div(
            ui.output_data_frame("dig_optim_table"),
            class_="carnegie-table-card",
        ),
    ),
)


page_digital = ui.nav_panel(
    "Digital Performance",
    ui.tags.div(
        _digital_filters(),
        ui.navset_pill(
            _dig_tab_overview,
            _dig_tab_interactions,
            _dig_tab_geography,
            _dig_tab_creative,
            _dig_tab_insights,
            id="dig_tabs",
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
    page_programs,
    page_geography,
    page_digital,
    title=navbar_title,
    id="nav",
    header=[
        ui.head_content(
            ui.tags.link(rel="stylesheet", href="styles.css?v=16"),
            ui.tags.script(src="https://cdn.plot.ly/plotly-3.4.0.min.js"),
            ui.tags.script(
                "document.addEventListener('click',function(){"
                "document.querySelectorAll('.pill-dropdown-menu').forEach(function(m){"
                "m.style.display='none';});});"
            ),
        ),
        _sidebar_overlay(),
    ],
)

app = App(app_ui, server_logic, static_assets=str(Path(__file__).parent / "www"))
