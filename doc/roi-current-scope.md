# ROI Dashboard — Current Build Scope

Last updated: March 2026

This document defines what is IN SCOPE for the current build.
Do not build beyond what is specified here.
Consult `roi-dashboard-design.md` for full product architecture and UX/UI rules.

---

## Pages to Build Now (Production-Ready)

| # | Page | Status |
|---|------|--------|
| 1 | **ROI Overview** | Build now |
| 2 | **Funnel Deep Dive** | Build now |
| 3 | **Geography** | Build now |
| 4 | **Digital Performance** | Placeholder only — data source pending |

### Digital Performance Constraint

Digital Performance is a future-phase dependency.
The navbar item must remain visible (it is part of the fixed Carnegie navbar), but the page itself should be:
- a placeholder stub, or
- clearly labeled "Coming soon — data source pending"

Do NOT fabricate or simulate these metrics until source data is validated:
- Impressions, Clicks, Key Interactions, Spend
- CPM, CPC, Cost per Key Interaction
- Product / Channel trend views
- Interaction category breakdown
- Paid key interaction detail
- Campaign detail, Optimization notes, Creative performance

---

## Available Data Sources

Build only from currently validated data:

| Data | Available | Use for |
|------|-----------|---------|
| Funnel / enrollment data | Yes | KPI strip, trending, funnel waterfall, source table |
| Source data | Yes | Source performance, source trend, conversion by source |
| Program data | Yes | Program ranked view, program detail table |
| Geography data (state/city) | Yes | Choropleth map, state ranked table |
| Institution-level funnel goals | Yes | Progress to goal bars on ROI Overview |
| Cost / spend data | Yes | Cost per funnel stage metrics (secondary KPIs) |
| Digital campaign data | No | Blocked — do not build production views |

---

## Goal Data Rules

CWU has institution-level funnel goals for:
- Inquiry Goal
- App Starts Goal
- App Submit Goal
- Admit Goal
- Deposit Goal
- Net Deposit Goal

Rules:
- Apply these as **CWU institution-level targets** only
- Do NOT treat them as program-specific goals
- Do NOT infer or split goal values by program, source, or geography
- Progress to goal should appear on ROI Overview only

---

## Core Funnel Metrics (Non-Negotiable)

Primary (always visible in KPI strip):
- Inquiries
- App Starts
- App Submits
- Admits
- Deposits
- Net Deposits

Secondary (smaller badges below KPI strip):
- Admit Rate (Admits ÷ App Submits)
- Yield Rate (Net Deposits ÷ Admits)
- Cost per Net Deposit (if cost data is available)

Rules:
- "Enrolled" is NOT a primary KPI unless confirmed as materially different from Net Deposits
- Cost metrics use Carnegie campaign spend ÷ full funnel volume — add a tooltip: "Cost metrics reflect Carnegie campaign spend divided by total funnel volume"
- YoY deltas: show as "▲ X% vs. PY" or "▼ X% vs. PY", whole percentages, green/red

---

## Navbar (Fixed — Do Not Modify)

The navbar is already implemented and follows Carnegie brand standard:
- "CARNEGIE" logo (Lora, uppercase, letter-spaced) left
- "ROI Report" (Carnegie Red accent) next to logo
- Page links right-aligned, uppercase: ROI OVERVIEW | FUNNEL DEEP DIVE | DIGITAL PERFORMANCE | GEOGRAPHY

Do not change the navbar in any way.

---

## Global Filters (Sidebar — All Pages)

| Filter | Type | Default |
|--------|------|---------|
| Institution | Single-select | Central Washington University |
| Term Year | Single-select | Current year |
| Term Semester | Single-select / radio | Current term |
| Student Type | Multi-select | All |
| Include International | Toggle | On |

These filters persist across all pages via the shared sidebar.

---

## Page-Specific Filters

| Page | Filter | Placement |
|------|--------|-----------|
| Funnel Deep Dive | Source | Inline filter bar |
| Funnel Deep Dive | Campaign Service | Advanced (collapsed) |
| Funnel Deep Dive | App Round | Advanced (collapsed) |
| Geography | Program Name | Inline filter bar (Programs tab) |
| Geography | Program Level | Secondary (Programs tab) |
| Geography | State | Inline / map-driven (Geographic tab) |
| Geography | Source | Advanced (collapsed) |

---

## Trending / Date Logic

Use validated monthly date fields by funnel stage where available.
- Trending chart on ROI Overview: monthly line chart, current cycle vs. prior year
- If stage-specific date fields exist (inquiry_date, app_start_date, admit_date, etc.), use the appropriate date for each stage
- If only a single date field exists, document the limitation and use it consistently

---

## What NOT to Do in This Phase

- Do not build Digital Performance as a real analytical page
- Do not invent metrics not supported by available data
- Do not split goals by program or source
- Do not re-argue the full product architecture — it is documented in `roi-dashboard-design.md`
- Do not propose a new information architecture unless a structural conflict is found
- Do not change the navbar