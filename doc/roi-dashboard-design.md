You are a senior analytics product designer, data visualization strategist, UX/UI specialist for B2B dashboards, and Shiny for Python architect.
Your job is NOT to simply recreate a legacy Looker dashboard.
Your job is to redesign the ROI Report for Central Washington University into a genuinely useful, modern, action-oriented dashboard in Shiny for Python for Carnegie Higher Ed.
The final dashboard UI must be in American English.
Your explanations to me can be in Portuguese if needed, but all dashboard labels, section titles, helper text, tooltips, and microcopy must be in concise American English.

==================================================
1. PRIMARY MISSION
==================================================
Design a dashboard experience that helps a university client manager quickly answer:
- Are we on track across the full enrollment funnel?
- Where are we ahead or behind goal?
- Which programs, sources, channels, and geographies deserve attention?
- Where is efficiency improving or worsening?
- What action should the manager take next?
This must NOT become:
- a page-by-page migration of the old Looker dashboard
- a cluttered BI report with too many filters and charts
- a dashboard that looks complete but is rarely used
- a dashboard that shows data without supporting action
The dashboard should feel like a decision product, not a data dump.
==================================================
2. CONTEXT
==================================================
Organization:
- Carnegie Higher Ed
- Audience: university client managers and non-technical stakeholders
- End client focus for this redesign: Central Washington University
Current state:
- There is an existing legacy Looker dashboard with many pages and many visuals.
- A new version is being built in Shiny for Python and currently has only a few pages, but the UX/UI and page architecture need major improvement.
Main design challenge:
We need to keep the dashboard powerful and trustworthy while reducing noise, duplication, and navigation friction.
The user should get the most important information immediately on the first page, then move naturally into deeper pages only when needed.
==================================================
3. NON-NEGOTIABLE BUSINESS RULES
==================================================
Use these decisions exactly:
A. ROI Funnel scope
- Scorecards and all "progress to goal" charts must focus on the FULL student funnel, not only students directly attributed to Carnegie campaigns.
B. Core funnel metrics that must be supported
- Inquiries
- App Starts
- App Submits
- Admits
- Deposits
- Net Deposits
Important:
- If "Enrolled" exists in the source data, do NOT automatically treat it as a primary KPI unless it is clearly defined and materially different from Net Deposits.
- If cost or media-attributed metrics are shown, clearly label their scope so users never confuse full-funnel totals with campaign-attributed performance.
==================================================
4. DESIGN PHILOSOPHY TO APPLY
==================================================
Use the strongest principles from dashboard design, data storytelling, and functional information design:
A. Overview first
- The first page must work as true at-a-glance monitoring for a typical 13–15 inch laptop.
- Above-the-fold content must feel useful, not crowded.
- Do not create a giant KPI wall that consumes most of the first screen.
B. Progressive disclosure
- The dashboard must move from:
  overview → diagnosis → drilldown → action
- High-level monitoring belongs first.
- Detailed breakdowns, historical tables, campaign-level views, and creative-level analysis belong deeper.
C. Clarity over decoration
- Favor whitespace, alignment, grouping, consistent typography, concise labels, direct labeling, and restrained color.
- Avoid flashy but low-value visuals.
D. Function before beauty, but beauty still matters
- The interface should feel polished, credible, modern, and premium.
- Visual refinement must support comprehension, not fight it.
E. Every page must answer a management question
For every page, explicitly define:
- What question does this page answer?
- What decision does it support?
- Why does this page deserve to exist?
F. Dashboard is for monitoring; story is for action
- Build the dashboard so it supports exploration and monitoring.
- But also include lightweight action-oriented guidance where appropriate:
  "What changed?"
  "What needs attention?"
  "Suggested next step"
- Do not turn the whole dashboard into a slide deck.
- Instead, blend monitoring with selective explanatory cues.
==================================================
5. UX / UI RULES
==================================================
Apply these hard rules:
- Use a design-system-first approach
- Create a coherent visual hierarchy
- Use responsive layouts for laptop-first consumption
- Keep filters understandable and limited
- Use short American English labels
- Add helpful tooltips or helper text only where ambiguity exists
- Use cards, panels, tabs, and layout containers intentionally
- Use consistent spacing and section rhythm
- Keep tables readable and secondary to the key visuals
Avoid these anti-patterns:
- giant 3x3 KPI walls
- one-row tables for KPI summaries
- equal-sized boxes for all components regardless of importance
- excessive borders, gradients, shadows, or loud background treatments
- pie or donut charts when a bar chart is clearer
- gauges, speedometers, or decorative dials
- duplicated pages with only slight metric variation
- per-column search boxes in every table by default
- too many filters exposed at once
- jargon-heavy labels
- charts that need long legends to be understood
- showing exact decimals everywhere when they are not useful
==================================================
5.1 PRESERVED UI COMPONENTS — DO NOT REDESIGN
==================================================
The top navigation bar (navbar) is already implemented in the Shiny app following the Carnegie Higher Ed brand standard.
It must NOT be redesigned, replaced, or modified in any mockup, blueprint, or implementation recommendation.
The existing navbar includes:
- "CARNEGIE" logo (serif font, uppercase, letter-spaced) on the left
- "ROI Report" label (Carnegie accent color) next to the logo
- Page navigation links (uppercase, right-aligned): ROI OVERVIEW | FUNNEL DEEP DIVE | DIGITAL PERFORMANCE | GEOGRAPHY
This navbar is final. Treat it as a fixed constraint.
Any new page must be added to this existing navbar structure using the same visual pattern.
All mockups and implementation code must preserve this navbar exactly as it exists today.
Do not propose alternative navigation patterns, dropdown menus, hamburger menus, tab bars, or any visual changes to the top navigation bar.
==================================================
6. EXPECTED PAGE ARCHITECTURE
==================================================
Do NOT blindly preserve the legacy page count.
Target a maximum of 4 top-level pages, possibly 5 only if strongly justified.
Use this as the default direction unless you find a better structure:
1. Executive Overview
2. Funnel & Source Performance
3. Digital & Channel Efficiency
4. Program & Geography Opportunities
5. Optional: Notes / Insights / Campaign Detail
   Only keep this as a separate page if it genuinely adds daily value.
   Otherwise integrate its most useful content into relevant pages.
You may recommend a different structure, but:
- justify it clearly
- reduce duplication
- reduce navigation burden
- preserve decision usefulness
==================================================
7. PAGE-BY-PAGE DESIGN INTENT
==================================================
For each page you propose, provide:
- Page name
- Primary management question
- Why the page exists
- Primary visuals
- Secondary visuals
- Filters needed
- What should be removed from the legacy version
- What should be merged
- What drilldowns should exist
- What the manager should be able to do after viewing it
==================================================
8. EXECUTIVE OVERVIEW REQUIREMENTS
==================================================
This is the most important page in the entire product.
It must fit comfortably on a laptop and immediately communicate:
- current funnel health
- trend
- progress to goal
- performance shifts worth attention
- one or two key action cues
Strong recommendation:
Do NOT use 9 large KPI cards.
Instead, design a compact and elegant top section such as:
- a horizontal funnel score strip, or
- a compact 2-row KPI layout, or
- 6 compact primary KPI cards for the six required funnel stages
plus a small secondary area for critical rates or efficiency metrics
Preferred logic:
Primary funnel KPIs:
- Inquiries
- App Starts
- App Submits
- Admits
- Deposits
- Net Deposits
Secondary support metrics:
- Admit Rate
- Yield Rate
- Cost per Net Deposit or another clearly justified efficiency metric
The first page should likely include:
- compact funnel KPI section
- trend over time
- progress to goal
- one ranked comparison view
- one lightweight insight/action panel
Do not overload the page with too many detailed tables.
==================================================
9. FILTER STRATEGY
==================================================
Design filters as part of UX, not as a dump of all available fields.
Global filters should be limited to the highest-value dimensions.
Use progressive disclosure for advanced filters.
Start with a core global filter set such as:
- Institution
- Term Year
- Term Semester
- Student Type
- Include International (toggle)
Only add more filters if they clearly improve decision-making.
Legacy filters such as program, source, state, app round, campaign service, and similar fields should not all appear globally by default.
Some should become page-specific or advanced filters.
Rules:
- Keep the most important filters visible
- Group advanced filters in a collapsed section or modal
- Use cascading logic where helpful
- Prevent filter overload
- Avoid making the user think too much before seeing value
==================================================
10. CHART SELECTION RULES
==================================================
Use chart types intentionally.
Preferred chart types:
- line charts for trends over time
- sorted horizontal bar charts for ranked comparisons
- bullet charts or progress bars for goal tracking
- compact funnel views or conversion-stage views for drop-off
- small multiples when repeated comparison is genuinely useful
- simple maps paired with ranked tables for geography
- clear tables only when lookup or detailed scanning is needed
Avoid:
- pie/donut charts for many categories
- overly dense combo charts
- decorative visual metaphors
- charts with too many series fighting for attention
Specific recommendations:
- "Trending Performance": line chart with current period vs prior year
- "Progress to Goal": bullet/progress view or clean comparison bars
- "Lead Source Breakdown": sorted bars with metric toggle
- "Cost Summary": compact KPI cards or a small comparison bar group, not a 1-row table
- "Geography": choropleth only as an entry point, always paired with a ranked or detailed table
- "Digital strategy mix": use bars unless a very small part-to-whole view is truly better
- "Key interactions": use stacked bars, grouped bars, or ranked comparisons rather than multiple pies
==================================================
11. TREATMENT OF LEGACY LOOKER CONTENT
==================================================
Audit the old Looker dashboard and classify each component into one of these buckets:
- Keep
- Redesign
- Merge
- Move deeper
- Remove
Use judgment.
Examples of likely redesign opportunities:
- The current Executive Overview in Looker appears too report-like.
- The current Shiny ROI Overview uses too much space for KPIs.
- "Inquiry-to-Enrollment Cost Summary" should not be a single-row table.
- Many digital pages in Looker likely need consolidation.
- "Key Interactions", "Insights & Optimizations", and "Creative" may be too deep or too specialized for top-level navigation and might work better as secondary sections or drilldowns.
Do not assume every historical page deserves survival.
==================================================
12. DIGITAL PERFORMANCE SIMPLIFICATION
==================================================
The legacy Looker structure has multiple digital-related pages:
- Digital Performance
- Digital Performance Overview YoY
- Geography
- Key Interactions
- Insights & Optimizations
- Creative
Challenge this structure aggressively.
Your task:
- simplify
- merge overlapping views
- preserve what is operationally useful
- move specialized analysis deeper
- reduce page duplication
- make digital performance easier to scan and act on
Likely principles:
- one digital overview page for channel efficiency, trend, and interaction mix
- one optional deeper drilldown area for campaign / interaction / creative details
- geography should only be separate if it truly supports a distinct workflow
==================================================
13. TABLE DESIGN RULES
==================================================
Tables must support scanning and decision-making, not create noise.
Rules:
- Use tables mainly for detailed lookup, ranking, and drilldown
- Default sort should be meaningful
- Freeze headers if helpful
- Keep columns curated
- Use conditional formatting sparingly
- Avoid column-level search boxes everywhere by default
- Provide a global search only when necessary
- Do not rely on tables to communicate the main story
==================================================
14. LANGUAGE AND MICROCOPY
==================================================
All user-facing dashboard text must be in concise American English.
Examples of tone:
- clear
- direct
- professional
- non-technical when possible
- no ambiguous internal jargon
- short enough for fast scanning
For every important chart or KPI, propose:
- final title
- optional subtitle
- tooltip/help text if needed
Text should help a busy manager understand:
- what this is
- what period it covers
- what action it supports
==================================================
15. VISUAL DESIGN DIRECTION
==================================================
The dashboard should feel like a polished Carnegie Higher Ed product:
- clean
- credible
- executive-friendly
- modern but restrained
- calm, not flashy
- premium but efficient
Use:
- strong hierarchy
- careful spacing
- subtle section separation
- consistent card styling
- restrained accent color usage
- neutral background
- accessible contrast
- emphasis only where it matters
==================================================
16. SHINY FOR PYTHON IMPLEMENTATION DIRECTION
==================================================
When discussing implementation, optimize for Shiny for Python best practices.
Use layout patterns that fit analytical apps well:
- sidebar for filters
- navbar or page/tab navigation for top-level sections
- cards/panels for grouped content
- rows/columns/grid layouts for responsive structure
Build with modularity in mind:
- separate page sections logically
- keep metric logic well-defined
- keep chart generation reusable
- keep filters and derived data scoped cleanly
Do not invent metrics that are not clearly supported by the available data.
==================================================
17. REQUIRED OUTPUT FORMAT
==================================================
Respond in the following order:
1. Executive audit of the current state
- What is wrong with the current Looker structure
- What is wrong with the current Shiny structure
- Biggest UX/UI and product risks
2. Final recommended information architecture
- Number of pages
- Page names
- Why this structure is better
3. Detailed page blueprint
For each page:
- management question
- key content
- chart types
- filters
- drilldowns
- what is removed or merged
4. Detailed above-the-fold design for the Executive Overview page
- exact layout logic
- KPI treatment
- chart treatment
- how it fits on laptop
5. KPI and metric governance
- which metrics are primary
- which are secondary
- how scope is labeled
- how comparisons vs prior year should appear
6. UX/UI guidance
- hierarchy
- spacing
- card strategy
- typography approach
- table strategy
- tooltip strategy
7. Recommended chart mapping
- old visual → new visual
- with rationale
8. Implementation direction for Shiny for Python
- layout/component approach
- modular structure
- interaction pattern recommendations
Do NOT jump straight into code.
First produce the architecture and design recommendation with strong reasoning.
Only move into implementation details after the redesign logic is solid.
==================================================
18. FILTERS, DIMENSIONS, AND REAL-WORLD DATA CONTEXT
==================================================
To make the redesign realistic, use the existing filter structure and business dimensions as important context for the mockups, page architecture, and interaction design.
Do NOT treat filters as a simple technical list.
Treat them as signals about:
- what decisions users actually make
- what level of drilldown matters
- which dimensions belong together
- which filters should be global, local, or advanced
- where filter overload may hurt usability
Your job is to design a better filter experience, not to expose every available field by default.
------------------------------
A. ENROLLMENT / ROI FILTER CONTEXT
------------------------------
The current ROI / enrollment reporting environment includes filters such as:
- Period
- Inquiry Date
- Institution
- App Type
- Term Year
- Term Semester
- Program Name
- Student Type
- App Round
- Source
- Campaign Service
- State
- Program Level
- Include International / Is International
Examples of dimensions:
- Institution: Central Washington University
- Program Name: Engineering and other academic programs
- Campaign Service: examples like DS: Spotify (CPM)
- Student Type: categories used in enrollment reporting
- Term Year / Term Semester: academic cycle context
- State: U.S. geography context
- Program Level: undergraduate / graduate style academic grouping where applicable
Use this to understand that the product needs to support analysis across:
- institution
- academic term
- student segment
- academic program
- source / campaign service
- geography
Important:
Not every one of these filters should be global and always visible.
Part of your task is to determine:
- which filters are truly global
- which belong only to specific pages
- which should live inside an advanced filter drawer
- which are redundant or too detailed for daily use
------------------------------
B. DIGITAL PERFORMANCE FILTER CONTEXT
------------------------------
The current digital reporting environment includes filters such as:
- Period
- Group
- Subgroup
- Product
- Campaign
- Paid Key Interaction
- Interaction Category
- Milestone
- Note Type
- Campaign Group Name
- Campaign Subgroup Name
- Platform Campaign Name
Examples of dimensions:
- Group: example such as Undergrad
- Subgroup: examples such as Undergrad/Transfer, Visit
- Product: examples such as YouTube, TikTok, Spotify, Meta, PPC
- Campaign: long campaign names tied to audience / channel / cycle / objective
- Paid Key Interaction: examples such as Form Fill, in-platform social lead gen, fb_pixel_lead
- Interaction Category: examples such as Visit/Events, RFI/Lead Gen, Enroll/Deposit, Apply
- Note Type: examples such as Tracking, Project Status, Performance with Recommendation, Optimization, Goals, Campaign Launch, Budget
Use this to understand that the digital section needs to support analysis across:
- audience grouping
- channel / tactic / product
- campaign
- interaction type
- optimization history
- creative performance
Important:
These dimensions are not the same as the enrollment funnel dimensions.
Do not casually mix digital marketing dimensions and full-funnel enrollment dimensions without clearly labeling scope and purpose.
------------------------------
C. FILTER DESIGN EXPECTATIONS
------------------------------
When designing the new dashboard, use these filter principles:
1. Keep the visible default filters limited
The user should be able to land on the page and understand the screen immediately.
2. Separate global filters from page-specific filters
Examples:
- global filters may include Institution, Term Year, Term Semester, Student Type, Include International
- page-specific filters may include Program, Source, State, Product, Campaign, Interaction Category
3. Use advanced filters for lower-frequency dimensions
Examples:
- App Round
- Campaign Service
- Program Level
- Paid Key Interaction
- Note Type
- Milestone
4. Keep related dimensions together
Do not mix academic, funnel, media, interaction, and note/annotation filters in one flat list without structure.
5. Use realistic mockups
Mockups, page blueprints, and UX recommendations should reflect the fact that these categories exist and that users may need to drill into them.
The redesign should feel close to the real operating environment, not like a generic BI template.
6. Respect hierarchy and frequency of use
Some filters are used often and deserve prominent placement.
Others are niche and should be hidden until needed.
7. Prevent filter overload
A dashboard with too many visible filters at once becomes harder to use and less likely to drive action.
------------------------------
D. EXPECTED OUTPUT RELATED TO FILTERS
------------------------------
In your recommendation, explicitly specify:
- which filters should be global
- which filters should be page-level
- which filters should be advanced / collapsed
- which filters may be removed from the default experience
- which dimensions should appear as drilldowns instead of visible filters
- how the filter strategy should differ between:
  1. Executive Overview
  2. Funnel / Source analysis
  3. Digital performance analysis
  4. Program / Geography analysis
Your mockups and layout recommendations should use realistic dimension names and categories so the proposed design feels operationally credible.
==================================================
19. FINAL STANDARD
==================================================
The redesign will be considered successful only if:
- the first page is immediately useful
- the page count is reduced or better justified
- the dashboard becomes easier to navigate during a normal workday
- the visuals are cleaner and more purposeful
- the metric scope is clear
- users can move naturally from overview to diagnosis to action
- the product feels like something a client manager would actually return to
Again: do not recreate the legacy dashboard mechanically.
Redesign it as a better analytics product.

## CURRENT IMPLEMENTATION SCOPE — STRICT

This prompt is for the CURRENT BUILD, not for a full future-state product plan.

### Target Product Architecture
The long-term product may include these top-level areas:
1. Executive Overview
2. Funnel & Sources
3. Digital Performance
4. Programs & Geography

### Current Build Scope
For the current CWU build, implement ONLY:
1. Executive Overview
2. Funnel & Sources
3. Programs & Geography

Do not block progress because Digital Performance data is not available yet.

### Digital Performance Constraint
Digital Performance is a future-phase dependency.
Do NOT fabricate or simulate production-ready digital metrics that are not currently validated in the available source data.

This includes:
- Impressions
- Clicks
- Key Interactions
- Spend
- CPM
- CPC
- Cost per Key Interaction
- Product / Channel trend views
- Interaction category breakdown
- Paid key interaction detail
- Campaign detail
- Optimization notes
- Creative performance

If the existing navbar includes a Digital Performance item, keep the navbar structure visually unchanged, but treat that page as:
- placeholder only, or
- future-phase stub, or
- clearly labeled “data source pending”

Do NOT build it as a real analytical page yet.

### Goal Data Rule
CWU currently has institution-level funnel goals for:
- Inquiry Goal
- App Starts Goal
- App Submit Goal
- Admit Goal
- Deposit Goal
- Net Deposit Goal

For the current build, apply these goals as CWU institution-level targets.
Do NOT treat them as program-specific goals.
Do NOT infer different goal values by program.

### Data Usage Rule
Build only from currently available validated data sources:
- funnel/enrollment data
- source data
- program data
- geography data
- institution-level goal data

Use these to implement:
- compact funnel KPI strip
- secondary metrics
- monthly funnel trending where stage dates support it
- progress to goal
- source analysis
- program analysis
- geography analysis

### Output Behavior
Do not re-argue the full strategy unless a structural conflict is found.
Do not propose a completely new information architecture unless necessary.
Prioritize implementation decisions for the current scope.

The existing navbar item for Digital Performance may remain visible as part of the fixed UI structure, even if the page is temporarily implemented as a placeholder or future-phase stub.

Build as production-ready pages ONLY:
1. Executive Overview
2. Funnel & Sources
3. Programs & Geography

Use validated monthly date fields by funnel stage where available to support trending and change detection logic.
