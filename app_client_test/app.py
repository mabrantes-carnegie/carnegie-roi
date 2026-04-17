"""
Carnegie ROI — Client Parameterization Test App
================================================

PURPOSE:
    Isolated localhost app to validate the full sage_id → institution → data flow
    before applying client parameterization to the main internal dashboard.

    The main app (app/app.py) is NOT modified by this test path.

HOW TO RUN:
    cd app_client_test
    shiny run app.py --port 8000 --reload

HOW TO TEST:
    With URL param (production flow simulation):
        http://127.0.0.1:8000/?sage_id=CentralWA11686

    Without URL param (uses SAGE_ID env var or DEFAULT_SAGE_ID fallback):
        http://127.0.0.1:8000/
        SAGE_ID=CentralWA11686 shiny run app.py --port 8000

WHAT IT VALIDATES:
    1. sage_id is read correctly from the URL query parameter
    2. sage_id is mapped to institution_name via udp_udl.institution
    3. BigQuery queries run correctly with the parameterized institution_name
    4. The data returned matches the expected institution (not CWU hardcoded)
    5. Row counts and column shapes are correct for Q6, Q2, Q3
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from shiny import App, ui, render, reactive, req
from shiny.types import NavSetArg

from client_resolver import resolve_institution, list_known_institutions, DEFAULT_SAGE_ID
from data_loader_param import load_q6, load_q2, load_q3

import pandas as pd


# ── UI ─────────────────────────────────────────────────────────────────────────

app_ui = ui.page_fluid(
    ui.tags.head(
        ui.tags.style("""
            body { font-family: Manrope, sans-serif; background: #f8f4f0; color: #021326; }
            .status-ok  { color: #2d8a4e; font-weight: 600; }
            .status-err { color: #EA332D; font-weight: 600; }
            .status-loading { color: #c8962d; font-weight: 600; }
            .section-title { font-size: 13px; font-weight: 700; color: #4b5563;
                             text-transform: uppercase; letter-spacing: .05em;
                             margin: 1.5rem 0 .5rem; }
            .param-badge { display: inline-block; background: #021326; color: #fff;
                           font-size: 12px; padding: 2px 10px; border-radius: 20px;
                           font-family: monospace; margin: 0 4px; }
            table { border-collapse: collapse; width: 100%; font-size: 13px; }
            th { background: #021326; color: #fff; padding: 6px 12px; text-align: left; }
            td { padding: 5px 12px; border-bottom: 1px solid #e5e1dc; }
            tr:hover td { background: #f0ece8; }
            .card { background: #fff; border-radius: 8px; padding: 1.5rem;
                    box-shadow: 0 1px 4px rgba(2,19,38,.08); margin-bottom: 1rem; }
        """)
    ),

    ui.div(
        ui.tags.h1(
            "Carnegie ROI — Client Parameterization Test",
            style="font-size:20px;font-weight:300;font-family:Lora,serif;margin:0;"
        ),
        ui.tags.p(
            "This app validates the sage_id → institution → BigQuery flow. "
            "It does not affect the main internal dashboard.",
            style="font-size:13px;color:#6b7280;margin:.25rem 0 0;"
        ),
        style="padding:1.5rem 2rem 1rem;"
    ),

    ui.div(
        # ── Resolution status ──────────────────────────────────────────────────
        ui.div(
            ui.div("Resolution", class_="section-title"),
            ui.output_ui("resolution_status"),
            class_="card",
        ),

        # ── Data validation ────────────────────────────────────────────────────
        ui.div(
            ui.div("Data Validation — Q6 (Principal Funnel)", class_="section-title"),
            ui.output_ui("q6_status"),
            ui.output_table("q6_preview"),
            class_="card",
        ),

        ui.div(
            ui.div("Data Validation — Q2 (Campaign Cost)", class_="section-title"),
            ui.output_ui("q2_status"),
            ui.output_table("q2_preview"),
            class_="card",
        ),

        ui.div(
            ui.div("Data Validation — Q3 (Geography)", class_="section-title"),
            ui.output_ui("q3_status"),
            ui.output_table("q3_preview"),
            class_="card",
        ),

        # ── Known institutions reference ───────────────────────────────────────
        ui.div(
            ui.div("Known Institutions (sample from udp_udl.institution)", class_="section-title"),
            ui.output_table("known_institutions"),
            class_="card",
        ),

        style="padding:0 2rem 2rem;"
    ),
)


# ── Server ─────────────────────────────────────────────────────────────────────

def server(input, output, session):

    # ── Read sage_id from URL query params ─────────────────────────────────────
    @reactive.calc
    def sage_id() -> str:
        params = session.http_conn.query_params
        return params.get("sage_id", DEFAULT_SAGE_ID)

    # ── Resolve sage_id → institution_name via BigQuery ────────────────────────
    @reactive.calc
    def institution_name() -> str | None:
        sid = sage_id()
        return resolve_institution(sid)

    # ── Load Q6 for resolved institution ──────────────────────────────────────
    @reactive.calc
    def q6_data() -> pd.DataFrame | None:
        name = institution_name()
        req(name is not None)
        return load_q6(name)

    # ── Load Q2 for resolved institution ──────────────────────────────────────
    @reactive.calc
    def q2_data() -> pd.DataFrame | None:
        name = institution_name()
        req(name is not None)
        return load_q2(name)

    # ── Load Q3 for resolved institution ──────────────────────────────────────
    @reactive.calc
    def q3_data() -> pd.DataFrame | None:
        name = institution_name()
        req(name is not None)
        return load_q3(name)

    # ── Outputs ────────────────────────────────────────────────────────────────

    @render.ui
    def resolution_status():
        sid = sage_id()
        name = institution_name()
        if name:
            return ui.tags.div(
                ui.tags.p(
                    ui.tags.span("sage_id: ", style="color:#6b7280;"),
                    ui.tags.span(sid, class_="param-badge"),
                    ui.tags.span(" → ", style="color:#6b7280;margin:0 6px;"),
                    ui.tags.span("institution_name: ", style="color:#6b7280;"),
                    ui.tags.span(name, class_="param-badge"),
                ),
                ui.tags.p(
                    ui.tags.span("RESOLVED", class_="status-ok"),
                    " — institution name successfully mapped from udp_udl.institution",
                    style="font-size:13px;margin:0;"
                ),
                ui.tags.p(
                    ui.tags.span(
                        "Simulating production flow: MyCarnegie would send this sage_id "
                        "as a URL parameter (?sage_id=" + sid + ").",
                        style="font-size:12px;color:#9ca3af;"
                    )
                )
            )
        else:
            return ui.tags.div(
                ui.tags.p(
                    ui.tags.span("sage_id: ", style="color:#6b7280;"),
                    ui.tags.span(sid, class_="param-badge"),
                ),
                ui.tags.p(
                    ui.tags.span("NOT FOUND", class_="status-err"),
                    " — no institution matched this sage_id in udp_udl.institution.",
                    style="font-size:13px;margin:0;"
                ),
                ui.tags.p(
                    "Check the Known Institutions table below for valid sage_id values.",
                    style="font-size:12px;color:#9ca3af;"
                )
            )

    @render.ui
    def q6_status():
        df = q6_data()
        if df is None or len(df) == 0:
            return ui.tags.span("No data returned", class_="status-err")
        inst_vals = df["institution_name"].unique().tolist()
        return ui.tags.p(
            ui.tags.span(f"{len(df):,} rows loaded", class_="status-ok"),
            f" — institution_name in data: {inst_vals}",
            style="font-size:13px;margin:0 0 .5rem;"
        )

    @render.table
    def q6_preview():
        df = q6_data()
        req(df is not None and len(df) > 0)
        cols = ["institution_name", "term_year", "term_semester", "student_type",
                "event_year", "event_month", "total_inquiries", "total_app_starts",
                "total_deposits", "total_enrolled"]
        cols = [c for c in cols if c in df.columns]
        return df[cols].head(8)

    @render.ui
    def q2_status():
        df = q2_data()
        if df is None or len(df) == 0:
            return ui.tags.span("No data returned", class_="status-err")
        return ui.tags.p(
            ui.tags.span(f"{len(df):,} rows loaded", class_="status-ok"),
            f" — total_cost range: ${df['total_cost'].min():,.0f} – ${df['total_cost'].max():,.0f}",
            style="font-size:13px;margin:0 0 .5rem;"
        )

    @render.table
    def q2_preview():
        df = q2_data()
        req(df is not None and len(df) > 0)
        cols = ["institution_name", "term_year", "lead_source",
                "campaign_service", "total_cost", "total_enrolled"]
        cols = [c for c in cols if c in df.columns]
        return df[cols].head(8)

    @render.ui
    def q3_status():
        df = q3_data()
        if df is None or len(df) == 0:
            return ui.tags.span("No data returned", class_="status-err")
        return ui.tags.p(
            ui.tags.span(f"{len(df):,} rows loaded", class_="status-ok"),
            f" — {df['student_state'].nunique()} unique states",
            style="font-size:13px;margin:0 0 .5rem;"
        )

    @render.table
    def q3_preview():
        df = q3_data()
        req(df is not None and len(df) > 0)
        cols = ["institution_name", "student_state", "student_city",
                "term_year", "total_inquiries", "total_enrolled"]
        cols = [c for c in cols if c in df.columns]
        return df[cols].head(8)

    @render.table
    def known_institutions():
        rows = list_known_institutions(limit=20)
        return pd.DataFrame(rows)


app = App(app_ui, server)
