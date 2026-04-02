# Carnegie ROI Dashboard

A modern, action-oriented enrollment analytics dashboard built in **Shiny for Python** for Carnegie Higher Ed. Designed to help university client managers quickly assess full-funnel performance, track progress to goal, and identify where to focus attention.

---

## Overview

This dashboard replaces a legacy Looker report with a decision-first experience — organized around the enrollment funnel, not around data tables. It covers:

- **ROI Overview** — At-a-glance funnel health with KPI scorecards and trend charts
- **Program Breakdown** — Performance by academic program
- **Lead Source** — Funnel metrics broken down by inquiry source
- **Funnel Geography** — Regional and state-level enrollment funnel maps
- **Digital Performance** — Paid media performance: spend, impressions, clicks, interactions, and creative detail

All pages follow Carnegie brand guidelines (colors, typography, spacing) and are optimized for 13–15 inch laptop screens.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | [Shiny for Python](https://shiny.posit.co/py/) |
| UI components | bslib / Bootstrap 5 |
| Charts | Plotly |
| Data | BigQuery (via CSV exports for current scope) |
| Fonts | Lora (headlines), Manrope (UI) |

---

## Project Structure

```
app/
  app.py              # Main Shiny app — UI layout and page structure
  server.py           # Reactive server logic for ROI/funnel pages
  digital_server.py   # Reactive server logic for Digital Performance pages
  data_loader.py      # Data loading and preprocessing
  digital_data.py     # Data loading for digital/media metrics
  metrics.py          # Metric definitions and KPI helpers
  formatters.py       # Number and label formatting utilities
  www/                # Static assets: CSS, JS, images, fonts

data/                 # Source data files (CSV exports from BigQuery)

doc/
  roi-dashboard-design.md    # Full product architecture and UX/UI rules
  roi-current-scope.md       # Current build scope and data constraints
  digital-architecture.md    # Digital Performance page architecture
  carnegie-brand.md          # Brand guidelines reference
  query-docs.md              # BigQuery query documentation
```

---

## Getting Started

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the app

```bash
shiny run app/app.py --reload
```

The app will be available at `http://localhost:8000`.

---

## Brand Guidelines

| Token | Value |
|-------|-------|
| Carnegie Red | `#EA332D` |
| Carnegie Blue | `#021326` |
| Off White | `#F8F4F0` |
| Carnegie Gold | `#C99D44` |

- Headlines: **Lora** (Thin / Light)
- UI & labels: **Manrope** (Regular / Medium)

Full reference: `doc/carnegie-brand.md`

---

## Data Notes

- Current data scope: Central Washington University
- Data is loaded from validated CSV exports in `data/`
- Digital Performance metrics require a live BigQuery connection (see `doc/digital-architecture.md`)
- Do not add or simulate metrics not listed in `doc/roi-current-scope.md`

---

## Contributing

1. Follow the coding and layout rules in `.claude/CLAUDE.md`
2. Read the relevant file fully before editing
3. One commit per completed task — no batched commits
4. Verify visual changes in the browser before marking a task done
5. Keep all dashboard copy in American English

---

*Built by Carnegie Higher Ed — Internal analytics tooling*
