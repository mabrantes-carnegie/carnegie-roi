"""Carnegie ROI Dashboard — UI layout and app entry point."""

import sys
from pathlib import Path

# Ensure the app directory is on sys.path so local modules resolve
# both locally and on Posit Connect (which runs from the repo root).
sys.path.insert(0, str(Path(__file__).parent))


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
    ("Inquiries",    "total_inquiries",    "#EA332D"),
    ("App Starts",   "total_app_starts",   "#C99D44"),
    ("App Submits",  "total_app_submits",  "#021326"),
    ("Admits",       "total_admits",       "#EA332D"),
    ("Deposits",     "total_deposits",     "#C99D44"),
    ("Net Deposits", "total_net_deposits", "#021326"),
]

_COST_METRICS = [
    ("Cost/Inquiry", "cost_per_inquiry"),
    ("Cost/App Start", "cost_per_app_start"),
    ("Cost/App Submit", "cost_per_app_submit"),
    ("Cost/Admit", "cost_per_admit"),
    ("Cost/Deposit", "cost_per_deposit"),
]


def _funnel_kpi_card(label: str, key: str, border_color: str = "#EA332D"):
    """Compact funnel KPI card with value, YoY delta (inline), goal text, and progress bar."""
    return ui.tags.div(
        ui.tags.div(label, class_="funnel-label"),
        ui.tags.div(
            ui.tags.div(ui.output_text(f"kpi_{key}"), class_="funnel-value"),
            ui.output_ui(f"yoy_{key}"),
            class_="funnel-value-row",
        ),
        ui.output_ui(f"goal_text_{key}"),
        ui.output_ui(f"progress_{key}"),
        class_="funnel-card",
        style=f"border-top:3px solid {border_color};",
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
        # Section 1: Funnel health strip (6 cards)
        ui.tags.div(
            *[_funnel_kpi_card(label, key, color) for label, key, color in PRIMARY_FUNNEL],
            class_="funnel-strip",
        ),

        # Section 3a: Conversion Rates collapsible row
        ui.tags.div(
            ui.tags.button(
                ui.tags.span("Show Conversion Rates", class_="collapsible-btn-label"),
                ui.tags.span("\u203a", class_="collapsible-btn-chevron"),
                class_="collapsible-section-btn",
                onclick=(
                    "var row=document.getElementById('conv-rates-row');"
                    "var open=row.classList.contains('collapsible-row--open');"
                    "row.classList.toggle('collapsible-row--open',!open);"
                    "this.querySelector('.collapsible-btn-label').textContent=open?'Show Conversion Rates':'Hide Conversion Rates';"
                    "this.querySelector('.collapsible-btn-chevron').style.transform=open?'rotate(0deg)':'rotate(90deg)';"
                ),
            ),
            class_="collapsible-section-header",
        ),
        ui.tags.div(
            _secondary_badge("Admit Rate", "admitted_rate"),
            _secondary_badge("Yield Rate", "yield_rate"),
            ui.tags.div(
                ui.tags.div("Enrolled", class_="secondary-label"),
                ui.tags.div(ui.output_text("kpi_total_enrolled"), class_="secondary-value"),
                ui.output_ui("yoy_total_enrolled"),
                title="Students who completed enrollment. May differ from Net Deposits due to enrollment timing and process variations.",
                class_="secondary-badge",
            ),
            ui.output_ui("melt_rate_secondary"),
            id="conv-rates-row",
            class_="secondary-row collapsible-row",
        ),

        # Section 3b: Cost Metrics collapsible row
        ui.tags.div(
            ui.tags.button(
                ui.tags.span("Show Cost Metrics", class_="collapsible-btn-label"),
                ui.tags.span("\u203a", class_="collapsible-btn-chevron"),
                class_="collapsible-section-btn",
                onclick=(
                    "var row=document.getElementById('cost-metrics-row');"
                    "var open=row.classList.contains('collapsible-row--open');"
                    "row.classList.toggle('collapsible-row--open',!open);"
                    "this.querySelector('.collapsible-btn-label').textContent=open?'Show Cost Metrics':'Hide Cost Metrics';"
                    "this.querySelector('.collapsible-btn-chevron').style.transform=open?'rotate(0deg)':'rotate(90deg)';"
                ),
            ),
            class_="collapsible-section-header",
        ),
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
                                    "monthly": "Monthly",
                                    "yearly": "Yearly",
                                },
                                selected="monthly",
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
                    options={"placeholder": "All"},
                ),
                class_="inline-filter",
            ),
            class_="page-filter-bar",
        ),

        # Section 1: Funnel waterfall
        ui.tags.h2("Enrollment funnel", class_="section-heading"),
        ui.tags.div(
            ui.output_ui("funnel_waterfall"),
            class_="chart-card",
        ),

        # Section 2: Source performance table (full width)
        ui.tags.h2("Source performance", class_="section-heading"),
        ui.tags.div(
            ui.output_ui("source_table"),
            class_="carnegie-table-card",
        ),

        # Section 3: Source trend chart
        ui.tags.div(
            ui.tags.div(
                ui.tags.span("Source trend", class_="card-heading"),
                _pill_dropdown(
                    "source_trend_metric",
                    {
                        "total_inquiries":    "Inquiries",
                        "total_app_starts":   "App Starts",
                        "total_app_submits":  "App Submits",
                        "total_admits":       "Admits",
                        "total_deposits":     "Deposits",
                        "total_net_deposits": "Net Deposits",
                    },
                    "total_inquiries",
                ),
                class_="card-header-row",
            ),
            ui.output_ui("source_trend_chart"),
            class_="chart-card",
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


# --- Page 4: Geography ---

page_geography = ui.nav_panel(
    "Geography",
    ui.tags.div(
        ui.tags.div(
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
            ),
            ui.output_ui("geo_map_section"),
            ui.tags.p(
                "* \"Unknown\" represents students who did not fill in the State or City field in a form or registration.",
                style="text-align:right; font-size:0.75rem; color:#6B7280; margin:4px 0 0 0;",
            ),
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
            ui.output_ui("geo_detail_table"),
            class_="carnegie-table-card",
        ),
        style=_CW,
    ),
)


# --- Page 5: Digital Performance (5 sub-tabs) ---

_dig_min, _dig_max = get_digital_date_range()


def _month_options(min_dt, max_dt):
    """Return list of (value, label) for every month in [min_dt, max_dt]."""
    opts = []
    cur = min_dt.replace(day=1)
    end = max_dt.replace(day=1)
    while cur <= end:
        opts.append((cur.strftime("%Y-%m-%d"), cur.strftime("%b %Y")))
        # advance one month
        if cur.month == 12:
            cur = cur.replace(year=cur.year + 1, month=1)
        else:
            cur = cur.replace(month=cur.month + 1)
    return opts


def _programs_filters():
    """Filter bar for the Programs page."""
    import calendar
    today = date.today()
    data_max = _dig_max.date()
    # Default: Jul of prior year → latest available data month (capped at _dig_max)
    prog_start = date(today.year - 1, 7, 1)
    prog_end = date(data_max.year, data_max.month, 1)
    prog_start_val = prog_start.strftime("%Y-%m-%d")
    prog_end_val = prog_end.strftime("%Y-%m-%d")

    month_opts = _month_options(_dig_min.date(), _dig_max.date())

    def _month_select(select_id, default_val):
        options = [
            ui.tags.option(
                label,
                value=val,
                selected=(val == default_val),
            )
            for val, label in month_opts
        ]
        return ui.tags.div(
            ui.tags.select(
                *options,
                id=select_id,
                class_="ios-month-select",
                onchange=(
                    "var s=document.getElementById('prog_month_start').value;"
                    "var e=document.getElementById('prog_month_end').value;"
                    "var ep=e.split('-'); var ey=+ep[0]; var em=+ep[1];"
                    "var lastDay=new Date(ey, em, 0).getDate();"
                    "var endStr=ep[0]+'-'+ep[1]+'-'+lastDay.toString().padStart(2,'0');"
                    "Shiny.setInputValue('prog_period',[s, endStr],{priority:'event'});"
                ),
            ),
            class_="ios-month-wrap",
        )

    return ui.tags.div(
        ui.tags.div(
            ui.tags.span("Period", class_="ios-month-label"),
            ui.tags.div(
                _month_select("prog_month_start", prog_start_val),
                ui.tags.span("→", class_="ios-month-sep"),
                _month_select("prog_month_end", prog_end_val),
                class_="ios-month-row",
            ),
            class_="inline-filter ios-month-filter",
        ),
        ui.tags.div(
            ui.input_selectize(
                "program_name_filter", "Program",
                choices=[],
                multiple=True,
                options={"placeholder": "All"},
            ),
            class_="inline-filter",
        ),
        ui.tags.div(
            ui.input_selectize(
                "prog_student_type", "Student Type",
                choices=[],
                multiple=True,
                options={"placeholder": "All"},
            ),
            class_="inline-filter",
        ),
        ui.tags.div(
            ui.input_selectize(
                "prog_lead_source", "Lead Source",
                choices=[],
                multiple=True,
                options={"placeholder": "All"},
            ),
            class_="inline-filter",
        ),
        ui.tags.div(
            ui.input_date_range(
                "prog_period", None,
                start=prog_start,
                end=prog_end,
                min=_dig_min.date(),
                max=_dig_max.date(),
            ),
            style="display:none;",
        ),
        class_="page-filter-bar",
        style="flex-wrap:wrap; gap:12px;",
    )


page_programs = ui.nav_panel(
    "Programs",
    ui.tags.div(
        # Program filter bar
        _programs_filters(),
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
            ui.output_ui("program_detail_table"),
            class_="carnegie-table-card",
        ),
        style=_CW,
    ),
)


def _digital_filters():
    """Shared filter bar for digital performance page."""
    import calendar
    # Default: current month (latest available data month).
    data_max = _dig_max.date()
    curr_month_start = date(data_max.year, data_max.month, 1)
    curr_month_end = data_max.replace(
        day=calendar.monthrange(data_max.year, data_max.month)[1]
    )
    prev_month_start = curr_month_start
    # month_opts uses "%Y-%m-%d" (first day of month) as values
    prev_month_val = curr_month_start.strftime("%Y-%m-%d")
    prev_month_end = curr_month_end
    # End dropdown uses first-of-month value; JS converts to last day on the fly
    default_end_val = curr_month_start.strftime("%Y-%m-%d")

    month_opts = _month_options(_dig_min.date(), _dig_max.date())

    def _month_select(select_id, default_val):
        options = [
            ui.tags.option(
                label,
                value=val,
                selected=(val == default_val),
            )
            for val, label in month_opts
        ]
        return ui.tags.div(
            ui.tags.select(
                *options,
                id=select_id,
                class_="ios-month-select",
                onchange=(
                    "var s=document.getElementById('dig_month_start').value;"
                    "var e=document.getElementById('dig_month_end').value;"
                    "var ep=e.split('-'); var ey=+ep[0]; var em=+ep[1];"
                    "var lastDay=new Date(ey, em, 0).getDate();"
                    "var endStr=ep[0]+'-'+ep[1]+'-'+lastDay.toString().padStart(2,'0');"
                    "Shiny.setInputValue('dig_period',[s, endStr],{priority:'event'});"
                ),
            ),
            class_="ios-month-wrap",
        )

    return ui.tags.div(
        # Month range picker
        ui.tags.div(
            ui.tags.span("Period", class_="ios-month-label"),
            ui.tags.div(
                _month_select("dig_month_start", prev_month_val),
                ui.tags.span("→", class_="ios-month-sep"),
                _month_select("dig_month_end", default_end_val),
                class_="ios-month-row",
            ),
            class_="inline-filter ios-month-filter",
        ),
        ui.tags.div(
            ui.input_selectize(
                "dig_group", "Group",
                choices=get_digital_groups(),
                multiple=True,
                options={"placeholder": "All"},
            ),
            class_="inline-filter",
        ),
        ui.tags.div(
            ui.input_selectize(
                "dig_subgroup", "Subgroup",
                choices=get_digital_subgroups(),
                multiple=True,
                options={"placeholder": "All"},
            ),
            class_="inline-filter",
        ),
        ui.tags.div(
            ui.input_selectize(
                "dig_product", "Product",
                choices=get_digital_products(),
                multiple=True,
                options={"placeholder": "All"},
            ),
            class_="inline-filter",
        ),
        ui.tags.div(
            ui.input_selectize(
                "dig_campaign", "Campaign",
                choices=get_digital_campaigns(),
                multiple=True,
                options={"placeholder": "All"},
            ),
            class_="inline-filter",
        ),
        # Hidden date range input — gives Shiny a registered input with the correct default
        # value baked in at render time. The JS selects override it when the user changes months.
        ui.tags.div(
            ui.input_date_range(
                "dig_period", None,
                start=prev_month_start,
                end=prev_month_end,
                min=_dig_min.date(),
                max=_dig_max.date(),
            ),
            style="display:none;",
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
        ui.tags.div(
            ui.tags.div(ui.output_text(f"dig_{output_id}"), class_="secondary-value"),
            ui.output_ui(f"dig_{output_id}_delta"),
            class_="secondary-value-row",
        ),
        class_="secondary-badge dig-metric-badge",
    )


_dig_overview_content = ui.tags.div(
    # KPI strip
    ui.tags.div(
        _dig_kpi_card("Key Interactions", "key_interactions", "#EA332D"),
        _dig_kpi_card("Cost per Interaction", "cpi", "#021326"),
        _dig_kpi_card("Inquiry Interactions", "inquiry_int", "#C99D44"),
        _dig_kpi_card("Visit Interactions", "visit_int", "#E8B9A4"),
        _dig_kpi_card("Apply Interactions", "apply_int", "#8B1A1A"),
        class_="funnel-strip",
    ),
    # Row A: Trending + Key Interaction Categories
    ui.tags.div(
        ui.tags.div(
            ui.tags.span("Trending Performance", class_="card-heading"),
            ui.output_ui("dig_trending_chart"),
            class_="chart-card",
            style="flex:3;",
        ),
        ui.tags.div(
            ui.tags.span("Key Interaction Categories", class_="card-heading"),
            ui.output_ui("dig_key_interaction_categories"),
            class_="chart-card",
            style="flex:2;",
        ),
        class_="main-content-row",
    ),
    # Row B: Engagement & spend (narrow=42fr) + Cost Per Total Conversion (wide=58fr)
    ui.tags.div(
        ui.tags.div(
            ui.tags.span("Engagement & Spend", class_="card-heading"),
            ui.tags.div(
                _dig_metric_card("Budget", "budget"),
                _dig_metric_card("Cost per Click", "cpc"),
                _dig_metric_card("Direct Key Interactions", "direct_conv"),
                _dig_metric_card("Cost per Direct Key Int.", "cpdc"),
                _dig_metric_card("In-Platform Leads", "ipl"),
                _dig_metric_card("Cost per In-Plat. Lead", "cpipl"),
                _dig_metric_card("View-through Int.", "vtc"),
                _dig_metric_card("Cost per Total Key Int.", "cptc"),
                class_="dig-metric-grid",
            ),
            class_="chart-card",
        ),
        ui.tags.div(
            ui.tags.span("Cost Per Total Key Interaction", class_="card-heading"),
            ui.output_ui("dig_cost_per_total_conv"),
            class_="chart-card",
        ),
        class_="main-content-row",
        style="grid-template-columns: 42fr 58fr;",
    ),
    # Strategy section
    ui.tags.div(
        ui.tags.div(
            ui.tags.span("Performance By Strategy", class_="card-heading"),
            ui.output_ui("dig_strategy_bar"),
            class_="chart-card",
        ),
        ui.tags.div(
            ui.tags.span("Strategy Trend", class_="card-heading"),
            ui.output_ui("dig_strategy_trend"),
            class_="chart-card",
        ),
        class_="main-content-row",
        style="grid-template-columns: 42fr 58fr;",
    ),
    ui.tags.h2("Performance By Subgroup", class_="section-heading"),
    ui.tags.div(ui.output_ui("dig_subgroup_table"), class_="carnegie-table-card"),
    ui.tags.h2("Performance By Strategy", class_="section-heading"),
    ui.tags.div(ui.output_ui("dig_strategy_table"), class_="carnegie-table-card"),
    ui.tags.h2("Interactions By Month & Year", class_="section-heading"),
    ui.tags.div(ui.output_ui("dig_interactions_by_month"), class_="carnegie-table-card"),
    ui.tags.h2("Interactions By Strategy & Month", class_="section-heading"),
    ui.tags.div(ui.output_ui("dig_interactions_by_strategy_month"), class_="carnegie-table-card"),
)


def _dig_page(content_div):
    """Wrap a digital sub-page: content only (filters are rendered once globally)."""
    return ui.tags.div(
        content_div,
        style=_CW,
    )


# ── Overview YoY tab content (mirrors Overview, _yoy output IDs) ──────────
_dig_overview_yoy_content = ui.tags.div(
    ui.tags.div(
        _dig_kpi_card("Impressions", "impressions_yoy", "#EA332D"),
        _dig_kpi_card("Clicks", "clicks_yoy", "#021326"),
        _dig_kpi_card("CTR", "ctr_yoy", "#C99D44"),
        _dig_kpi_card("Total Key Interactions", "total_conv_yoy", "#021326"),
        _dig_kpi_card("Key Interaction Rate", "conv_rate_yoy", "#C99D44"),
        class_="funnel-strip",
    ),
    ui.tags.div(
        ui.tags.div(
            ui.tags.span("Trending Performance (YoY)", class_="card-heading"),
            ui.output_ui("dig_trending_chart_yoy"),
            class_="chart-card",
            style="flex:3;",
        ),
        ui.tags.div(
            ui.tags.span("Engagement & Spend", class_="card-heading"),
            ui.tags.div(
                _dig_metric_card("Budget", "budget_yoy"),
                _dig_metric_card("Cost per Click", "cpc_yoy"),
                _dig_metric_card("Direct Key Interactions", "direct_conv_yoy"),
                _dig_metric_card("Cost per Direct Key Int.", "cpdc_yoy"),
                _dig_metric_card("In-Platform Leads", "ipl_yoy"),
                _dig_metric_card("Cost per In-Plat. Lead", "cpipl_yoy"),
                _dig_metric_card("View-through Int.", "vtc_yoy"),
                _dig_metric_card("Cost per Total Key Int.", "cptc_yoy"),
                class_="dig-metric-grid",
            ),
            class_="chart-card",
            style="flex:2;",
        ),
        class_="main-content-row",
    ),
    ui.tags.div(
        ui.tags.div(
            ui.tags.span("Performance By Strategy", class_="card-heading"),
            ui.output_ui("dig_strategy_bar_yoy"),
            class_="chart-card",
            style="flex:1;",
        ),
        ui.tags.div(
            ui.tags.span("Strategy Trend", class_="card-heading"),
            ui.output_ui("dig_strategy_trend_yoy"),
            class_="chart-card",
            style="flex:1;",
        ),
        class_="main-content-row",
    ),
    ui.tags.h2("Performance By Subgroup", class_="section-heading"),
    ui.tags.div(
        ui.output_ui("dig_subgroup_table_yoy"),
        class_="carnegie-table-card",
    ),
    ui.tags.h2("Performance By Strategy", class_="section-heading"),
    ui.tags.div(
        ui.output_ui("dig_strategy_table_yoy"),
        class_="carnegie-table-card",
    ),
)


page_digital = ui.nav_menu(
    "Digital Performance",

    ui.nav_panel(
        "Overview",
        _dig_page(_dig_overview_content),
    ),

    ui.nav_panel(
        "Overview YoY",
        _dig_page(_dig_overview_yoy_content),
    ),

    ui.nav_panel(
        "Interactions",
        _dig_page(ui.tags.div(
            ui.tags.h2("Interaction Filters", class_="section-heading"),
            ui.tags.div(
                ui.tags.div(
                    ui.input_selectize(
                        "dig_interaction_cat", "Interaction Category",
                        choices=[], multiple=True,
                        options={"placeholder": "All"},
                    ),
                    class_="inline-filter",
                ),
                ui.tags.div(
                    ui.input_selectize(
                        "dig_conversion_name", "Paid Key Interaction",
                        choices=[], multiple=True,
                        options={"placeholder": "All"},
                    ),
                    class_="inline-filter",
                ),
                class_="page-filter-bar",
                style="flex-wrap:wrap; gap:12px;",
            ),
            ui.tags.div(
                _dig_kpi_card("RFI / Lead Gen", "cat_rfi", "#EA332D"),
                _dig_kpi_card("Visit / Events", "cat_visit", "#021326"),
                _dig_kpi_card("Apply", "cat_apply", "#C99D44"),
                _dig_kpi_card("Enroll / Deposit", "cat_enroll", "#E8B9A4"),
                _dig_kpi_card("Other", "cat_other", "#8B1A1A"),
                class_="funnel-strip",
            ),
            # Cost Metrics collapsible row
            ui.tags.div(
                ui.tags.button(
                    ui.tags.span("Show Cost Metrics", class_="collapsible-btn-label"),
                    ui.tags.span("\u203a", class_="collapsible-btn-chevron"),
                    class_="collapsible-section-btn",
                    onclick=(
                        "var row=document.getElementById('int-cost-metrics-row');"
                        "var open=row.classList.contains('collapsible-row--open');"
                        "row.classList.toggle('collapsible-row--open',!open);"
                        "this.querySelector('.collapsible-btn-label').textContent=open?'Show Cost Metrics':'Hide Cost Metrics';"
                        "this.querySelector('.collapsible-btn-chevron').style.transform=open?'rotate(0deg)':'rotate(90deg)';"
                    ),
                ),
                class_="collapsible-section-header",
            ),
            ui.output_ui("dig_int_cost_panel"),
            ui.tags.h2("Key Interaction Category Trending", class_="section-heading"),
            ui.tags.div(
                ui.tags.div(
                    ui.output_ui("dig_cat_trend_chart"),
                    class_="chart-card",
                    style="flex:3;",
                ),
                ui.tags.div(
                    ui.tags.span("Key Interaction Breakdown", class_="card-heading"),
                    ui.output_ui("dig_cat_breakdown_chart"),
                    class_="chart-card",
                    style="flex:2;",
                ),
                class_="main-content-row",
            ),
            ui.tags.div(
                ui.tags.div(
                    ui.tags.span("Key Interactions By Category & Strategy", class_="card-heading"),
                    ui.output_ui("dig_cat_strategy_chart"),
                    class_="chart-card",
                    style="flex:5;",
                ),
                ui.tags.div(
                    ui.tags.span("Breakdown By Interaction Category & Name", class_="card-heading"),
                    ui.output_ui("dig_interaction_breakdown_table"),
                    class_="carnegie-table-card",
                    style="flex:7;",
                ),
                class_="main-content-row",
            ),
            ui.tags.h2("Key Interactions By Campaign Name", class_="section-heading"),
            ui.tags.div(ui.output_ui("dig_interactions_campaign_table"), class_="carnegie-table-card"),
            ui.tags.h2("Key Interactions By Month", class_="section-heading"),
            ui.tags.div(ui.output_ui("dig_interactions_month_table"), class_="carnegie-table-card"),
            ui.tags.h2("Key Interactions By Campaign & Interaction Name", class_="section-heading"),
            ui.tags.div(ui.output_ui("dig_interactions_detail_table"), class_="carnegie-table-card"),
        )),
    ),

    ui.nav_panel(
        "Geography",
        _dig_page(ui.tags.div(
            ui.tags.div(
                ui.tags.div(
                    ui.output_ui("dig_geo_map_title"),
                    _pill_dropdown(
                        "dig_geo_metric",
                        {
                            "impressions": "Impressions",
                            "clicks": "Clicks",
                            "total_conversions": "Total Interactions",
                        },
                        "impressions",
                    ),
                    class_="card-header-row",
                ),
                ui.output_ui("dig_geo_map"),
                ui.tags.p(
                    "* \"Unknown\" indicates impressions or interactions where the ad platform could not determine the user's location.",
                    style="text-align:right; font-size:0.75rem; color:#6B7280; margin:4px 0 0 0;",
                ),
                class_="chart-card",
            ),
            ui.tags.h2("Region performance", class_="section-heading"),
            ui.tags.div(ui.output_ui("dig_geo_table"), class_="carnegie-table-card"),
        )),
    ),

    ui.nav_panel(
        "Creative",
        _dig_page(ui.tags.div(
            # ── Sub-page tab switcher ──
            ui.tags.div(
                ui.input_radio_buttons(
                    "crv_sub", None,
                    choices={
                        "display": "Display Creative",
                        "ppc": "PPC Keyword Performance",
                        "meta": "Meta Creative",
                        "linkedin": "LinkedIn Creative",
                        "youtube": "YouTube Creative",
                        "snapchat": "Snapchat Creative",
                        "tiktok": "TikTok Creative",
                        "spotify": "Spotify Creative",
                        "reddit": "Reddit Creative",
                    },
                    selected="display",
                    inline=True,
                ),
                class_="insight-segmented",
            ),
            # ── KPI summary strip ──
            ui.tags.div(
                _dig_kpi_card("Total Creatives", "crv_total", "#EA332D"),
                _dig_kpi_card("Impressions", "crv_impressions", "#021326"),
                _dig_kpi_card("Avg. CTR", "crv_ctr", "#C99D44"),
                _dig_kpi_card("Total Interactions", "crv_conversions", "#021326"),
                class_="funnel-strip",
            ),
            # ── Page-specific filters ──
            ui.tags.div(
                ui.tags.div(
                    ui.input_text(
                        "crv_search", "Search",
                        placeholder="Search using keywords",
                    ),
                    class_="inline-filter",
                ),
                ui.tags.div(
                    ui.output_ui("crv_search_count"),
                    style="align-self:flex-end; padding-bottom:10px;",
                ),
                class_="page-filter-bar",
                style="flex-wrap:wrap; gap:12px; align-items:flex-start;",
            ),
            # ── Sort by row ──
            ui.tags.div(
                # Hidden Shiny input to hold sort value
                ui.tags.div(
                    ui.input_radio_buttons(
                        "crv_sort", None,
                        choices={
                            "impressions": "Impressions",
                            "clicks": "Clicks",
                            "ctr": "CTR",
                            "total_conversions": "Interactions",
                            "conv_rate": "Int. Rate",
                        },
                        selected="impressions",
                        inline=True,
                    ),
                    style="display:none;",
                ),
                # Visible pill toolbar
                ui.tags.span("SORT BY", class_="crv-sort-label"),
                ui.tags.div(
                    ui.tags.button("Impressions", class_="crv-sort-pill active",
                                   **{"data-val": "impressions"},
                                   onclick="window._crvSort(this)"),
                    ui.tags.button("Clicks", class_="crv-sort-pill",
                                   **{"data-val": "clicks"},
                                   onclick="window._crvSort(this)"),
                    ui.tags.button("CTR", class_="crv-sort-pill",
                                   **{"data-val": "ctr"},
                                   onclick="window._crvSort(this)"),
                    ui.tags.button("Interactions", class_="crv-sort-pill",
                                   **{"data-val": "total_conversions"},
                                   onclick="window._crvSort(this)"),
                    ui.tags.button("Int. Rate", class_="crv-sort-pill",
                                   **{"data-val": "conv_rate"},
                                   onclick="window._crvSort(this)"),
                    class_="crv-sort-pills",
                ),
                class_="crv-sort-bar",
            ),
            ui.tags.script(
                "window._crvSort=function(btn){"
                "  var pills=btn.parentElement.querySelectorAll('.crv-sort-pill');"
                "  var val=btn.getAttribute('data-val');"
                "  var cur=document.querySelector('.crv-sort-pill.active');"
                "  if(cur&&cur.getAttribute('data-val')===val){"
                "    var asc=btn.classList.contains('asc');"
                "    pills.forEach(function(p){p.classList.remove('active','asc');});"
                "    btn.classList.add('active');"
                "    if(!asc){btn.classList.add('asc');}"
                "  }else{"
                "    pills.forEach(function(p){p.classList.remove('active','asc');});"
                "    btn.classList.add('active');"
                "  }"
                "  var dir=btn.classList.contains('asc')?'__asc':'';"
                "  Shiny.setInputValue('crv_sort',val+dir);"
                "};"
                "window._crvToggle=function(id,btn){"
                "  var panel=document.getElementById(id);"
                "  if(!panel)return;"
                "  var open=panel.style.display!=='none';"
                "  panel.style.display=open?'none':'flex';"
                "  var lbl=btn.querySelector('.crv-toggle-label');"
                "  var chev=btn.querySelector('.crv-toggle-chevron');"
                "  if(lbl)lbl.textContent=open?'Details':'Close';"
                "  if(chev){chev.textContent=open?'\\u25BE':'\\u25B4';}"
                "  btn.classList.toggle('crv-details-btn--open',!open);"
                "  btn.closest('.crv-card').classList.toggle('crv-card--expanded',!open);"
                "};"
            ),
            # ── Creative card / table list (dynamic based on sub-page) ──
            ui.output_ui("crv_card_list"),
            # ── Pagination ──
            ui.tags.div(
                ui.tags.div(
                    ui.tags.label("Cards per page", class_="insight-pag-label"),
                    ui.tags.select(
                        ui.tags.option("10", value="10", selected="selected"),
                        ui.tags.option("25", value="25"),
                        ui.tags.option("50", value="50"),
                        class_="insight-pag-select",
                        id="crv_per_page",
                        onchange=(
                            "Shiny.setInputValue('crv_per_page', parseInt(this.value));"
                            "Shiny.setInputValue('crv_page', 1);"
                        ),
                    ),
                    class_="insight-pag-group",
                ),
                ui.tags.div(
                    ui.output_ui("crv_pag_range"),
                    class_="insight-pag-range",
                ),
                ui.tags.div(
                    ui.output_ui("crv_pag_buttons"),
                    class_="insight-pag-nav",
                ),
                class_="insight-pag-bar",
            ),
            # Initialize pagination inputs on first render
            ui.tags.script(
                "$(function(){"
                "  Shiny.setInputValue('crv_page', 1);"
                "  Shiny.setInputValue('crv_per_page', 10);"
                "});"
            ),
        )),
    ),

    ui.nav_panel(
        "Insights",
        _dig_page(ui.tags.div(
            # ── Segmented view switcher ──
            ui.tags.div(
                ui.input_radio_buttons(
                    "insights_view", None,
                    choices={
                        "performance": "Performance Insights & Analysis",
                        "optimization": "Campaign Optimization History",
                    },
                    selected="performance",
                    inline=True,
                ),
                class_="insight-segmented",
            ),
            # ── Shared filters ──
            ui.tags.div(
                ui.tags.div(
                    ui.input_switch("dig_milestone_only", "Milestones only", value=False),
                    class_="inline-filter",
                    style="padding-top:28px;",
                ),
                ui.tags.div(
                    ui.input_selectize(
                        "dig_note_type", "Note Type",
                        choices=["Performance", "Performance with Recommendation",
                                 "Optimization", "Campaign Launch", "Budget", "Key Dates"],
                        multiple=True,
                        options={"placeholder": "All"},
                    ),
                    class_="inline-filter",
                ),
                ui.tags.div(
                    ui.input_text(
                        "insights_search", "Search",
                        placeholder="Search using keywords",
                    ),
                    class_="inline-filter",
                ),
                ui.tags.div(
                    ui.output_ui("insights_search_count"),
                    style="align-self:flex-end; padding-bottom:10px;",
                ),
                class_="page-filter-bar",
                style="flex-wrap:wrap; gap:12px; align-items:flex-start;",
            ),
            # ── Card list ──
            ui.output_ui("insights_card_list"),
            # ── Pagination ──
            ui.tags.div(
                ui.tags.div(
                    ui.tags.label("Cards per page", class_="insight-pag-label"),
                    ui.tags.select(
                        ui.tags.option("10", value="10", selected="selected"),
                        ui.tags.option("25", value="25"),
                        ui.tags.option("50", value="50"),
                        class_="insight-pag-select",
                        id="insights_per_page",
                        onchange=(
                            "Shiny.setInputValue('insights_per_page', parseInt(this.value));"
                            "Shiny.setInputValue('insights_page', 1);"
                        ),
                    ),
                    class_="insight-pag-group",
                ),
                ui.tags.div(
                    ui.output_ui("insights_pag_range"),
                    class_="insight-pag-range",
                ),
                ui.tags.div(
                    ui.output_ui("insights_pag_buttons"),
                    class_="insight-pag-nav",
                ),
                class_="insight-pag-bar",
            ),
            # Initialize pagination inputs on first render
            ui.tags.script(
                "$(function(){"
                "  Shiny.setInputValue('insights_page', 1);"
                "  Shiny.setInputValue('insights_per_page', 10);"
                "});"
            ),
        )),
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
    ui.tags.span("ROI Report - Central Washington University", class_="navbar-title-text"),
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
            ui.tags.link(rel="stylesheet", href="styles.css?v=42"),
            ui.tags.script(src="https://cdn.plot.ly/plotly-3.4.0.min.js"),
            ui.tags.script(src="sortable-tables.js"),
            ui.tags.script(src="paginated-tables.js?v=2"),
            ui.tags.script(
                "document.addEventListener('click',function(){"
                "document.querySelectorAll('.pill-dropdown-menu').forEach(function(m){"
                "m.style.display='none';});});"
            ),
            # Show/hide digital filters based on active tab (uses Shiny nav input)
            ui.tags.script("""
(function() {
  var DIG_TABS  = ['Overview','Overview YoY','Interactions','Geography','Creative','Insights'];
  // Tabs that default to academic-year start → current month
  var ACAD_TABS = ['Overview YoY', 'Geography', 'Creative'];

  // Helper: get the last available month option value from the end dropdown
  // (this is the latest month with data, e.g. "2026-03-01")
  function _lastDataMonth() {
    var me = document.getElementById('dig_month_end');
    if (me && me.options.length > 0) return me.options[me.options.length - 1].value;
    return null;
  }

  // Helper: compute last day of a "YYYY-MM-DD" first-of-month string
  function _lastDayOf(sel) {
    var p = sel.split('-'); var ey = +p[0]; var em = +p[1];
    var ld = new Date(ey, em, 0).getDate();
    return p[0] + '-' + p[1] + '-' + String(ld).padStart(2, '0');
  }

  // Data-month range: both start and end = last available data month
  // Used for Overview & Interactions
  function _dataMonthRange() {
    var sel = _lastDataMonth();
    if (!sel) return null;
    return {start: sel, end: _lastDayOf(sel), startSel: sel, endSel: sel};
  }

  // Academic-year range: Jul of current AY → last data month
  // Used for Overview YoY, Geography, Creative
  function _acadRange() {
    var sel = _lastDataMonth();
    if (!sel) return null;
    var p = sel.split('-'); var ey = +p[0]; var em = +p[1]; // 1-based month
    var ayStartYear = (em >= 7) ? ey : ey - 1;
    var startStr = ayStartYear + '-07-01';
    return {start: startStr, end: _lastDayOf(sel), startSel: startStr, endSel: sel};
  }

  // Insights default: Jul of current AY → last data month (if AY 2025-26),
  // or Jul AY-start → Jun AY-end for subsequent academic years.
  function _insightsAcadRange() {
    var sel = _lastDataMonth();
    if (!sel) return null;
    var p = sel.split('-'); var ey = +p[0]; var em = +p[1]; // 1-based month
    var ayStartYear = (em >= 7) ? ey : ey - 1;
    var startStr = ayStartYear + '-07-01';
    var endStr, endSel;
    if (ayStartYear === 2025) {
      endStr = _lastDayOf(sel);
      endSel = sel;
    } else {
      var endYear = ayStartYear + 1;
      endStr = endYear + '-06-30';
      endSel = endYear + '-06-01';
    }
    return {start: startStr, end: endStr, startSel: startStr, endSel: endSel};
  }

  function _setDigPeriod(startStr, endStr, startSel, endSel) {
    // Update the visible month dropdowns IMMEDIATELY (prevents flash)
    var ms = document.getElementById('dig_month_start');
    var me = document.getElementById('dig_month_end');
    if (ms) ms.value = startSel;
    if (me) me.value = endSel;
    // Defer Shiny input update to next tick
    setTimeout(function() {
      Shiny.setInputValue('dig_period', [startStr, endStr], {priority:'event'});
    }, 50);
  }

  var _prevTab = null;

  // Show/hide the digital filter bar (no period change)
  function _showHideBar(tabVal) {
    var bar = document.getElementById('dig-global-filters');
    if (bar) bar.style.display = DIG_TABS.indexOf(tabVal) !== -1 ? '' : 'none';
  }

  // Adjust period defaults when switching between Digital sub-tabs
  function updateDigFilters(tabVal) {
    _showHideBar(tabVal);

    // Only adjust period on actual tab switches (not initial load)
    if (_prevTab === null) { _prevTab = tabVal; return; }
    if (_prevTab === tabVal) return;

    var r;

    if (ACAD_TABS.indexOf(tabVal) !== -1) {
      // → Overview YoY / Geography / Creative: AY start → last data month
      r = _acadRange();
      if (r) _setDigPeriod(r.start, r.end, r.startSel, r.endSel);
    } else if (tabVal === 'Insights') {
      // → Insights: own academic-year rule
      r = _insightsAcadRange();
      if (r) _setDigPeriod(r.start, r.end, r.startSel, r.endSel);
    } else if (tabVal === 'Overview' || tabVal === 'Interactions') {
      // → Overview / Interactions: always reset to last data month
      r = _dataMonthRange();
      if (r) _setDigPeriod(r.start, r.end, r.startSel, r.endSel);
    }
    _prevTab = tabVal;
  }

  $(document).on('shiny:inputchanged', function(e) {
    if (e.name === 'nav') updateDigFilters(e.value);
  });
  // On initial connection: only show/hide bar + record tab, let Python default handle period
  $(document).on('shiny:connected', function() {
    try {
      var val = Shiny.shinyapp.$inputValues ? Shiny.shinyapp.$inputValues['nav'] : '';
      val = val || '';
      _showHideBar(val);
      _prevTab = val;
    } catch(err) {}
  });
})();
"""),
        ),
        _sidebar_overlay(),
        # Digital filters rendered once globally
        ui.tags.div(
            _digital_filters(),
            id="dig-global-filters",
            style="display:none;",
        ),
    ],
)

app = App(app_ui, server_logic, static_assets=str(Path(__file__).parent / "www"))
