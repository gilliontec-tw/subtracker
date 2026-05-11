---
phase: 03-reports-subscription-filtering
plan: "01"
subsystem: reports
tags: [reports, charts, multi-currency, department-analysis, tdd]
dependency_graph:
  requires: []
  provides: [REPORT-01, REPORT-03]
  affects: [src/interfaces/web/routes/subscriptions.py, src/interfaces/web/templates/reports.html]
tech_stack:
  added: []
  patterns: [per-section JSON embedding, IIFE JS loop, TDD red-green]
key_files:
  created:
    - src/interfaces/web/templates/reports.html
    - tests/unit/test_reports_route.py
    - src/domain/entities/config_option.py
    - src/domain/repositories/config_option_repository.py
    - src/infrastructure/database/sql_config_option_repository.py
  modified:
    - src/interfaces/web/routes/subscriptions.py
decisions:
  - Extracted _build_report_sections as testable module-level helper to avoid FastAPI machinery in unit tests
  - Merged chart-pair loop and detail-table loop into single for-sec-in-sections pass to avoid two separate loops over sections
  - IIFE wrapping each new Chart() call prevents labels/values JS variable collision across Jinja2 loop iterations
  - Department accumulator uses same defaultdict pattern as category accumulator in same for-s-in-active loop (single pass)
metrics:
  duration: "~25 minutes"
  completed: "2026-05-11"
  tasks_completed: 2
  files_changed: 7
---

# Phase 3 Plan 1: Reports Chart Fix and Department Analysis Summary

**One-liner:** Per-currency donut/bar chart pair rendered via IIFE loop with embedded per-section JSON, plus department cost analysis card with 費用最高 badge.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Embed per-section chart JSON and department data in reports route | cbc027c | subscriptions.py (feat), test_reports_route.py + 3 support files (test/RED: f0d53c3) |
| 2 | Fix chart rendering in reports.html — per-currency loop and dept card | 8c94cef | reports.html |

## What Was Built

**REPORT-01 (multi-currency chart fix):**
- Extracted `_build_report_sections(active: list) -> list[dict]` from the `reports` handler — makes the data-assembly logic independently testable without FastAPI machinery.
- Each section dict now contains `cat_labels_json`, `cat_values_json`, `cat_colors_json` (per-currency), and `departments` (sorted descending by cost).
- Removed `first_cats` and three top-level `cat_*_json` vars from the `TemplateResponse` call.
- `reports.html` replaces the standalone `chart-grid-2` block (hardcoded to `sections[0]`) with a `{% for sec in sections %}` loop. Each iteration renders a chart pair (donut + bar) followed by the detail table — no more two separate loops.
- Canvas IDs follow `donutChart-{{ sec.currency }}` pattern (D-02 compliant).
- `{% block scripts %}` replaced with IIFE-wrapped `new Chart()` calls per currency, using `sec.cat_labels_json`, `sec.cat_values_json`, and `donutChart-{{ sec.currency }}`.

**REPORT-03 (department analysis card):**
- `cur_dept_map` accumulator added in the same `for s in active` loop as `cur_cat_map` (single pass, no double iteration).
- Departments sorted descending by cost, with `monthly` and `pct` enrichments.
- `reports.html` renders a `部門費用分析` card after the per-currency loop with `{% if sec.departments %}` guard and `費用最高` badge on the first row via `{% if loop.first %}`.

**TDD compliance:**
- RED: 4 failing tests committed (f0d53c3) — `_build_report_sections` didn't exist yet.
- GREEN: Implementation added (cbc027c) — all 4 tests pass.
- No REFACTOR needed (code was clean on first pass).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Missing config_option modules in worktree**
- **Found during:** Task 1 RED phase (import chain failure)
- **Issue:** `dependencies.py` imports `SqlConfigOptionRepository` which didn't exist in the worktree (those files are untracked in the main repo). This blocked test collection for `test_reports_route.py`.
- **Fix:** Copied three files from the main repo into the worktree: `src/domain/entities/config_option.py`, `src/domain/repositories/config_option_repository.py`, `src/infrastructure/database/sql_config_option_repository.py`.
- **Files modified:** 3 new files added to worktree
- **Commit:** f0d53c3 (combined with RED test commit)

## Deferred Issues (Out of Scope)

6 pre-existing test failures in the worktree are from Phase 2B in-progress work (worktree has older versions of `create_subscription.py` and `register_user.py`):
- `test_email_failure_returns_empty_notified` — pre-existing in main repo too
- 3 `test_create_subscription` failures — `icon_emoji` param in worktree's use case doesn't match entity
- 2 `test_register_user` failures — worktree's `RegisterUserUseCase` has a `password` param the main repo removed

These were all failing before this plan's changes and are NOT caused by this plan. Logged to deferred-items.

## Success Criteria Check

- [x] REPORT-01: canvas `id="donutChart"` removed; `donutChart-{currency}` used (2 occurrences: canvas + JS)
- [x] REPORT-01: JS scripts block loops over sections with IIFE wrapping each `Chart()` call
- [x] REPORT-03: `_build_report_sections` populates `departments` key on each section dict
- [x] REPORT-03: reports.html renders 部門費用分析 card with 費用最高 badge on top department
- [x] 4 new unit tests in `test_reports_route.py` pass
- [x] 45 other existing tests still pass (6 pre-existing worktree failures excluded)

## Threat Flags

No new threat surfaces introduced. The `_build_report_sections` helper uses `json.dumps(ensure_ascii=False)` for zh-TW labels — JSON encoding automatically escapes `<` preventing XSS via `|safe` filter (T-03-02 mitigated as planned).

## Known Stubs

None — all sections data flows from live subscription data via `_build_report_sections`.

## Self-Check: PASSED

- `src/interfaces/web/routes/subscriptions.py` — exists, contains `_build_report_sections`
- `src/interfaces/web/templates/reports.html` — exists, contains `donutChart-{{ sec.currency }}`
- `tests/unit/test_reports_route.py` — exists, 4 tests pass
- Commits f0d53c3, cbc027c, 8c94cef — all present in git log
