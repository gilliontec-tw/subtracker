# Phase 3: Reports & Subscription Filtering - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-11
**Phase:** 3-Reports & Subscription Filtering
**Areas discussed:** Multi-currency charts, Filter strengthening (SUBSCR-02)

---

## Multi-currency charts (REPORT-01)

### Q1: Chart layout when multiple currencies exist

| Option | Description | Selected |
|--------|-------------|----------|
| One chart per currency (Recommended) | Each currency gets its own donut + bar chart pair, shown above its detail table. | ✓ |
| Currency-toggle tabs | Keep one chart area, add tab buttons to switch between currencies. | |
| You decide | Claude picks the simpler approach. | |

**User's choice:** One chart per currency (Recommended)

---

### Q2: Canvas ID pattern

| Option | Description | Selected |
|--------|-------------|----------|
| donutChart-{currency} | e.g. donutChart-TWD, donutChart-USD. Clear, no conflicts. | ✓ |
| donutChart-{loop.index} | Index-based. Simpler but less readable. | |

**User's choice:** donutChart-{currency}

---

### Q3: Bar chart scope

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, one bar chart per currency too (Recommended) | Keeps each currency section self-contained — full chart pair + detail table per currency. | ✓ |
| Bar chart only for the largest currency | Only the first currency gets the ranking bar chart; others get just the donut. | |

**User's choice:** Yes, one bar chart per currency too

---

### Q4: Chart data embedding strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Embedded per-currency via Jinja2 (Recommended) | Each currency's chart data rendered inline using sec.cat_labels_json etc. Consistent with current approach. | ✓ |
| Single JSON block at page top | All currencies' data as one JSON object, indexed by currency in JS. | |

**User's choice:** Embedded per-currency via Jinja2

---

## Filter strengthening (SUBSCR-02)

### Q1: What does 「補強」 mean?

| Option | Description | Selected |
|--------|-------------|----------|
| Use admin-configured options | Category and dept dropdowns use ConfigOption list instead of subscription-derived data. | |
| Add URL state (bookmarkable filters) | Persist active filters in URL query params. | |
| It's already done — just verify | The feature works as-is. SUBSCR-02 needs a verification pass only. | ✓ |

**User's choice:** It's already done — just verify

---

### Q2: What does passing look like?

| Option | Description | Selected |
|--------|-------------|----------|
| Manual smoke-test + note in SUMMARY | No code changes — just verify all 3 filters work and document. | ✓ |
| Add a unit/route test | Write a test validating data-attributes on rows. | |

**User's choice:** Manual smoke-test: confirm all 3 filters work + write a note in SUMMARY

---

## Claude's Discretion

- **REPORT-03 (Department cost analysis):** User did not select this area — full implementation details at Claude's discretion. Decisions: placement at bottom of reports page, per-currency dept breakdown, flat totals only (no category breakdown within dept), top dept highlighted with badge.
- **REPORT-02 (annual_cost cleanup):** Purely technical — verify route uses `subscription.annual_cost()`, remove any duplicate. No user decision needed.

## Deferred Ideas

- URL state for bookmarkable filters
- Admin-configured filter options (ConfigOption as dropdown source)
- Category breakdown within departments
- CSV export with active filter applied
