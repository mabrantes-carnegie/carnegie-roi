## Project Context

- Project type: Carnegie dashboards in Shiny for Python
- IDE context: Claude Code inside VS Code
- Primary goal: build production-ready, brand-consistent dashboards for Carnegie
- Prefer concise, maintainable, reusable code
- Preserve current working behavior unless the task explicitly asks for refactor

## Framework — Shiny for Python

- Prefer Shiny Express for new simple modules and prototypes
- Use Shiny Core when the app requires more layout/control flexibility
- Never mix Shiny Express and Shiny Core syntax in the same file
- Default Express imports:
  - `from shiny.express import input, render, ui`
- Prefer:
  - `@reactive.calc` for derived values
  - `@reactive.effect` for side effects
- Use `req()` to guard outputs and reactive logic when inputs/data are not ready
- Prefer shared helpers for repeated layout/styling patterns

## UI and Layout

- Prefer Shiny/bslib-native components first
- Prefer `ui.layout_sidebar()` / `ui.sidebar()` for sidebar layouts
- Prefer `ui.card()` to wrap charts and tables
- Prefer `ui.value_box()` for KPI metrics
- Prefer reusable wrapper helpers in `app.py` for width, padding, and alignment
- Use CSS only for fine-grained brand/layout adjustments that are hard to express in Shiny components
- Do not stack CSS hacks repeatedly; remove conflicting rules before adding new ones

## Visual Identity — Carnegie Brand

Always follow Carnegie brand guidance for dashboards and data products.
Reference: `docs/carnegie-brand.md`

### Primary Colors
- Carnegie Red: `#EA332D`
- Carnegie Blue: `#021326`
- Off White: `#F8F4F0`
- Carnegie Gold: `#C99D44`

### Typography
- Headlines / display text: Lora Thin / Light
- Body / UI: Manrope
- Numeric emphasis in charts when needed: Inter

### Brand Rules
- Use HEX values in digital/dashboard contexts
- Do not assign semantic meaning to secondary colors
- Use Lora only for display/headline text
- Use Manrope for filters, tabs, labels, cards, tables, and UI text
- Keep visual hierarchy clean, premium, and spacious
- Prefer theme/tokens first, CSS second

## Data Layer

- Data source: BigQuery via Python client
- Load static/shared data outside reactive context when appropriate
- Load filtered/reactive data inside `@reactive.calc`
- Keep data access separate from UI logic
- Prefer:
  - `data/` for loaders and query logic
  - `app/` for UI and reactive app structure
- Avoid embedding SQL directly in UI files unless trivial

## File Organization

- `app.py`: main Shiny app entry point
- `www/`: CSS, JS, images, fonts
- `data/`: loaders, query helpers, transformations
- `docs/`: brand guidance, data contracts, dashboard notes
- `.claude/skills/`: reusable local skills for Shiny, Carnegie brand, UI patterns

## Claude Code Working Rules

- Read the relevant file(s) fully before editing
- Prefer the smallest working change that solves the task
- Preserve existing working behavior outside the requested scope
- When debugging UI/layout:
  - identify the real controlling wrapper first
  - prefer one clean fix over multiple layered hacks
- When changing CSS:
  - remove conflicting old rules
  - verify visually in browser before concluding
- When changing layout:
  - prefer structure changes in `app.py` over brute-force CSS
- Do not claim success based only on code edits; validate visually or by app behavior

## Skills and Extensions

- Use local Shiny skills from `.claude/skills/` when relevant
- Use UI/UX skills for dashboard polish, hierarchy, spacing, typography, and design system consistency
- If persistent memory tooling is enabled, use it for project continuity, decisions, and prior fixes
- Treat external skills/plugins as accelerators, not as substitutes for project-specific rules

## Safe Editing Rules

- Do not rewrite large sections unnecessarily
- Do not introduce new dependencies unless justified
- Do not change brand tokens without updating the brand reference
- Do not mix layout experiments with unrelated refactors
- For navbar/layout tasks, fix one problem at a time:
  - width first
  - alignment second
  - polish third

## Definition of Done

A task is only done when:
- code is updated cleanly
- no conflicting rules remain
- app still runs
- requested visual/functional behavior is actually verified
- changes stay consistent with Carnegie brand

## Product Design Reference
- Full dashboard architecture, page blueprints, KPI governance, filter strategy,
  and UX/UI rules are in `docs/roi-dashboard-design.md`
- Current build scope, data constraints, and implementation boundaries are in
  `docs/roi-current-scope.md`
- Consult these docs before making structural decisions about pages, metrics,
  layout hierarchy, or filter placement
- Do not contradict decisions documented there unless explicitly asked