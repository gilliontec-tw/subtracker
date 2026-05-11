# Phase 3: Reports & Subscription Filtering - Context

**Gathered:** 2026-05-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix the multi-currency chart rendering bug in reports, eliminate the remaining `annual_cost()` duplicate in the route layer, and add a department cost analysis section. SUBSCR-02 (subscription filtering) is already implemented via front-end JS and only requires a verification pass — no new code.

**In scope:**
- REPORT-01: Render one donut + bar chart pair per currency (currently only `sections[0]` gets a chart)
- REPORT-02: Verify `subscriptions.py` report route uses `subscription.annual_cost()` from the domain entity — remove any remaining inline duplicate
- REPORT-03: Add department cost analysis section to reports page (per-currency annual totals, sorted by highest, top department highlighted)
- SUBSCR-02: Verify the three existing JS filters (department, category, status) work correctly — manual smoke-test, no code changes expected

**Out of scope:**
- URL state / bookmarkable filters — deferred
- Using admin-configured ConfigOption as filter source (derived-from-subscriptions approach is acceptable for now)
- Category breakdown within department (flat dept totals only)
- Cross-currency dept aggregation (show per-currency, consistent with category tables)

</domain>

<decisions>
## Implementation Decisions

### REPORT-01: Multi-currency charts

- **D-01:** One full chart pair (donut + bar) per currency section, each pair rendered above its detail table. No toggle or tab — each currency is independently visualized inline.
- **D-02:** Canvas IDs follow the pattern `donutChart-{currency}` (e.g., `donutChart-TWD`, `donutChart-USD`). Generated in a Jinja2 loop — no hardcoded single `donutChart` canvas.
- **D-03:** Both the donut (category breakdown) AND bar (category ranking) charts render per currency. Full pair per currency, not just donut-only for secondary currencies.
- **D-04:** Chart data embedded per-currency inline in Jinja2: each section dict in the route exposes `cat_labels_json`, `cat_values_json`, and `cat_colors_json` (JSON strings, `|safe` filter). The current global `catLabels`, `catValues` JS variables are replaced by per-section equivalents in the loop.

### REPORT-02: annual_cost() cleanup

- **D-05:** The reports route (`subscriptions.py`) must call `subscription.annual_cost()` from the domain entity for all cost calculations. If any inline `annual_cost` function still exists in the route file, remove it. (Phase 1 D-09/D-10 already extracted the method to `Subscription` entity.)

### REPORT-03: Department cost analysis

### Claude's Discretion
- **Placement:** New card section at the bottom of the reports page, after all per-currency detail tables.
- **Structure:** Per-currency department breakdown (same pattern as per-currency category tables). For each currency: annual total per department, subscription count, sorted by highest cost. Top department highlighted with a badge.
- **Detail level:** Flat totals only — no category breakdown within departments.
- **Cross-currency:** No aggregation across currencies. Show separate dept breakdown per currency (consistent with how category tables work).

### SUBSCR-02: Filter verification

- **D-06:** SUBSCR-02 is already implemented. The subscription list (`index.html`) has working department, category, and status filter dropdowns with JS `applyFilters()`. Requirement passes with a manual smoke-test confirming all three filters function correctly; document in the plan SUMMARY. No code changes expected.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Planning Docs
- `.planning/ROADMAP.md` — Phase 3 goal, success criteria, requirements list (REPORT-01, REPORT-02, REPORT-03, SUBSCR-02)
- `.planning/REQUIREMENTS.md` — Full requirement specs for REPORT-01 through SUBSCR-02

### Reports Page (primary change surface)
- `src/interfaces/web/templates/reports.html` — Current template; chart bug is the single hardcoded `<canvas id="donutChart">` and the single `new Chart(...)` call in `{% block scripts %}`; fix requires looping both
- `src/interfaces/web/routes/subscriptions.py` — `/reports` route handler; currently passes `cat_labels_json`, `cat_values_json`, `cat_colors_json` as top-level context vars for `sections[0]` only; needs to move these into each section dict + add dept breakdown data

### Subscription List (verification only)
- `src/interfaces/web/templates/index.html` — Has existing `applyFilters()` JS and three filter dropdowns; read to verify data-attributes on rows match filter logic

### Domain Layer
- `src/domain/entities/subscription.py` — `annual_cost()` method (added in Phase 1); all cost calculations must call this
- `.planning/phases/01-foundation-security/01-CONTEXT.md` — D-09/D-10: `annual_cost()` extraction decision context

### Codebase Maps
- `.planning/codebase/CONVENTIONS.md` — Template/UI conventions, option list patterns, zh-TW UI language
- `.planning/codebase/STRUCTURE.md` — Where to add new route logic, template layout

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `reports.html` KPI card loop (`{% for sec in sections %}`) — already iterates all currency sections; the chart block needs to move inside this same loop pattern
- `cat_colors` dict and `CAT_COLORS` JS constant — already passed as context; per-section approach embeds `sec.cat_colors_json` inline, same data per currency
- Existing `chart-grid-2` CSS class — reuse for each per-currency chart pair; no new CSS needed

### Established Patterns
- Per-currency section data structure in the route: `sections` is a list of dicts with `currency`, `total_annual`, `total_monthly`, `count`, `categories`; extend each dict with `cat_labels_json`, `cat_values_json`, `cat_colors_json`, and a new `departments` list
- `subscription.annual_cost()` call pattern — already used elsewhere after Phase 1; reports route must match
- `_to_entity` / route data assembly pattern: all report data built in the route handler from `repo.list_all()` result; add dept grouping in the same loop

### Integration Points
- `subscriptions.py` `/reports` route: the only file that needs code changes for REPORT-01, REPORT-02, REPORT-03
- `reports.html`: template changes to loop chart rendering and add dept section at bottom
- `index.html`: read-only verification pass (no edits expected)

</code_context>

<specifics>
## Specific Ideas

- The chart bug fix is entirely in the template: move `<canvas id="donutChart">` and the `new Chart(...)` call into the `{% for sec in sections %}` loop; use `donutChart-{{ sec.currency }}` as the canvas id; use `sec.cat_labels_json` / `sec.cat_values_json` / `sec.cat_colors_json` (to be added to the route) instead of the top-level vars.
- The bar chart (category ranking) uses a Jinja2 bar-row loop — no Chart.js — so it naturally renders per currency already if moved inside the `{% for sec in sections %}` block. Only the donut canvas needs JS changes.
- Department section heading in zh-TW: `部門費用分析`; top-department badge label: `費用最高`

</specifics>

<deferred>
## Deferred Ideas

- **URL state for filters** — bookmarkable filter links (?dept=IT&status=active). Deferred — the current JS-only approach is sufficient for internal use.
- **Admin-configured filter options** — using ConfigOption entity as the source for category/dept dropdowns instead of deriving from subscription data. Deferred — current approach works for the current data volume.
- **Category breakdown within departments** — showing which categories a department spends on. Deferred — flat dept totals are sufficient for REPORT-03.
- **CSV export with dept filter** — exporting only subscriptions matching the current filter selection. v2 requirement.

</deferred>

---

*Phase: 3-Reports & Subscription Filtering*
*Context gathered: 2026-05-11*
