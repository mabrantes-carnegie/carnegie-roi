# ROI Dashboard — Query Documentation

Last updated: March 31, 2026

---

## Data Sources

All queries pull from BigQuery project: `unified-data-platform-prod`

### Primary Tables

| Table | Schema | Purpose |
|---|---|---|
| `udp_url.conversion` | Enrollment funnel events | Person-level and application-level funnel data. One row per person × application. Contains all stage dates (inquired, app created, submitted, admitted, deposited, enrolled, exit). |
| `udp_url.conversion_campaign_attribution` | Campaign attribution | Links person_id to campaign_id. Multi-touch: one person can appear in multiple campaigns/sources. No first-touch or primary source field exists. |
| `udp_url.campaign_roi` | Campaign metadata + spend | Campaign-level data: product group, service, spend, conversions. Grain: one row per campaign × term. |
| `udp_udl.institution` | Institution reference | Institution name, city, state. Joined via institution_id. |
| `udp_udl.address` | Student address | Student home address (state, city). Joined via person_id + institution_id. Uses `address_rank = 1` for primary address. |

### Source of Truth — funnel_benchmark_current

The validated reference table is `udp_url.funnel_benchmark_current`. All funnel KPIs in the dashboard have been validated to 100% match against this table (zero gap across all 8 funnel stages).

**This table is the foundation for the entire dashboard.** It was built by the dbt team and powers the Slate enrollment dashboard.

#### How it works

The table unpivots the `conversion` table so that each funnel milestone date becomes its own row. Instead of one row per person with multiple date columns, each row represents **one person/application reaching one funnel stage on one specific date**.

Example: A student who was a prospect on 2024-01-01, inquiry on 2024-02-01, and submitted on 2024-03-01 becomes 3 rows:
- Row 1: funnel_day=2024-01-01, funnel_stage counts include prospect
- Row 2: funnel_day=2024-02-01, funnel_stage counts include inquiry
- Row 3: funnel_day=2024-03-01, funnel_stage counts include app_submitted

#### Key fields

| Column | Type | Description |
|---|---|---|
| `institution_id` | STRING | FK to institution table |
| `institution_name` | STRING | Institution name |
| `entry_term_year` | INT64 | Enrollment cohort year |
| `entry_term_semester` | STRING | Enrollment cohort semester |
| `student_type` | STRING | Person-level for Prospect/Inquiry, app-level for later stages |
| `is_international_student` | BOOL | International flag |
| `origin_source_first` | STRING | First source of this prospect |
| `region` | STRING | 2-letter US state code from primary address |
| `program_level` | STRING | Graduate, Undergraduate, etc. |
| `program_modality` | STRING | Online, On-Campus, etc. |
| `funnel_day` | DATE | **The date this funnel event occurred** |
| `funnel_prospect_count` | INT64 | New prospects on this day |
| `funnel_inquired_count` | INT64 | New inquiries on this day |
| `funnel_app_created_count` | INT64 | New app starts on this day |
| `funnel_app_submitted_count` | INT64 | New app submits on this day |
| `funnel_admitted_count` | INT64 | New admits on this day |
| `funnel_deposited_count` | INT64 | New deposits on this day |
| `funnel_enrolled_count` | INT64 | New enrolled on this day |
| `funnel_net_deposited_count` | INT64 | Deposits minus exits after deposit on this day |
| `funnel_exit_after_deposit_count` | INT64 | Exits after deposit on this day |

#### Why this matters for our queries

**We can potentially replace Q1 and Q4 by querying this table directly:**

- **For KPI totals (Q1):** `SUM(funnel_inquired_count)` grouped by institution, term_year, term_semester, student_type, is_international
- **For monthly trending (Q4):** `SUM(funnel_inquired_count)` grouped by `FORMAT_DATE('%Y-%m', funnel_day)` — the monthly granularity comes free from `funnel_day`
- **For program-level data:** Has `program_level` and `program_modality` — may support the Programs tab
- **For geography:** Has `region` (2-letter state code) — may supplement or replace Q3

**Advantages of using this table:**
- It IS the Source of Truth — no risk of counting logic divergence
- Already handles the COALESCE logic for term fields, student_type, and CommonApp dates
- Already handles person_id dedup for Prospect/Inquiry and application_id for App stages
- Has daily granularity (`funnel_day`) which we can aggregate to monthly
- Has `origin_source_first` — a first-touch source field that could solve the multi-touch problem in Q5

**`origin_source_first` is potentially the solution to the Q5 multi-touch issue.** It's a person-level first source attribute, not campaign attribution. Need to investigate what values it contains and whether it maps to the lead sources used in Q2.

#### Grain handling from the dbt model

The dbt model documents an important grain detail:
- Source table (`conversion`) grain: institution × person × application × rank
- Prospect and Inquiry are **person-level** (use COUNT DISTINCT person_id to avoid double-counting people with multiple applications)
- Application-level stages (App Created onward) use **COUNTIF** since the grain is already correct at the application level
- The table's counts already handle this correctly — we just need to SUM them

---

## Campaign Attribution Gap — Critical Finding

> **Investigated: March 31, 2026**

### Root cause

`conversion_campaign_attribution` only includes students whose funnel stage date falls **within an active campaign period**. The WHERE clause in the underlying dbt model (`conversion_campaign_attribution.sql`) enforces this:

```sql
where case
    when c.funnel_target = 'Prospect' then bc.person_prospect_date
    when c.funnel_target = 'Inquiry'  then bc.person_inquired_date
    ...
end between c.start_date and c.end_date
```

For CWU, no campaigns are registered in BigQuery before **2024-04-01**. This means any student who reached a funnel stage before that date has no campaign attribution — even if they are enrolled in a 2026 term cohort.

This is expected behavior per the dbt model design. It is not a bug in the dashboard.

### Measured gap (CWU, Fall 2026, First Year)

| Source | Total Inquiries |
|---|---|
| `funnel_benchmark_current` (Source of Truth) | 27,851 |
| `conversion_campaign_attribution` | 356 |
| **Gap** | **27,495 (98.7%)** |

The 27,495 students without campaign attribution either converted organically, converted before any campaign was registered, or were never touched by a tracked campaign.

**Important note from engineering (Roy Nalven):** `funnel_day` for Prospect comes from `person.person_prospect_date`, which can originate from the distant past (e.g., middle school engagement events). It is valid for a prospect date of 2018 to belong to a 2026 entry term cohort — which is why funnel_day values as old as 2018-08-08 appear in Fall 2026 data.

### Implication for cost metrics

Because Q2 funnel counts represent only 1.3% of the real funnel, **Q2 counts must never be used as denominators for cost metrics shown alongside Q6 totals.** The correct formula for all cost-per-stage metrics is:

| Metric | Numerator | Denominator | Notes |
|---|---|---|---|
| Cost per Net Deposit | Q2 total spend | Q6 net deposits | ✅ Valid — measures total investment efficiency |
| Cost per Inquiry (campaign-attributed) | Q2 spend | Q2 inquiries (356) | ✅ Valid only if labeled "campaign-attributed" |
| Cost per Inquiry (vs full funnel) | Q2 spend | Q6 inquiries (27,851) | ❌ Misleading — dilutes cost across non-campaign students |

In Python, always verify the denominator source:

```python
# Correct
cost_per_net_deposit = q2['total_cost'].sum() / q6['total_net_deposits'].sum()

# Wrong — denominador inflado pelo multi-touch, universo errado
cost_per_inquiry = q2['total_cost'].sum() / q2['total_inquiries'].sum()
```

### Validation query

Use this to confirm the gap for any institution/term combination:

```sql
select
  'funnel_benchmark_current' as source,
  sum(funnel_inquired_count) as total_inquiries
from `unified-data-platform-prod.udp_url.funnel_benchmark_current`
where institution_name like '%Central Washington%'
  and entry_term_year = 2026
  and entry_term_semester = 'Fall'
  and student_type = 'First Year'

union all

select
  'conversion_campaign_attribution' as source,
  count(distinct person_id) as total_inquiries
from `unified-data-platform-prod.udp_url.conversion_campaign_attribution`
where institution_name like '%Central Washington%'
  and entry_term_year = 2026
  and entry_term_semester = 'Fall'
  and campaign_funnel_target = 'Inquiry'
```

To validate Q6 against the raw `conversion` table (confirming the gap is a campaign data issue, not a counting logic issue):

```sql
select
  'funnel_benchmark_current' as source,
  sum(funnel_inquired_count) as total_inquiries
from `unified-data-platform-prod.udp_url.funnel_benchmark_current`
where institution_name like '%Central Washington%'
  and entry_term_year = 2026
  and entry_term_semester = 'Fall'
  and student_type = 'First Year'

union all

select
  'conversion' as source,
  count(distinct c.person_id) as total_inquiries
from `unified-data-platform-prod.udp_url.conversion` as c
inner join `unified-data-platform-prod.udp_udl.institution` as i
  on c.institution_id = i.id
where i.name like '%Central Washington%'
  and coalesce(c.person_entry_term_year, c.app_entry_term_year) = 2026
  and coalesce(c.person_entry_term_semester, c.app_entry_term_semester) = 'Fall'
  and coalesce(c.person_student_type, c.app_student_type) = 'First Year'
  and c.person_inquired_date is not null
```

If both rows return equal numbers → Q6 is correct. The gap with Q2 is purely a campaign data coverage issue upstream. The open question (tracked in Asana) is why CWU campaign history prior to April 2024 was not imported into BigQuery.

---

## Counting Rules (from Anderson Murphy, VP Data Intelligence)

| Funnel Stage | Count Method | ID Field | Date Field |
|---|---|---|---|
| Prospects | COUNT DISTINCT | `person_id` | `person_prospect_date` |
| Inquiries | COUNT DISTINCT | `person_id` | `person_inquired_date` |
| App Starts | COUNT DISTINCT | `application_id` | `app_created_date` (or `app_submitted_date` for CommonApp) |
| App Submits | COUNT DISTINCT | `application_id` | `app_submitted_date` |
| Admits | COUNT DISTINCT | `application_id` | `app_admitted_date` |
| Deposits | COUNT DISTINCT | `person_id` | `app_deposited_date` |
| Net Deposits | Deposits − Exits | `person_id` | `app_deposited_date` minus `app_exit_date` where `app_exit_after_deposit = TRUE` |
| Enrolled | COUNT DISTINCT | `person_id` | `app_enrolled_date` |

### Nuance on Count Distinct (confirmed by Anderson)

The enrollment dashboard uses a **cumulative funnel**: a student who is Net Confirmed also counts in Confirmed, Admits, Applicants, etc. Within each stage:

- **Prospects and Inquiries** = unique students (`person_id`)
- **App Starts, App Submits** = unique applications (`application_id`) — one person with 2 applications counts as 2 at these stages
- **Admits** = unique applications (`application_id`) — same logic, one person admitted in 2 programs counts as 2
- **Deposits, Net Deposits, Enrolled** = back to unique students (`person_id`)

### Special Logic

**CommonApp date fix:** For applications where `LOWER(app_type) LIKE '%common%'`, use `app_submitted_date` as the App Start date instead of `app_created_date`.

**Inquiry term fallback:** Use `COALESCE(person_entry_term_year, app_entry_term_year)` and `COALESCE(person_entry_term_semester, app_entry_term_semester)` because inquiry-stage students may not have application-level term fields populated yet.

**Net Deposits formula:** `Net Deposits = Deposits - Withdrawals`. Uses `app_exit_after_deposit = TRUE` flag (confirmed by Anderson: "Net Deposits is Deposits - Withdraws. If app_exit_after_deposit would be the same as withdraw then you're correct").

### Scope Decisions (confirmed by Anderson)

- **ROI Funnel scope:** Scorecards and all "progress to goal" charts should focus on the **full student funnel** — everyone who converted regardless of campaign attribution
- **Default filters:** Default for all clients should be **all student types**. If a client has unique filtering requirements (like CWU = First Year + Domestic), configure on ad hoc basis or use filters at the top of the report
- **The old ROI dashboard problem:** Used `SUM(inquired_converted)` which counted a student once per campaign they're attributed to — the same student counted multiple times. Anderson confirmed the dashboard should use COUNT DISTINCT instead

---

## Query Inventory

### ACTIVE QUERIES

---

### Q6: Monthly Funnel from Source of Truth (PRIMARY)

| Property | Value |
|---|---|
| **File** | `data/q6_fbc_monthly.csv` |
| **Source table** | `udp_url.funnel_benchmark_current` (Slate dashboard Source of Truth) |
| **Status** | ✅ Active — primary data source for most dashboard components |
| **Powers** | KPI cards, YoY deltas, trending chart, source trend, state geography, program_level |
| **Grain** | institution × term_year × term_semester × student_type × is_international × origin_source_first × student_state × program_level × event_year × event_month |
| **Has monthly data?** | Yes (from `funnel_day` aggregated to month) |
| **Has source data?** | Yes (`origin_source_first` — first-touch, deduplicated per person) |
| **Has state data?** | Yes (`region` — 2-letter state code from student primary address) |
| **Has program data?** | Yes (`program_name` from application table via LEFT JOIN — specific program names like "aviation pilot", "elementary education baed") |
| **Term years** | 2024, 2025, 2026 |

**Columns:** institution_name, term_year, term_semester, student_type, is_international, origin_source_first, student_state, program_level, program_name, event_year, event_month, event_month_name, total_prospects, total_inquiries, total_app_starts, total_app_submits, total_admits, total_deposits, total_net_deposits, total_enrolled

**Why this query exists:** Replicates the exact dbt logic of funnel_benchmark_current, adding application.program_name via LEFT JOIN. This gives ONE query that powers the entire dashboard with consistent counting logic.

**VALIDATED:** When aggregated without program_name, matches funnel_benchmark_current 100% across all stages (27,522 inquiries, 9,139 app starts, 7,703 app submits, 6,892 admits, 1,808 deposits, 1,767 net deposits for CWU Fall 2026 First Year Domestic).

**Program name behavior:**
- Source: `application.program_name` (standardized program names from application table)
- Students who inquired but never applied have NULL program_name → display as "Not Specified" in the Programs tab
- A student who applied to 2 programs will count in both programs when grouped by program_name — this is expected and correct for program-level ranking analysis
- The Programs tab does NOT show total KPI cards — only per-program rankings — so the multi-program count is never compared against institution totals
- Program names are lowercase in source data — Python converts to title case for display

**Python aggregation examples:**
- KPI totals (ROI Overview): `df.groupby(['term_year'])['total_inquiries'].sum()` — do NOT include program_name in groupby
- Monthly trending: `df.groupby(['term_year','event_year','event_month'])['total_inquiries'].sum()`
- Source trend: `df.groupby(['term_year','origin_source_first','event_year','event_month'])['total_inquiries'].sum()`
- State totals: `df.groupby(['term_year','student_state'])['total_inquiries'].sum()`
- Program ranking: `df.groupby(['term_year','program_name'])['total_inquiries'].sum()` — for Programs tab only

---

### Q2: Campaign Lead Source + Cost

| Property | Value |
|---|---|
| **File** | `data/q2_campaign_cost.csv` |
| **Source table** | `udp_url.conversion_campaign_attribution` + `udp_url.campaign_roi` |
| **Status** | ✅ Active — only source of campaign spend data |
| **Powers** | Cost per net deposit badge on ROI Overview |
| **Grain** | institution × term_year × term_semester × lead_source × campaign_service |
| **Has monthly data?** | No |
| **Has source data?** | Yes (`campaign_product_group` as lead_source — marketing attribution, multi-touch) |
| **Has cost data?** | Yes (`campaign_spend`) |
| **Term years** | 2025, 2026 |

**Columns:** institution_name, term_year, term_semester, lead_source, campaign_service, campaign_funnel_target, campaign_attributable, total_cost, total_inquiries, total_app_starts, total_app_submits, total_admits, total_deposits, total_net_deposits, total_enrolled

**⚠️ Critical — Campaign attribution gap:** For CWU Fall 2026 First Year, Q2 captures only 356 out of 27,851 inquiries (1.3%). This is because `conversion_campaign_attribution` only links students whose funnel stage date falls within a registered campaign period, and CWU has no campaigns in BigQuery before 2024-04-01. See the **Campaign Attribution Gap** section above for full details.

**⚠️ Critical — Funnel counts in Q2 must not be used as denominators for cost metrics displayed against Q6 totals.** The only valid cost metric combining Q2 and Q6 is Cost per Net Deposit (Q2 spend ÷ Q6 net deposits). All other per-stage cost metrics must use Q2 counts as the denominator AND be clearly labeled "campaign-attributed only" in the UI.

**Known issue — Multi-touch attribution:** Funnel counts in this query are also inflated because each student counts in every campaign/source they were attributed to. These numbers will NOT match Q6 totals. This is expected — Q2 shows campaign-attributed performance, Q6 shows full-funnel deduplicated performance. Different scopes.

#### Spend allocation — Critical finding (March 31, 2026)

The original Q2 used `campaign_roi.campaign_spend` as the spend source. This caused **double-counting**: the same campaign's total spend appeared in both 2025 and 2026 whenever the campaign touched students from both cohorts.

**Root cause:** The dbt pipeline aggregates `campaign_revenue` into a single total per campaign before any join with `entry_term_year`:

```sql
-- Inside conversion_campaign_attribution dbt model
select campaign_id, sum(revenue) as total_revenue  -- loses campaign_month
from campaign_revenue
group by 1
```

This discards `campaign_month`, so `campaign_roi` has no way to know which portion of spend belongs to which year — it simply repeats the total for every `entry_term_year` that had conversions.

**The fix:** Bypass `campaign_roi` and read `campaign_revenue` directly, allocating spend by `campaign_month` using the academic year definition (Fall N = July N-1 to June N):

```sql
CASE
    WHEN campaign_month BETWEEN '2024-07-01' AND '2025-06-30' THEN 2025
    WHEN campaign_month BETWEEN '2025-07-01' AND '2026-06-30' THEN 2026
END AS term_year
```

**Why this is the correct approach:** The dashboard shows a funnel view filtered by academic year. A campaign may touch a student today who only enrolls in a future term — that is a sign of campaign effectiveness, not a problem. But the spend itself happened in a specific month and should be counted in the academic year that month belongs to. This is consistent with how all other metrics in the dashboard are scoped: by the academic year in which the activity occurred.

This means a campaign that spent $110k between July 2024 and June 2025 counts fully as Fall 2025 spend — regardless of whether some attributed students converted in Fall 2026. The spend allocation follows the financial calendar, not the student cohort.

**Scope note:** Spend that occurred before July 2024 (e.g. a Clarity Slate Integration with $3,000 in April 2024) belongs to Fall 2024 and is intentionally excluded from the dashboard scope (2025/2026 only).

**Validated spend after fix:**

| term_year | Old spend (campaign_roi) | Correct spend (campaign_revenue) |
|---|---|---|
| 2025 | $782,816 | $375,622 |
| 2026 | $741,469 | $224,675 |

The old values were inflated by ~2x because campaign spend was being double-counted across years.

**Python calculates:** cost per net deposit (Q2 spend ÷ Q6 net deposits), YoY cost comparison

**Used by:** ROI Overview (cost per net deposit badge)

---

### Q3: Geography Breakdown — City Level

| Property | Value |
|---|---|
| **File** | `data/q3_geography.csv` |
| **Source table** | `udp_url.conversion` + `udp_udl.address` |
| **Status** | ✅ Active — only source of city-level data |
| **Powers** | City detail table on Geography page |
| **Grain** | institution × term_year × term_semester × state × city |
| **Has monthly data?** | No |
| **Has city data?** | Yes (via address table JOIN) |
| **Term years** | 2024, 2025, 2026 |

**Columns:** institution_name, institution_state, student_state, student_city, term_year, term_semester, total_inquiries, total_app_starts, total_app_submits, total_admits, total_deposits, total_net_deposits, total_enrolled

**Note:** State-level totals now come from Q6. Q3 is only needed for the city-level drill-down table. If city detail is removed from the dashboard, Q3 can be retired.

#### Bug fix — March 31, 2026

The original Q3 had two bugs that caused incorrect counts for app-level stages (App Submits, Admits, Deposits, Enrolled), especially for 2026 (gap of -610 app_submits, -648 admits).

**Bug 1 — Wrong COALESCE order for app stages:** The original query used `COALESCE(person_student_type, app_student_type)` and `COALESCE(person_entry_term_year, app_entry_term_year)` for all stages. App-level stages require `app` fields first — same logic as `funnel_benchmark_current`.

**Bug 2 — GROUP BY conflicting with stage logic:** Even with the correct COALESCE inside each `COUNT DISTINCT`, the `GROUP BY term_year` used `COALESCE(person_entry_term_year, app_entry_term_year)`. A student with `person_term_year=2025` and `app_term_year=2026` was bucketed into 2025, but the SOT placed their app_submit in 2026 — causing counts in the wrong year.

**Fix:** Each funnel stage now has its own CTE with the correct `term_year` COALESCE order before aggregation. The final SELECT joins all stage CTEs at the `student_state × student_city × term_year × term_semester` level. This is the only approach that correctly attributes each stage to the right term_year when person fields differ from app fields.

**Validation results (March 31, 2026):**

| Stage | 2024 | 2025 | 2026 |
|---|---|---|---|
| Inquiries | ✅ 0 | ✅ 0 | ✅ 0 |
| App Submits | ✅ 0 | ✅ 0 | ✅ 0 |
| Admits | ✅ 0 | ✅ 0 | ✅ 0 |
| Deposits | -2 | ✅ 0 | ✅ 0 |
| Enrolled | -2 | ✅ 0 | ✅ 0 |

The -2 gap in 2024 deposits/enrolled is negligible and may reflect an edge case in `app_exit_after_deposit` logic for historical data.

**Known data quality issues:**

**NULL state/city — by stage (CWU Fall 2026 First Year Domestic):**

| Stage | Total | No State | % |
|---|---|---|---|
| Inquiries | 27,720 | 4,901 | 17.7% |
| App Submits | 7,766 | 102 | 1.3% |
| Admits | 6,948 | 58 | 0.8% |
| Deposits | 1,858 | 26 | 1.4% |
| Enrolled | 1,877 | 27 | 1.4% |

The NULL state concentration in Inquiries is expected and by design — students captured at campus events or college fairs are not required to provide an address at that point. The top sources with no state are Campus Event (1,566), College Fair (932), RFI Forms (431), and International Fair (290). As students progress through the funnel and complete an application, they provide a full address — which is why NULL state drops to ~1% at App Submits and beyond.

For 2024, NULL state reaches 53.6% — historical records from before consistent address collection was in place.

**Display rule:** All NULL and empty string states should be displayed as "Unknown" in the dashboard with the note: *"Students captured at campus events or college fairs may not have a state on record."*

**Q6 vs Q3 representation:** Q6 represents no-state as `""` (empty string), Q3 as `NULL` — same students, different representation. Python must treat both as "Unknown".

---

### Q7: Program Performance (RETIRED → merged into Q6 Unified)

| Property | Value |
|---|---|
| **File** | `data/q7_programs.csv` |
| **Status** | ⚠️ Retired — Q6 Unified now includes program_name via LEFT JOIN with application table |
| **Reason** | Q6 Unified replicates the funnel_benchmark_current dbt logic and adds application.program_name. When aggregated without program_name, matches Source of Truth 100%. When grouped by program_name, provides per-program rankings. No need for a separate query. |

---

### DIGITAL PERFORMANCE QUERIES

All digital queries pull from BigQuery project: `carnegie-dartlet-1528198422380.tinman`

Common filter fields across all digital tables: `client_name`, `campaign_group_name` (Group), `campaign_subgroup_name` (Subgroup), `product_name` (Product), `campaign_name` (Campaign), `day` (date).

**CRITICAL — Cost field:** The Looker dashboard uses `budget` (not `cost`) for all cost metrics. Validated: CWU Feb 2026 Cost per Interaction = $22.71 matches `budget / total_interactions`. All Python cost calculations must use `budget`.

**CRITICAL — Metric formulas (validated against Looker, March 31, 2026):**

| Metric | Formula | Notes |
|---|---|---|
| Total Interactions | `SUM(conversions + view_through_conversions + leads)` | Includes view-through |
| Conversion Rate | `SUM(conversions + leads) / SUM(clicks)` | **Excludes** view_through_conversions |
| CTR | `SUM(clicks) / SUM(impressions)` | |
| Cost per Interaction | `SUM(budget) / SUM(total_interactions)` | |
| CPC | `SUM(budget) / SUM(clicks)` | |

`view_through_conversions` counts toward Total Interactions but is excluded from Conversion Rate. Looker formula confirmed: `SUM(conversions + leads) / SUM(clicks)`. Validated: CWU Jul 2025–Jun 2026 = 3.6% ✅.

**CRITICAL — Interaction Category mapping (Q9):** The `conversion_type` field does not match Looker's "Conversion Buckets" logic exactly. Q9 replicates the full Looker CASE using `LOWER(conversion) LIKE` pattern matching. Key example: `submit_application_website` has `conversion_type = 'Other'` but Looker maps it to `Apply` via pattern `%app%`. Without this remapping, Apply interactions are undercounted. See Digital Architecture doc for full mapping logic.

**Validated benchmarks (CWU):**

| Period | Metric | Value |
|---|---|---|
| Feb 2026 | Total Interactions | 568.8 ✅ |
| Feb 2026 | Cost per Interaction | $22.71 ✅ |
| Feb 2026 | RFI/Lead Gen | 278.9 ✅ |
| Feb 2026 | Visit/Event | 48.0 ✅ |
| Feb 2026 | Apply | 241.9 ✅ |
| Jul 25–Jun 26 | Impressions | 21.6M ✅ |
| Jul 25–Jun 26 | Clicks | 115.4K ✅ |
| Jul 25–Jun 26 | CTR | 0.5% ✅ |
| Jul 25–Jun 26 | Conversion Rate | 3.6% ✅ |

---

### Q8: Digital Overview

| Property | Value |
|---|---|
| **File** | `data/q8_digital_overview.csv` |
| **Source table** | `tinman.v_kpi_campaign` |
| **Status** | ✅ Active |
| **Powers** | Digital > Overview tab (KPIs, trending, engagement, channel mix, strategy/subgroup tables) |
| **Grain** | client × group × subgroup × product × campaign × day |
| **Rows** | ~8,000 |

**Columns:** client_name, group_name, subgroup_name, strategy (product_group_name), product_name, campaign_name, day, event_year, event_month, event_month_name, impressions, clicks, direct_conversions, view_through_conversions, in_platform_leads, total_interactions, cost, budget, followers, likes, shares, comments, video_starts, video_25pct, video_50pct, video_75pct, video_completions

**Python calculates:**
- CTR = clicks / impressions
- CPC = budget / clicks
- Cost per Interaction = budget / total_interactions
- Cost per Direct Conversion = budget / direct_conversions
- Cost per In-Platform Lead = budget / in_platform_leads
- Conversion Rate = total_interactions / clicks
- YoY Δ and MoM Δ for all metrics

**Validated:** CWU Feb 2026 — total_interactions = 565.94 ✅, budget_per_interaction = $22.83 ✅ (matches Looker)

---

### Q9: Digital Interactions

| Property | Value |
|---|---|
| **File** | `data/q9_digital_interactions.csv` |
| **Source table** | `tinman.v_kpi_conversion` |
| **Status** | ✅ Active |
| **Powers** | Digital > Interactions tab (categories, trending, breakdown by strategy/campaign) |
| **Grain** | client × group × subgroup × product × campaign × conversion_name × interaction_category × day |

**Columns:** client_name, group_name, subgroup_name, product_name, campaign_name, conversion_name, interaction_category, day, event_year, event_month, event_month_name, direct_conversions, view_through_conversions, in_platform_leads, total_interactions, cost, budget

**Key field — interaction_category:** Maps to Looker KPI cards:

| interaction_category (data) | Looker label | Dashboard label |
|---|---|---|
| RFI/Lead Gen | Inquiry Interactions | Inquiry Interactions |
| Apply | Apply Interactions | Apply Interactions |
| Visit/Event | Visit Interactions | Visit Interactions |
| Enroll/Deposit | Enroll/Deposit | Enroll/Deposit |
| Other | Other | Other |

**Validated:** CWU Feb 2026 — RFI/Lead Gen = 278.94 ✅, Apply = 239.02 ✅, Visit/Event = 46.98 ✅, Total = 565.94 ✅ (matches Q8 and Looker)

---

### Q10: Digital Geography

| Property | Value |
|---|---|
| **File** | `data/q10_digital_geo.csv` |
| **Source table** | `tinman.v_kpi_geo` |
| **Status** | ✅ Active |
| **Powers** | Digital > Geography tab (map, region table) |
| **Grain** | client × group × subgroup × product × region × month |
| **Rows** | ~2,820 |

**Columns:** client_name, group_name, subgroup_name, product_name, region, event_year, event_month, event_month_name, impressions, clicks, direct_conversions, view_through_conversions, in_platform_leads, total_conversions, cost, budget

**Note:** Aggregated to region × month (no location, no day) to keep CSV manageable. Location-level detail available via live BigQuery when connected. Region totals may not match Q8 exactly (~1% gap) because some platforms don't report geographic data for all impressions.

---

### Q11a: Digital Creative

| Property | Value |
|---|---|
| **File** | `data/q11_digital_creative.csv` |
| **Source table** | `tinman.v_kpi_creative` |
| **Status** | ✅ Active |
| **Powers** | Digital > Creative tab (creative tables by platform) |
| **Grain** | client × group × subgroup × product × campaign × creative × month |
| **Rows** | ~2,153 |

**Columns:** client_name, group_name, subgroup_name, product_name, platform_campaign_name, campaign_name, creative, ad_description, ad_url, image_url, preview_url, ad_group, event_year, event_month, event_month_name, impressions, clicks, direct_conversions, view_through_conversions, in_platform_leads, total_conversions, cost, budget, followers, likes, shares, comments, video_starts, video_completions

**Used by:** Display Creative table, Meta Creative table, LinkedIn Creative table, YouTube Creative table, Snapchat Creative table, TikTok Creative table, Spotify Creative table, Reddit Creative table — all filtered by `product_name`

---

### Q11b: PPC Keywords

| Property | Value |
|---|---|
| **File** | `data/q11_digital_keywords.csv` |
| **Source table** | `tinman.v_kpi_keyword` |
| **Status** | ✅ Active |
| **Powers** | Digital > Creative tab (PPC keyword performance table) |
| **Grain** | client × campaign × keyword × match_type × month |
| **Rows** | ~2,380 |

**Columns:** client_name, platform_campaign_name, campaign_name, product_name, keyword, match_type, event_year, event_month, event_month_name, impressions, clicks, direct_conversions, cost, budget

---

### Q13: Campaign Coverage by Funnel Stage

| Property | Value |
|---|---|
| **File** | `data/q13_campaign_coverage.csv` |
| **Source table** | `udp_url.funnel_benchmark_current` + `udp_url.conversion_campaign_attribution` + `udp_url.conversion` |
| **Status** | ✅ Active |
| **Powers** | Campaign Reach section — shows the real penetration of Carnegie campaigns within the full funnel |
| **Grain** | institution × term_year |
| **Term years** | 2025, 2026 |

**Columns:** term_year, sot_prospects, campaign_prospects, pct_prospects, sot_inquiries, campaign_inquiries, pct_inquiries, sot_app_starts, campaign_app_starts, pct_app_starts, sot_app_submits, campaign_app_submits, pct_app_submits, sot_admits, campaign_admits, pct_admits, sot_deposits, campaign_deposits, pct_deposits, sot_net_deposits, campaign_net_deposits, pct_net_deposits, sot_enrolled, campaign_enrolled, pct_enrolled

**Why this query exists:** The campaign attribution gap (~1-8% for early funnel stages) means the client needs context on how much of their total funnel was actually touched by Carnegie campaigns. This query provides that context by stage.

**Key finding (CWU Fall 2025/2026, First Year Domestic):**

| Stage | 2025 | 2026 |
|---|---|---|
| Prospects | 1.0% | 0.6% |
| Inquiries | 7.6% | 4.2% |
| App Starts | 15.6% | 11.9% |
| App Submits | 18.9% | 14.1% |
| Admits | 21.0% | 15.7% |
| Deposits | 57.2% | 56.8% |
| Net Deposits | 59.8% | 56.3% |
| Enrolled | 57.9% | 57.6% |

**Notable insight:** There is a large jump between Admits (~21%) and Deposits (~57%), suggesting Carnegie yield campaigns (deposit-stage) are significantly more effective than awareness/inquiry campaigns at penetrating the full funnel. Coverage stabilizes at ~57-60% for all final conversion stages, consistent across both years.

---

### Q12: Optimization Notes

| Property | Value |
|---|---|
| **File** | `data/q12_digital_notes.csv` |
| **Source table** | `tinman.v_opnote` |
| **Status** | ✅ Active |
| **Powers** | Digital > Insights tab (performance insights, optimization history) |
| **Grain** | One row per note |
| **Rows** | 286 |

**Columns:** client_name, group_name, subgroup_name, product_name, strategy, campaign_name, day, note_type, is_milestone, notes, created_by

**note_type values:**

| note_type | Count | Use |
|---|---|---|
| Optimization | 168 | Campaign Optimization History table |
| Performance | 73 | Performance Insights & Analysis table |
| Performance with Recommendation | 21 | Performance Insights table (merged with Performance) |
| Campaign Launch | 19 | Can show in either table or as a filter |
| Budget | 4 | Budget-related notes |
| Key Dates | 1 | Milestone dates |

---

### RETIRED QUERIES

---

### Q1: Funnel KPIs (RETIRED → replaced by Q6)

---

### Q4: Monthly Trending by Stage (RETIRED → replaced by Q6)

| Property | Value |
|---|---|
| **File** | `data/q4_monthly_trending.csv` |
| **Status** | ⚠️ Retired — Q6 provides the same monthly data directly from Source of Truth |
| **Reason** | Q6 has the same event_year + event_month granularity, plus origin_source_first and student_state that Q4 lacked. |

**Migration:** Replace all references to `q4_monthly_trending.csv` with Q6 filtered by stage. Q4 used a long format (one `stage` column); Q6 uses wide format (one column per stage). Python pivot or column selection handles the difference.

---

### Q5: Monthly Trending by Lead Source (RETIRED → never usable)

| Property | Value |
|---|---|
| **File** | `data/q5_monthly_source_trending.csv` |
| **Status** | ❌ Retired — multi-touch attribution made all source lines identical |
| **Reason** | `conversion_campaign_attribution` is multi-touch. Same student appeared in all 4 sources. Q6 uses `origin_source_first` (first-touch, deduplicated) which produces meaningful distinct values per source. |

---

## Query Dependency Map

```
ROI Overview page
├── KPI Strip ──────────── Q6 (aggregated by term_year)
├── Secondary Metrics ──── Q6 (rates) + Q2 (cost per net deposit: Q2 spend ÷ Q6 net_deposits)
├── Trending Performance ── Q6 (aggregated by event_year + event_month)
└── Progress to Goal ───── Q6 (actuals) + roi_goals.csv (targets)

Funnel Deep Dive page
├── Enrollment Funnel ──── Q6 (aggregated by term_year, current vs PY)
├── Source Performance ─── Q6 (by origin_source_first — Slate lead source, first-touch)
├── Source Trend ────────── Q6 (by origin_source_first + event_month)
├── Conversion Rates ───── Q6 (admit rate, yield rate by origin_source_first)
└── Cost per Lead Source ── Q2 (campaign spend data — secondary/advanced view if needed)

Geography page
├── Programs tab ────────── Q6 (grouped by program_name)
├── Map ─────────────────── Q6 (grouped by student_state)
└── City Detail Table ──── Q3 (only query with city-level data)

Digital Performance page (5 sub-pages via tabs)
├── Overview tab ─────────── Q8 (campaign-level: KPIs, trending, channel mix, strategy/subgroup tables)
├── Interactions tab ──────── Q9 (conversion-level: interaction categories, trending, breakdown)
├── Geography tab ─────────── Q10 (region-level: map, region table)
├── Creative tab ──────────── Q11a (creative performance) + Q11b (PPC keywords)
└── Insights tab ──────────── Q12 (optimization notes, performance insights)
```

### Data file summary (after migration)

| File | Role | Used by |
|---|---|---|
| `q6_fbc_monthly.csv` | PRIMARY — all funnel metrics, trending, sources, states, programs | ROI Overview, Funnel Deep Dive, Geography |
| `q2_campaign_cost.csv` | Cost/spend data only | ROI Overview (cost badge) |
| `q3_geography.csv` | City-level detail only | Geography (city table) |
| `q8_digital_overview.csv` | Digital campaign metrics (impressions, clicks, conversions, cost) | Digital > Overview |
| `q9_digital_interactions.csv` | Key Interactions by category and conversion name | Digital > Interactions |
| `q10_digital_geo.csv` | Digital geographic performance by region | Digital > Geography |
| `q11_digital_creative.csv` | Creative performance (ads, copy, images, landing pages) | Digital > Creative |
| `q11_digital_keywords.csv` | PPC keyword performance | Digital > Creative |
| `q12_digital_notes.csv` | Optimization notes and performance insights | Digital > Insights |
| `roi_goals.csv` | Institution goals (placeholder) | ROI Overview (progress bars) |

### Migration from old queries

| Old CSV | New source | Status |
|---|---|---|
| `q1_funnel_kpis.csv` | Q6 aggregated | ⚠️ Retire |
| `q2_campaign_cost.csv` | Stays as Q2 | ✅ Keep — cost data |
| `q3_geography.csv` | Stays for city detail | ✅ Keep — city data |
| `q4_monthly_trending.csv` | Q6 aggregated | ⚠️ Retire |
| `q5_monthly_source_trending.csv` | Q6 by origin_source_first | ❌ Retire |
| `q7_programs.csv` | Q6 by program_name | ⚠️ Retire — merged into Q6 |

---

## Additional Data Files

| File | Source | Purpose |
|---|---|---|
| `data/roi_goals.csv` | Google Sheets export | Institution-level goals by program. Columns: Program, Inquiry Goal, App Starts Goal, App Submit Goal, Admit Goal, Deposit Goal, Net Deposit Goal. **⚠️ Values appear to be placeholder data — all programs show identical goals (1000/1000/900/850/700/650). Awaiting team confirmation.** |

---

## Open Issues

1. **Program name in Q6 — multi-program counting (documented, by design):** When Q6 is grouped by program_name, a student who applied to 2 programs counts in both. This inflates per-program inquiry totals vs institution total. This is correct for program-level ranking analysis. The Programs tab does NOT show total KPI cards or sum rows — only per-program rankings — so the multi-count is never visible as an inconsistency. Do not add a grand total row to the Programs tab.

2. **Two different "source" concepts in the dashboard (clearly separated now):**
   - `origin_source_first` (from Q6/funnel_benchmark_current) = where the student originally came from (College Fair, College Board, CWU CIHS, Campus Event, RFI Forms, etc.). First-touch, deduplicated. **Used for: Source Performance table, Source Trend chart, Conversion Rates by Source** — all on Funnel Deep Dive page.
   - `campaign_product_group` / `lead_source` (from Q2/campaign_roi) = which Carnegie marketing channel touched the student (Programmatic Display, Clarity, Paid Search, Paid Digital). Multi-touch. **Used for: cost calculations only** (Cost per Net Deposit badge). Not displayed as a source breakdown visual.
   - The Asana task "Replace Product Group with Lead Source" is resolved by this migration — the dashboard now shows `origin_source_first` (Slate lead source) instead of `campaign_product_group`.

3. **Goal data validation** — roi_goals.csv has placeholder values (1000/1000/900/850/700/650 identical across programs). Danielle confirmed in March 19 meeting: "just entirely made up by me as I was trying to get some numbers in there." Team needs to confirm real CWU goals. Long-term plan: goals will be entered in Tinman, not Google Sheets.

4. **Unknown geography data** — ~4,950 inquiry records have NULL/empty state (`region`). Investigate whether this is students without U.S. addresses or a data quality issue.

5. **Digital Performance queries** — Data source received from Ry (March 18). Queries not yet built. Anderson mentioned meeting with strategists (Denise, Katie) to determine which metrics to prioritize. May need multiple pages or tabs per Danielle's feedback.

6. **CSV → BigQuery migration** — Current dashboard reads from CSV extracts. Live BigQuery connection is a future step. Queries should remain unchanged; only the data loading layer in Python changes.

7. **Q6 vs Q1 counting difference (documented, resolved):** Q6 shows slightly higher numbers for App Starts onward because `funnel_benchmark_current` uses the correct dbt logic: `COALESCE(app_student_type, person_student_type)` for application stages, while Q1 used `COALESCE(person_student_type, app_student_type)` for all stages. Difference: ~109 applications where person=Transfer but app=First Year. Q6 is correct — matches Slate dashboard. Q1 is retired.

8. **Melt rate metric** — Greg asked in March 19 meeting about adding a melt rate card (deposits lost between deposit and enrollment). Danielle said she'll check with strategists (Denise, Katie) if it's useful for clients. Not implemented yet — pending feedback.

9. **Scaling question** — Greg asked about scaling from 1 client to 10/20/100. Architecture is institution-agnostic (Institution filter in sidebar), but performance and deployment need assessment. Backlog item.

10. **Deployment** — Currently running on local machine. Need to identify Carnegie infra team for deployment (Shiny for Python on Linux/Docker/Posit Connect). Backlog item.

11. **Campaign history gap for CWU (open — engineering):** CWU has no campaigns registered in BigQuery before 2024-04-01, resulting in 98.7% of Fall 2026 First Year inquiries having no campaign attribution. Engineering needs to investigate whether pre-2024 campaign data was never imported or simply doesn't exist. Tracked in Asana. This does not affect dashboard correctness — Q6 uses the full funnel regardless of campaign coverage.