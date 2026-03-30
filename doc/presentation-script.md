# ROI Report — Presentation Script
**Central Washington University | Digital Performance Team**
*30-minute session · March 2026*

---

## Timing Guide

> **Context:** Mish is joining today and has never seen the dashboard before, so spend more time on the first pages. Don't worry about covering everything — we can share the link with the team after the meeting so they can explore on their own.

| Section | Suggested Time |
|---|---|
| Opening + navigation overview | ~2 min |
| ROI Overview | ~7 min |
| Funnel Deep Dive | ~5 min |
| Programs *(new)* | ~4 min |
| Geography | ~2 min |
| Digital Performance — all tabs | ~8 min total |
| Buffer / Q&A | ~2 min |

---

## Opening (~2 min)

*"This is the ROI Report for Central Washington University — it's a live dashboard that gives us a complete picture of both the enrollment funnel and the digital media performance in one place. The report title in the nav bar is 'ROI Report - Central Washington University.'"*

*"There are two main sections: the enrollment funnel side — ROI Overview, Funnel Deep Dive, Programs, and Geography — and then the Digital Performance section with six sub-pages. Let me walk you through each one."*

### Dashboard Structure

| Section | Pages |
|---|---|
| **Enrollment Funnel** | ROI Overview · Funnel Deep Dive · Programs · Geography |
| **Digital Performance** | Overview · Overview YoY · Interactions · Geography · Creative · Insights |

---

## Global Filters (Sidebar)

*"Before we dive in — there's a filter sidebar accessible from the hamburger icon in the top-left. These global filters apply to all enrollment funnel pages."*

| Filter | Default | Description |
|---|---|---|
| **Institution** | Central Washington University | Institution selector |
| **Term Year** | 2026 | The enrollment cycle (2026 = Fall 2026) |
| **Term Semester** | Fall | Fall / Spring / Summer |
| **Student Type** | All | First Year, Transfer, Graduate, etc. — multi-select |
| **Include International** | ON | Toggle to exclude international students |

> **Year-over-Year comparison rule (all funnel pages):** The current year is the selected Term Year (e.g., Fall 2026); the prior year is always Term Year − 1 (Fall 2025). Both years are **capped at the same academic calendar month** — for example, if today is March, both years show data only through March. This ensures a fair apples-to-apples comparison.

---

## 1 · ROI Overview (~7 min)

*"This is the main page of the report — the executive summary of the entire enrollment funnel. Everything here is based on CWU's data from the Slate enrollment system, validated to match the Slate dashboard 100%."*

### KPI Strip (6 primary cards)

**Inquiries → App Starts → App Submits → Admits → Deposits → Net Deposits**

Each card shows:
- **Current value** for the selected term year
- **YoY badge** (▲/▼ vs. the same period last year)
- **Goal text** (e.g., "Goal: 28,000 · 90%")
- **Progress bar** color-coded by status:
  - 🟢 Green ≥ 95% of goal
  - 🟡 Amber 80–94%
  - 🔴 Red < 80%

> **What is "Net Deposits"?** Net Deposits = Deposits minus students who withdrew after depositing (exits after deposit). It is the cleanest signal for students who are actually going to enroll.

### Collapsible Rows

**"Show Conversion Rates"** (click to expand):

| Metric | Formula |
|---|---|
| **Admit Rate** | Admits ÷ App Submits × 100 |
| **Yield Rate** | Net Deposits ÷ Admits × 100 |
| **Enrolled** | Students who completed enrollment *(may differ slightly from Net Deposits due to enrollment timing)* |
| **Melt Rate** | (1 − Net Deposits ÷ Deposits) × 100 — % of deposited students who withdrew before enrolling. Green < 3%, amber 3–5%, red > 5% |

**"Show Cost Metrics"** (click to expand):

| Metric | Formula |
|---|---|
| Cost/Net Deposit | Carnegie campaign spend ÷ Net Deposits |
| Cost/Inquiry | Carnegie campaign spend ÷ Inquiries |
| Cost/App Start | Carnegie campaign spend ÷ App Starts |
| Cost/App Submit | Carnegie campaign spend ÷ App Submits |
| Cost/Admit | Carnegie campaign spend ÷ Admits |
| Cost/Deposit | Carnegie campaign spend ÷ Deposits |

> **Important note on cost metrics:** These use Carnegie campaign spend only (from the `campaign_roi` table). The YoY badge is inverted — cost going **down** is green (better efficiency), cost going **up** is red.

### Trending Performance (chart)

Metric selector: Inquiries / App Starts / App Submits / Admits / Deposits / Net Deposits

**Monthly mode (default):**
- Red line = current year (cumulative by academic month, Jul → current month)
- Gold dashed line = prior year (same period)
- Light gray dotted line = 3-month rolling average for the current year
- X-axis in academic order: Jul, Aug, Sep, Oct, Nov, Dec, Jan, Feb, Mar, Apr, May, Jun

**Yearly mode:**
- Bar chart with one bar per year, YoY % annotations between each pair

### Funnel at a Glance (SVG visual)

A funnel diagram where each stage's width is proportional to its volume. Each stage shows a YoY badge on the right. The Melt Rate is shown below the Net Deposits stage.

> **Progress bar coloring:** Green ≥ 95% of goal · Amber 80–94% · Red < 80%. The goal values are currently placeholders — real CWU goals need to be confirmed by the team and will eventually be entered directly in Tinman.

---

## 2 · Funnel Deep Dive (~5 min)

*"This page lets you dig into the funnel by lead source — where students are actually coming from."*

### Page-Level Filter

**Lead Source** (multi-select): filters by `origin_source_first` from the Slate data.
- This is the **first-touch origin** of the student in Slate — e.g., College Fair, College Board, CWU CIHS, RFI Forms, Campus Event.
- This is **different from Carnegie campaign attribution** (Display, Paid Search, etc.) — those are used only for cost calculations.

### Enrollment Funnel (grouped bar chart)

- Grouped bars: prior year (light pink) vs. current year (red) for each funnel stage
- YoY % badge above each group
- **Chart note at the bottom:** *"Same period compared: Jul – [current month] | 2024-25 vs 2025-26"*
  - This tells you exactly which months are being compared. Both years run from July through the current month — same-period comparison.

### Source Performance (heatmap table)

Grouped by `origin_source_first`. Columns:

| Column | Formula |
|---|---|
| Inquiries | Count |
| % Inquiries | Source's share of total inquiries |
| App Starts | Count |
| % App Starts | Source's share of total app starts |
| **Start Rate** | App Starts ÷ Inquiries — how well does a source convert to applications? |
| App Submits, % App Submits | — |
| **Submit Rate** | App Submits ÷ App Starts |
| Enrolled, % Enrolled | — |
| **Inq→Enroll Rate** | Enrolled ÷ Inquiries — end-to-end funnel efficiency per source |
| Deposits, Net Deposits | — |

### Source Trend (chart)

Metric selector. Cumulative volume by month for each lead source in the selected year.

### Conversion Rates by Source (chart)

Admit rate and yield rate broken down by lead source — identifies which sources deliver the highest-quality students down the funnel.

---

## 3 · Programs ✨ *New*  (~4 min)

*"This is one of the new pages we built. It breaks down the enrollment funnel by program name — so you can see which programs are growing, which ones have a goal gap, and how each one is pacing through the academic year."*

### Page-Level Filters

| Filter | Default | Notes |
|---|---|---|
| **Period** | July of prior year → current month | Jul 2025 → Mar 2026 |
| **Program** | All | Multi-select; null/blank programs are excluded from this list |
| **Student Type** | All | Independent of the global sidebar filter |
| **Lead Source** | All | Independent of the global sidebar filter |

### Program Trending vs. Goal (line chart)

Metric selector: Inquiries, App Starts, App Submits, Deposits, Net Deposits

- Red line = current academic year (cumulative by month, Jul → current month)
- Gold dashed line = prior year (**full 12 months — not truncated**)
- Horizontal goal line (when available)

> ⚠️ **Important rule about the Period filter on this page:** The Period filter **does** affect the Top Programs ranking chart and the Program Detail table. However, it **does NOT affect** the "Program Trending vs. Goal" chart. That chart always shows the full academic year regardless of the period selected — this is intentional, so you always see the complete prior-year rhythm for seasonality comparison.

> ⚠️ **Note on totals:** Students who inquired but never applied have no program name on record. They are included in this chart's totals (so the numbers match the ROI Overview) but they do not appear in the Program filter dropdown.

### Top Programs (horizontal bar chart)

Ranking of programs by the selected metric volume. This chart **is** filtered by the Period selector.

> **Note on double-counting by program:** A student who applied to 2 programs is counted in both programs when we group by program name. This is correct for program-level ranking — it reflects the demand for each program. However, it means the sum across all programs will be higher than the institutional total. For this reason, there is no "Total" row on this page.

### Program Detail (heatmap table)

Full table with all programs: Inquiries, App Starts, App Submits, Admits, Deposits, Net Deposits. Heatmap coloring by volume intensity.

---

## 4 · Geography (~2 min)

*"The Geography page shows where students are coming from geographically — by home state."*

### Map

US choropleth. Metric selector: Inquiries / App Submits / Admits / Net Deposits.

> **Map note:** *"'Unknown' represents students who did not fill in the State or City field in a form or registration."* There are approximately 4,950 inquiry records with no state on file — these are labeled "Unknown" and not plotted on the map.

### State / City Detail (table)

- **"Include international & unknown" toggle** (default: OFF) — turn on to see international students and the unknown-state group
- Drill-down by state → city
- City-level data comes from a separate query (address table join) — it is the only data source that has city-level detail

---

---

# Digital Performance ✨ *All New*  (~8 min total)

*"Everything from here is brand new since last week. I'll walk through each tab at a high level — and we'll share the link after the meeting so you can explore each one in more detail on your own."*

## Digital Filters (shared bar at the top of all Digital pages)

| Filter | Default | Description |
|---|---|---|
| **Period** | Previous month (1st → last day) | Month-range selector: start month → end month |
| **Group** | All | `campaign_group_name` — top-level grouping |
| **Subgroup** | All | `campaign_subgroup_name` — mid-level grouping |
| **Product** | All | `product_name` — strategy (e.g., Display, Meta, PPC) |
| **Campaign** | All | Individual campaign |

> **Default period:** Previous complete month. Example: if today is March 26, 2026, the default is Feb 1 – Feb 28, 2026.

> **Comparison logic for digital metrics (Overview tab):** Each metric badge compares the selected period against the **same period in the prior year** (e.g., Feb 2026 vs. Feb 2025). The badge shows ▲/▼ %.

---

## 5 · Digital — Overview ✨ (~3 min)

*"This is the main digital dashboard — a summary of campaign performance for the selected period."*

**Data source:** Q8 — `tinman.v_kpi_campaign` (grain: client × group × subgroup × product × campaign × day)

### KPI Strip (5 cards)

| Metric | Formula | Comparison |
|---|---|---|
| **Key Interactions** | `SUM(total_interactions)` | vs. same period prior year |
| **Cost per Interaction** | `budget / total_interactions` | vs. same period prior year |
| **Inquiry Interactions** | Interactions in the RFI/Lead Gen category | vs. same period prior year |
| **Visit Interactions** | Interactions in the Visit/Event category | vs. same period prior year |
| **Apply Interactions** | Interactions in the Apply category | vs. same period prior year |

> **What is a "Key Interaction"?** It is the umbrella term for three types of digital conversions:
> - **Direct Key Interaction** — a pixel fired on the website (e.g., form submit, page visit)
> - **View-Through Interaction** — a student saw the ad but didn't click, then converted organically later
> - **In-Platform Lead** — a lead generated inside the ad platform itself (e.g., Meta Lead Ads)
>
> `total_interactions = direct_conversions + view_through_conversions + in_platform_leads`

### Trending Performance (daily line chart)

- X-axis: each day in the selected period
- Red line = current period (Key Interactions per day)
- Gold dashed line = same period prior year, aligned by day-of-month position
- Only odd-numbered days are labeled on the X-axis to reduce clutter

> **How does the daily comparison work?** Feb 15, 2026 is compared against Feb 15, 2025. It's a raw daily value, not cumulative.

### Key Interaction Categories (bar chart)

Volume breakdown by category: RFI/Lead Gen · Visit/Event · Apply · Enroll/Deposit · Other

### Engagement & Spend (metric grid)

| Metric | Formula |
|---|---|
| Budget | `SUM(budget)` |
| Cost per Click (CPC) | `budget / clicks` |
| Direct Key Interactions | `SUM(direct_conversions)` |
| Cost per Direct Key Int. | `budget / direct_conversions` |
| In-Platform Leads | `SUM(in_platform_leads)` |
| Cost per In-Plat. Lead | `budget / in_platform_leads` |
| View-through Int. | `SUM(view_through_conversions)` |
| Cost per Total Key Int. | `budget / total_interactions` |

> **Cost field note:** All cost metrics use the `budget` field, not `cost`. This was validated against Looker — CWU Feb 2026: Cost per Interaction = $22.83 ✅.

### Cost Per Total Key Interaction (line chart)

Daily cost-per-interaction trend for the current period (red) vs. the same period last year (gold dashed). Y-axis in dollars.

### Tables

| Table | Grouped by | Columns |
|---|---|---|
| Performance By Subgroup | subgroup_name | Impressions · Clicks · CTR% · Direct Key Int. · View-Through Int. · In-Platform Leads · Total Interactions |
| Performance By Strategy | product_name | Same columns |
| Interactions By Month & Year | event_year × event_month | All available months |
| Interactions By Strategy & Month | product_name × event_month | — |

All tables use heatmap coloring — darker = higher relative volume.

---

## 6 · Digital — Overview YoY ✨ (~1 min)

*"This tab is the same structure as Overview but focused on the year-over-year comparison view — it adds Impressions and CTR to the KPI strip and shows trending by month rather than by day."*

### KPI Strip (different from Overview)

| Metric | Formula |
|---|---|
| Impressions | `SUM(impressions)` |
| Clicks | `SUM(clicks)` |
| CTR | `clicks / impressions × 100` |
| Total Key Interactions | `SUM(total_interactions)` |
| Key Interaction Rate | `total_interactions / clicks × 100` |

### YoY Tables

Show current value and Δ% for each metric side by side:
Impressions | Δ% · Clicks | Δ% · CTR | Δ% · Direct Key Interaction | Δ% · View-Through Int. · In-Platform Leads | Δ% · Total Conversions | Δ% · Key Interaction Rate | Δ%

---

## 7 · Digital — Interactions ✨ (~2 min)

*"This tab goes one level deeper — it shows performance through the lens of what action the student took, not just which campaign they came from."*

**Data source:** Q9 — `tinman.v_kpi_conversion` — more granular than Q8; each row includes `conversion_name` (the exact conversion event configured in the ad platform) and `interaction_category` (Carnegie's standardized category).

### Page-Level Filters

| Filter | Description |
|---|---|
| **Interaction Category** | RFI/Lead Gen · Visit/Event · Apply · Enroll/Deposit · Other |
| **Paid Key Interaction** | Specific conversion name (as configured in the ad platform) |

### KPI Strip (5 cards by category)

| Card | `interaction_category` value |
|---|---|
| RFI / Lead Gen | "RFI/Lead Gen" |
| Visit / Events | "Visit/Event" |
| Apply | "Apply" |
| Enroll / Deposit | "Enroll/Deposit" |
| Other | "Other" |

**Validated:** CWU Feb 2026 — RFI/Lead Gen = 278.94 ✅ · Apply = 239.02 ✅ · Visit/Event = 46.98 ✅ · Total = 565.94 ✅ (matches Q8 and Looker).

### Charts

- **Key Interaction Category Trending** — volume by category over the selected period
- **Key Interaction Breakdown** — category share as a bar/pie breakdown
- **Key Interactions By Category & Strategy** — cross of category × product_name

### Tables

| Table | Grouped by |
|---|---|
| Breakdown By Interaction Category & Name | Category → Conversion Name → Strategy → Campaign |
| Key Interactions By Campaign Name | campaign_name |
| Key Interactions By Month | event_month |
| Key Interactions By Campaign & Interaction Name | campaign_name × conversion_name |

---

## 8 · Digital — Geography ✨ (~1 min)

*"Geography shows where the digital campaigns are generating results — by U.S. state."*

**Data source:** Q10 — `tinman.v_kpi_geo` (aggregated to region × month)

> **Note on totals:** Geographic totals may be ~1% lower than the Overview tab totals. This is expected — some platforms do not report geographic data for every impression. This gap is documented.

- **Map:** US choropleth. Metric selector: Impressions · Clicks · Total Key Interactions
- **Region Table:** Region · Impressions · Clicks · CTR · Direct Key Int. · View-Through Int. · Total Conversions — heatmap coloring

---

## 9 · Digital — Creative *(Work in Progress)* (~30 sec)

*"The Creative tab breaks down performance by individual ad creative — by platform. It's still a work in progress on the layout side, but the data is all there."*

**Data sources:** Q11a (`v_kpi_creative`) for creative performance + Q11b (`v_kpi_keyword`) for PPC keyword performance.

Each platform has its own table with the relevant columns:

| Platform | Unique columns |
|---|---|
| Display | Ad Group · Creative · Landing Page · Direct Key Int. · View-Through Int. · Total Key Int. |
| Meta | Ad Name · Description · Image · In-Platform Leads |
| YouTube | Video Starts · Video Completions |
| Snapchat | Clicks (Swipe Ups) |
| TikTok | Followers · Likes · Shares · Comments |
| LinkedIn | Description · Image · In-Platform Leads |
| PPC Keywords | Keyword · Match Type · CTR% · CPC · Cost/Conv. |

---

## 10 · Digital — Insights *(Work in Progress)* (~30 sec)

*"The Insights tab is going to be the home for the optimization notes — the qualitative history of decisions made on campaigns. It's pulling from the Tinman notes database."*

**Data source:** Q12 — `tinman.v_opnote` — 286 notes total

| Note Type | Count | Goes to |
|---|---|---|
| Optimization | 168 | Campaign Optimization History table |
| Performance | 73 | Performance Insights & Analysis table |
| Performance with Recommendation | 21 | Performance Insights (merged with Performance) |
| Campaign Launch | 19 | Either table |
| Budget | 4 | — |
| Key Dates | 1 | — |

> **Status:** Data is functional. Still working on the visual layout (cards vs. table), filtering by period and strategy, and highlighting milestone notes.

---

---

## Quick-Reference: Data Sources

### Enrollment Funnel Pages

| Query | File | Source | Used by |
|---|---|---|---|
| **Q6** | `q6_fbc_monthly.csv` | `udp_url.funnel_benchmark_current` (Slate source of truth) | All funnel KPIs, trending, source, program, state |
| **Q2** | `q2_campaign_cost.csv` | `conversion_campaign_attribution` + `campaign_roi` | Cost metrics only |
| **Q3** | `q3_geography.csv` | `conversion` + `address` | City-level detail table only |

### Digital Performance Pages

| Query | File | Source | Used by |
|---|---|---|---|
| **Q8** | `q8_digital_overview.csv` | `tinman.v_kpi_campaign` | Digital > Overview |
| **Q9** | `q9_digital_interactions.csv` | `tinman.v_kpi_conversion` | Digital > Interactions |
| **Q10** | `q10_digital_geo.csv` | `tinman.v_kpi_geo` | Digital > Geography |
| **Q11a** | `q11_digital_creative.csv` | `tinman.v_kpi_creative` | Digital > Creative |
| **Q11b** | `q11_digital_keywords.csv` | `tinman.v_kpi_keyword` | Digital > Creative (PPC) |
| **Q12** | `q12_digital_notes.csv` | `tinman.v_opnote` | Digital > Insights |

> **Why is Q6 the source of truth?** It's built on `funnel_benchmark_current` — the same dbt table that powers the Slate enrollment dashboard. All counts have been validated with zero gap against Slate across all 8 funnel stages.

---

## Anticipated Q&A

**"Do the numbers match Looker?"**
Yes — Q8/Q9 were validated against Looker. CWU Feb 2026: total_interactions = 565.94 ✅ · budget per interaction = $22.83 ✅.

**"Why doesn't the program total match the ROI Overview?"**
A student who applied to 2 programs is counted in both when we group by program name. This is correct for program-level ranking. The ROI Overview uses deduplicated person-level counts from Slate (source of truth).

**"The program trending chart shows the full year even when I filter to 3 months — is that a bug?"**
No, it's intentional. The "Program Trending vs. Goal" chart always shows the full academic year regardless of the period filter. The period filter only affects the Top Programs ranking chart and the Program Detail table.

**"The Digital Geography numbers don't quite match the Overview total — why?"**
Some ad platforms don't report geographic data for 100% of impressions. The gap is approximately 1% and is expected — it's documented in the data source.

**"Are the goal numbers accurate?"**
The current goal values are placeholder numbers set up for testing. Real CWU goals need to be confirmed by the team. The long-term plan is to have goals entered directly in Tinman rather than from a spreadsheet.

---

*Generated March 2026. Update as new data or features are added.*
