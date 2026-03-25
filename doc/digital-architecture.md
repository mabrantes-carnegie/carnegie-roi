# Digital Performance — Architecture & Query Plan

## Data Source

All digital data lives in BigQuery project: `carnegie-dartlet-1528198422380.tinman`

### Tables

| Table | Purpose | Key unique fields |
|---|---|---|
| `v_kpi_campaign` | Campaign-level metrics (impressions, clicks, conversions, cost, spend) | `day`, `product_name`, `campaign_group_name`, `campaign_subgroup_name` |
| `v_kpi_conversion` | Key Interactions breakdown by conversion type/name | `conversion` (name), `conversion_type` (category: RFI/Lead Gen, Apply, Visit/Events, etc.) |
| `v_kpi_geo` | Geographic performance (region, location) | `region`, `location` |
| `v_kpi_creative` | Creative-level performance (ad copy, images, landing pages) | `creative`, `image_url`, `ad_description`, `ad_url`, `preview_url` |
| `v_kpi_keyword` | PPC keyword performance | `keyword`, `match_type` |
| `v_opnote` | Optimization notes & performance insights | `type` (note type), `notes`, `is_milestone` |

### Common filter fields (shared across all tables)

| Field | Maps to Looker filter |
|---|---|
| `client_name` | Institution (= "Central Washington University") |
| `day` | Period |
| `campaign_group_name` | Group (e.g., "UG", "TRN", "UG + TRN") |
| `campaign_subgroup_name` | Subgroup (e.g., "UG", "Parent", "Transfer", "Computer Science") |
| `product_name` | Product (e.g., "Meta", "TikTok", "PPC", "YouTube", "Display", etc.) |
| `campaign_name` | Campaign |

### CWU Data Profile

- Date range: 2024-01-04 to 2026-03-22
- Total rows in v_kpi_campaign: 8,004
- Number of campaigns: 49
- Products: Meta, TikTok, YouTube, IP Targeting, Display, Spotify, PPC, Reddit, Mobile Location Targeting
- Groups: UG, TRN, UG + TRN
- Subgroups: UG, Parent, Transfer, Computer Science, CMGT & SHM, UG + TRN

---

## Page Architecture

Danielle confirmed Digital Performance needs multiple sub-pages. The navbar item "DIGITAL PERFORMANCE" should expand into sub-pages.

### Proposed sub-page structure (inside Digital Performance):

| # | Sub-page | Looker equivalent | Data source | Purpose |
|---|---|---|---|---|
| 1 | **Overview** | Digital Performance + Digital Performance Overview YoY (merged) | `v_kpi_campaign` | KPIs, trending, engagement metrics, channel mix, performance by strategy & subgroup |
| 2 | **Interactions** | Key Interactions | `v_kpi_conversion` | Interaction categories, trending by category, breakdown by strategy & campaign |
| 3 | **Geography** | Geography (digital) | `v_kpi_geo` | Map + table of impressions/clicks/conversions by region/location |
| 4 | **Creative** | Creative | `v_kpi_creative` + `v_kpi_keyword` | Creative performance by platform, PPC keyword performance |
| 5 | **Insights** | Insights & Optimizations | `v_opnote` | Performance notes, campaign optimization history |

### Why 5 sub-pages instead of fewer

The digital content is fundamentally different from enrollment funnel data — it's about media performance, not student progression. Each sub-page answers a distinct question:

1. **Overview**: "How are our channels performing? Where is spend going?"
2. **Interactions**: "What types of conversions are we driving? Which categories are growing?"
3. **Geography**: "Where are our ads reaching? Which regions perform best?"
4. **Creative**: "Which ads/keywords are working? What should we refresh?"
5. **Insights**: "What has the strategy team been optimizing? What do the notes say?"

These map directly to what the Looker pages showed, but we merge the two Overview pages (monthly + YoY) into one with a period toggle.

---

## Query Plan

### Q8: Digital Overview (from v_kpi_campaign)

**Export as:** `q8_digital_overview.csv`

```sql
SELECT
    client_name,
    campaign_group_name AS group_name,
    campaign_subgroup_name AS subgroup_name,
    product_name,
    campaign_name,
    day,
    EXTRACT(YEAR FROM day) AS event_year,
    EXTRACT(MONTH FROM day) AS event_month,
    FORMAT_DATE('%b', day) AS event_month_name,
    SUM(impressions) AS impressions,
    SUM(clicks) AS clicks,
    SUM(conversions) AS direct_conversions,
    SUM(view_through_conversions) AS view_through_conversions,
    SUM(conversions + view_through_conversions + leads) AS total_interactions,
    SUM(leads) AS in_platform_leads,
    SUM(cost) AS cost,
    SUM(budget) AS budget,
    SUM(followers) AS followers,
    SUM(likes) AS likes,
    SUM(shares) AS shares,
    SUM(comments) AS comments
FROM `carnegie-dartlet-1528198422380.tinman.v_kpi_campaign`
WHERE client_name = 'Central Washington University'
    AND day >= '2024-01-01'
GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9
ORDER BY day, product_name
```

**Powers:**
- Executive Overview KPIs (Key Interactions, Cost per Interaction, Impressions, Clicks, CTR)
- Trending Performance (total conversions current vs PY)
- Engagement & Spend Metrics (Budget, CPC, Direct Conversions, Cost per Direct Conversion, etc.)
- Performance by Strategy (pie chart → bars, trending by strategy)
- Performance by Subgroup table
- Performance by Strategy table
- Interactions by Month & Year
- Interactions by Strategy & Month

**Python calculates:** CTR, CPC, Cost per Interaction, Cost per Direct Conversion, Cost per In-Platform Lead, Cost per Total Conversion, Conversion Rate, YoY/MoM deltas

**CRITICAL — Cost field mapping:**
The Looker dashboard uses `budget` (not `cost`) for all cost-related metrics. Validated for CWU Feb 2026:
- Looker shows Cost per Interaction = $22.83
- `budget / total_interactions` = $22.83 ✅
- `cost / total_interactions` = $19.11 ❌

All Python cost calculations must use `budget` as the numerator:
- Budget = `SUM(budget)`
- Cost per Click = `budget / clicks`
- Cost per Interaction = `budget / total_interactions`
- Cost per Direct Conversion = `budget / direct_conversions`
- Cost per In-Platform Lead = `budget / in_platform_leads`
- Cost per Total Conversion = `budget / total_interactions`

The `cost` field is available in the data but is NOT what the Looker dashboard displays. Keep both fields in the CSV but default all dashboard calculations to `budget`.

---

### Q9: Digital Interactions (from v_kpi_conversion)

**Export as:** `q9_digital_interactions.csv`

```sql
SELECT
    client_name,
    campaign_group_name AS group_name,
    campaign_subgroup_name AS subgroup_name,
    product_name,
    campaign_name,
    conversion AS conversion_name,
    conversion_type AS interaction_category,
    day,
    EXTRACT(YEAR FROM day) AS event_year,
    EXTRACT(MONTH FROM day) AS event_month,
    FORMAT_DATE('%b', day) AS event_month_name,
    SUM(conversions) AS direct_conversions,
    SUM(view_through_conversions) AS view_through_conversions,
    SUM(conversions + view_through_conversions + leads) AS total_interactions,
    SUM(leads) AS in_platform_leads
FROM `carnegie-dartlet-1528198422380.tinman.v_kpi_conversion`
WHERE client_name = 'Central Washington University'
    AND day >= '2024-01-01'
GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11
ORDER BY day, interaction_category
```

**Powers:**
- Paid Key Interaction Categories KPIs (RFI/Lead Gen, Visit/Events, Apply, Enroll/Deposit, Other)
- Key Interaction Category Trending (time series by category)
- Key Interaction Breakdown (bar chart replacing pie)
- Key Interaction by Category & Strategy
- Breakdown by Interaction Category & Name table
- Key Interactions by Campaign Name table
- Key Interactions by Month table
- Key Interactions by Campaign & Interaction Name table

---

### Q10: Digital Geography (from v_kpi_geo)

**Export as:** `q10_digital_geo.csv`

```sql
SELECT
    client_name,
    campaign_group_name AS group_name,
    campaign_subgroup_name AS subgroup_name,
    product_name,
    campaign_name,
    region,
    location,
    day,
    SUM(impressions) AS impressions,
    SUM(clicks) AS clicks,
    SUM(conversions) AS total_conversions,
    SUM(cost) AS cost
FROM `carnegie-dartlet-1528198422380.tinman.v_kpi_geo`
WHERE client_name = 'Central Washington University'
    AND day >= '2024-01-01'
GROUP BY 1, 2, 3, 4, 5, 6, 7, 8
ORDER BY day, region
```

**Powers:**
- Inquiries by Location map
- Region/location performance table

---

### Q11: Digital Creative (from v_kpi_creative + v_kpi_keyword)

**Export as:** `q11_digital_creative.csv` and `q11_digital_keywords.csv`

**Creative:**
```sql
SELECT
    client_name,
    campaign_group_name AS group_name,
    campaign_subgroup_name AS subgroup_name,
    product_name,
    platform_campaign_name,
    campaign_name,
    creative,
    ad_description,
    ad_url,
    image_url,
    preview_url,
    segment_group AS ad_group,
    day,
    SUM(impressions) AS impressions,
    SUM(clicks) AS clicks,
    SUM(conversions) AS direct_conversions,
    SUM(view_through_conversions) AS view_through_conversions,
    SUM(leads) AS in_platform_leads,
    SUM(conversions + view_through_conversions + leads) AS total_conversions,
    SUM(cost) AS cost,
    SUM(followers) AS followers,
    SUM(likes) AS likes,
    SUM(shares) AS shares,
    SUM(comments) AS comments
FROM `carnegie-dartlet-1528198422380.tinman.v_kpi_creative`
WHERE client_name = 'Central Washington University'
    AND day >= '2024-01-01'
GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13
ORDER BY day, product_name
```

**Keywords:**
```sql
SELECT
    client_name,
    platform_campaign_name,
    campaign_name,
    product_name,
    keyword,
    match_type,
    day,
    SUM(impressions) AS impressions,
    SUM(clicks) AS clicks,
    SUM(conversions) AS direct_conversions,
    SUM(cost) AS cost
FROM `carnegie-dartlet-1528198422380.tinman.v_kpi_keyword`
WHERE client_name = 'Central Washington University'
    AND day >= '2024-01-01'
GROUP BY 1, 2, 3, 4, 5, 6, 7
ORDER BY day
```

**Powers:**
- Display Creative table (by tactic, campaign, adgroup, creative image)
- Display Creative by ad size
- PPC keyword performance table
- Meta Creative table
- LinkedIn Creative table
- YouTube Creative table
- Snapchat Creative table
- TikTok Creative table
- Spotify Creative table
- Reddit Creative table

---

### Q12: Optimization Notes (from v_opnote)

**Export as:** `q12_digital_notes.csv`

```sql
SELECT
    client_name,
    campaign_group_name AS group_name,
    campaign_subgroup_name AS subgroup_name,
    product_name,
    product_group_name,
    campaign_name,
    day,
    type AS note_type,
    is_milestone,
    notes,
    created_by
FROM `carnegie-dartlet-1528198422380.tinman.v_opnote`
WHERE client_name = 'Central Washington University'
    AND day >= '2024-01-01'
ORDER BY day DESC
```

**Powers:**
- Performance Insights & Analysis table (note_type = 'Performance' or similar)
- Campaign Optimization History table (note_type = 'Optimization' or similar)

---

## Filter Strategy for Digital Performance

### Sub-page level filters (visible at top of digital section):

| Filter | Source field | Default |
|---|---|---|
| Period | `day` range picker | Jul 1, 2025 – Jun 30, 2026 (current academic year) |
| Group | `campaign_group_name` | All |
| Subgroup | `campaign_subgroup_name` | All |
| Product | `product_name` | All |
| Campaign | `campaign_name` | All (searchable dropdown) |

### Additional filters per sub-page:

| Sub-page | Extra filters |
|---|---|
| Interactions | Paid Key Interaction (`conversion_name`), Interaction Category (`conversion_type`) |
| Insights | Milestone (`is_milestone`), Note Type (`note_type`) |
| Creative | Platform Campaign Name (`platform_campaign_name`) |

### Relationship to global filters

The global sidebar filters (Institution, Term Year, Term Semester, Student Type, Include International) apply to enrollment funnel data only. Digital Performance uses its own filter set because:
- Digital data has `day` ranges, not `term_year`/`term_semester`
- Digital data has `campaign_group_name`/`campaign_subgroup_name`, not `student_type`
- These are different data domains with different filter dimensions

The Institution filter still applies (`client_name` = selected institution).

---

## Navigation Implementation

The navbar item "DIGITAL PERFORMANCE" should show sub-pages. Options:

**Option A — Tabs within the page (recommended for Shiny):**
When the user clicks "DIGITAL PERFORMANCE" in the navbar, the page loads with a secondary tab bar below the navbar:
```
[ Overview | Interactions | Geography | Creative | Insights ]
```
This keeps the main navbar clean (4 items) and uses Shiny's `ui.navset_pill()` or `ui.navset_tab()` for the sub-navigation.

**Option B — Dropdown in navbar:**
The "DIGITAL PERFORMANCE" navbar item has a dropdown showing the 5 sub-pages. This is harder to implement in Shiny's `ui.page_navbar()` and may break the existing navbar pattern.

**Recommendation: Option A.** Matches what the Danielle described ("it may end up being multiple pages or it could be one... once you build it out we'll have a better sense"). Tabs are flexible — easy to add/remove/reorder.

---

## Implementation Priority

1. **Q8 + Overview sub-page** — highest impact, replaces 2 Looker pages
2. **Q9 + Interactions sub-page** — high value, interaction breakdown is key for strategists
3. **Q12 + Insights sub-page** — easy to build (just tables), high value for optimization history
4. **Q11 + Creative sub-page** — lots of tables, lower daily-use priority
5. **Q10 + Geography sub-page** — nice to have, can be last

Build Overview first, validate numbers against Looker, then expand.