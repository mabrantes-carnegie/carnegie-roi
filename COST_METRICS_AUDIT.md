# Cost Metrics Audit — Carnegie ROI Dashboard

Generated: 2026-04-04

---

## 1. Complete Cost Metric Inventory

### A. ROI Overview Page (q2_campaign_cost.csv)

Source: `data/q2_campaign_cost.csv`
Budget column: `total_cost`

| CSV Column | Computed Column | UI Label | Definition | Page(s) |
|---|---|---|---|---|
| `total_cost` | — | (no direct display) | Raw campaign spend | ROI Overview (underlying) |
| `total_inquiries` | `cost_per_inquiry` | Cost/Inquiry | total_cost / total_inquiries | ROI Overview |
| `total_app_starts` | `cost_per_app_start` | Cost/App Start | total_cost / total_app_starts | ROI Overview |
| `total_app_submits` | `cost_per_app_submit` | Cost/App Submit | total_cost / total_app_submits | ROI Overview |
| `total_admits` | `cost_per_admit` | Cost/Admit | total_cost / total_admits | ROI Overview |
| `total_deposits` | `cost_per_deposit` | Cost/Deposit | total_cost / total_deposits | ROI Overview |
| `total_net_deposits` | `cost_per_net_deposit` | Cost/Net Deposit | total_cost / total_net_deposits | ROI Overview (KPI + detail panel) |
| `total_enrolled` | `cost_per_enrolled` | Cost/Enrolled | total_cost / total_enrolled | ROI Overview |

These are defined in `app/metrics.py` as `COST_PER_DEFS` and rendered via the collapsible "Cost Metrics" panel in `app/server.py` (`cost_detail_panel`).

### B. Digital Overview Page (q8_digital_overview.csv)

Source: `data/q8_digital_overview.csv`
Budget column: `budget`

| CSV Column(s) | Server ID | UI Label | Definition | Page(s) |
|---|---|---|---|---|
| `budget` | `dig_budget` | Budget | Sum of budget | Digital Overview, Digital Overview YoY |
| `budget`, `total_interactions` | `dig_cpi` | Cost per Interaction | budget / total_interactions | Digital Overview (KPI strip) |
| `budget`, `clicks` | `dig_cpc` | Cost per Click | budget / clicks | Digital Overview, Digital Overview YoY |
| `budget`, `direct_conversions` | `dig_cpdc` | Cost per Direct Key Int. | budget / direct_conversions | Digital Overview, Digital Overview YoY |
| `budget`, `in_platform_leads` | `dig_cpipl` | Cost per In-Plat. Lead | budget / in_platform_leads | Digital Overview, Digital Overview YoY |
| `budget`, `total_interactions` | `dig_cptc` | Cost per Total Key Int. | budget / total_interactions | Digital Overview, Digital Overview YoY |

The line chart "Cost Per Total Key Interaction" (`dig_cost_per_total_conv`) also plots daily budget / total_interactions over time.

### C. Digital Interactions Page (q9_digital_interactions.csv)

Source: `data/q9_digital_interactions.csv`
Budget column: `budget`

| CSV Column(s) | UI Label | Definition | Page(s) |
|---|---|---|---|
| `budget`, interactions where `interaction_category = "RFI/Lead Gen"` | Cost per RFI / Lead Gen | budget / RFI/Lead Gen interactions | Digital Interactions |
| `budget`, interactions where `interaction_category = "Visit/Event"` | Cost per Visit / Events | budget / Visit/Event interactions | Digital Interactions |
| `budget`, interactions where `interaction_category = "Apply"` | Cost per Application | budget / Apply interactions | Digital Interactions |
| `budget`, interactions where `interaction_category = "Enroll/Deposit"` | Cost per Enroll | budget / Enroll/Deposit interactions | Digital Interactions |
| `budget`, `total_interactions` (all categories) | Cost per Key Interaction | budget / total_interactions | Digital Interactions |

These are rendered in the collapsible "Cost Metrics" panel on the Interactions page (`dig_int_cost_panel`).

### D. PPC Keywords Table (q8_digital_overview.csv, PPC-filtered)

Computed columns added during aggregation in `digital_server.py` (line ~2527):

| Computed Column | UI Label | Definition | Page(s) |
|---|---|---|---|
| `cost_per_click` | Cost Per Click | budget / clicks | PPC Keywords |
| `cost_per_conversion` | Cost Per Direct Int. | budget / direct_conversions | PPC Keywords |

---

## 2. Redundancies

### Redundancy 1: "Cost per Interaction" vs "Cost per Total Key Int."

| Metric | Server ID | Formula | Page |
|---|---|---|---|
| Cost per Interaction | `dig_cpi` | budget / total_interactions | Digital Overview (KPI strip) |
| Cost per Total Key Int. | `dig_cptc` | budget / total_interactions | Digital Overview (metric card) |

**These are the same calculation.** Both divide `budget` by `total_interactions` from the same q8 dataset. They are computed independently in `dig_cpi()` (line 596) and `dig_cptc()` (line 732). The KPI strip uses the label "Cost per Interaction" while the metric card grid uses "Cost per Total Key Int."

**Recommendation:** Unify into a single label ("Cost per Key Interaction" is the clearest) and share a single reactive calc.

### Redundancy 2: "Cost per Click" appears in two contexts

- Digital Overview metric card grid (all strategies)
- PPC Keywords table (PPC-filtered only)

This is **not a true redundancy** since the scope differs (all strategies vs. PPC only), but the label is identical. Users may confuse them.

### Redundancy 3: "Cost per Direct Key Int." vs "Cost Per Direct Int."

- Digital Overview: "Cost per Direct Key Int." (budget / direct_conversions, all strategies)
- PPC Keywords: "Cost Per Direct Int." (budget / direct_conversions, PPC only)

Same formula, different scope, slightly different label. Consider aligning the naming.

---

## 3. Recommended Funnel Order for Cost Columns in Tables

Cost columns should follow the marketing/enrollment funnel from top to bottom:

### ROI Overview (enrollment funnel)

1. Cost/Inquiry
2. Cost/App Start
3. Cost/App Submit
4. Cost/Admit
5. Cost/Deposit
6. Cost/Net Deposit
7. Cost/Enrolled

### Digital Overview / Interactions (digital media funnel)

1. Cost per Click (top of funnel — ad engagement)
2. Cost per In-Plat. Lead (mid funnel — platform action)
3. Cost per Direct Key Int. (mid funnel — attributed conversion)
4. Cost per Total Key Int. (bottom of digital funnel — all conversions)

### Digital Interactions (interaction category funnel)

1. Cost per RFI / Lead Gen (top — inquiry)
2. Cost per Visit / Events (mid — engagement)
3. Cost per Application (mid-bottom — application)
4. Cost per Enroll (bottom — enrollment)
5. Cost per Key Interaction (aggregate — all categories)

### PPC Keywords Table

1. Cost Per Click
2. Cost Per Direct Int.
