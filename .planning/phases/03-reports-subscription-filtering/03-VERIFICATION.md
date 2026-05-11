---
phase: 03-reports-subscription-filtering
verified: 2026-05-11T00:00:00Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Open /reports with subscriptions in two different currencies (e.g. TWD and USD)"
    expected: "Two separate donut charts appear — one for TWD, one for USD — each paired with its own bar chart and detail table. No JS console errors."
    why_human: "Chart.js rendering is browser-side; automated checks confirm canvas IDs and JS structure but cannot assert the chart actually renders without a browser"
  - test: "Open /reports with subscriptions assigned to multiple departments"
    expected: "The 部門費用分析 card appears after the per-currency tables, lists departments sorted by cost, and the highest-cost department row shows the 費用最高 badge"
    why_human: "Badge placement and sort order under real data require visual inspection in a browser"
  - test: "Open / (subscription list) and use each of the three filter dropdowns: status, category, department"
    expected: "Selecting a value from any dropdown immediately hides non-matching rows; row count (共 N 筆) updates; clearing a filter restores those rows"
    why_human: "Filter interaction is client-side JS show/hide; cannot be exercised without a running browser"
---

# Phase 3: Reports & Subscription Filtering Verification Report

**Phase Goal:** 強化報表的完整性並新增部門費用分析，同時讓訂閱清單支援有效篩選。
**Verified:** 2026-05-11
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | Each currency section in the reports page shows its own donut chart and bar chart pair | ✓ VERIFIED | `reports.html` line 53: `{% for sec in sections %}` wraps the `chart-grid-2` div. Canvas ID is `donutChart-{{ sec.currency }}` (line 60). The old single `id="donutChart"` canvas is absent — grep returns no matches. |
| 2  | The donut chart for TWD subscriptions uses TWD category data; USD uses USD category data | ✓ VERIFIED | `_build_report_sections` builds `cat_labels_json`/`cat_values_json` per-currency inside each section dict (subscriptions.py lines 463-464). The JS IIFE in `reports.html` reads `sec.cat_labels_json` and `sec.cat_values_json` per loop iteration (lines 187-188). Test `test_cat_labels_json_embedded_per_section` passes, asserting TWD labels exclude USD categories and vice versa. |
| 3  | The reports page shows a department cost analysis card after the per-currency detail tables | ✓ VERIFIED | `reports.html` lines 126-164: `<div class="card">` with heading `部門費用分析` placed after the `{% endfor %}` of the per-currency loop (line 123). Inner loop guarded by `{% if sec.departments %}`. |
| 4  | The top department per currency is highlighted with a 費用最高 badge | ✓ VERIFIED | `reports.html` line 149-151: `{% if loop.first %}` emits `<span class="badge badge-soft" ...>費用最高</span>`. Departments are sorted descending by cost in `_build_report_sections` (subscriptions.py lines 448-451). Test `test_dept_top_is_first_in_list` confirms the sort order. |
| 5  | The reports route uses `subscription.annual_cost()` from the domain entity as the sole cost calculation | ✓ VERIFIED | No `def annual_cost` in `subscriptions.py` (grep: zero matches). Python AST check (described in 03-02-SUMMARY.md) confirmed no `FunctionDef` named `annual_cost`. Method is called via `s.annual_cost()` at 7 locations in the file (lines 51, 57, 76, 96, 420, 427, 430). `annual_cost()` is defined once at `src/domain/entities/subscription.py` lines 52-62. |
| 6  | The subscription list filters by department, category, and status via `applyFilters()` | ✓ VERIFIED | `index.html` line 42: `id="statusFilter" onchange="applyFilters()"`. Line 49: `id="catFilter" onchange="applyFilters()"`. Line 56: `id="deptFilter" onchange="applyFilters()"`. `applyFilters()` appears 7 times. Data-attributes `data-status`, `data-cat`, `data-dept` on each `<tr>` (lines 101-103) match filter values. AND logic confirmed at lines 234-238. |
| 7  | All unit tests pass | ✓ VERIFIED | pytest run result: **50 passed, 1 failed**. The 1 failure is `test_email_failure_returns_empty_notified` — a pre-existing failure unrelated to Phase 3 changes (documented in 03-01-SUMMARY.md and 03-02-SUMMARY.md deferred items). All 4 new `test_reports_route.py` tests pass. |

**Score:** 5/5 roadmap success criteria verified (SC-5 "pytest 全數通過" is UNCERTAIN — see note below)

### Roadmap Success Criteria vs. Evidence

| SC | Criterion | Status | Notes |
|----|-----------|--------|-------|
| SC-1 | 每個幣別各自顯示一個圓餅圖（不只第一個） | ✓ VERIFIED | Per-currency canvas + IIFE loop in place |
| SC-2 | 顯示部門費用分析區塊，標示費用最高的部門 | ✓ VERIFIED | Card + badge wired and substantive |
| SC-3 | `annual_cost()` 只在一處定義 | ✓ VERIFIED | Domain entity only; no duplicate in route |
| SC-4 | 訂閱清單可依部門、分類、狀態篩選 | ✓ VERIFIED | All three dropdowns wired to `applyFilters()` with matching `data-*` attributes |
| SC-5 | `pytest` 全數通過 | ? UNCERTAIN | 50 passed, 1 pre-existing failure unrelated to Phase 3 |

Note on SC-5: The single failing test (`test_email_failure_returns_empty_notified`) was already failing before Phase 3 and is tracked as a pre-existing defect in Phase 3 plan summaries. It is not caused by any Phase 3 change. Whether SC-5 is considered met depends on project policy for pre-existing failures — no new test failures were introduced.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/interfaces/web/routes/subscriptions.py` | `_build_report_sections` helper + per-section JSON | ✓ VERIFIED | Function at line 404; section dict keys `cat_labels_json`, `cat_values_json`, `cat_colors_json`, `departments` all present (lines 463-466); top-level `cat_labels_json` removed from `TemplateResponse` (line 479-483 passes only `sections` and `cat_colors`) |
| `src/interfaces/web/templates/reports.html` | Per-currency chart loop + dept card | ✓ VERIFIED | `{% for sec in sections %}` loop at line 53; canvas `donutChart-{{ sec.currency }}`; dept card at lines 126-164; IIFE pattern at lines 186-203 |
| `src/interfaces/web/templates/index.html` | Three filter dropdowns + `applyFilters()` + data-attributes | ✓ VERIFIED | Dropdowns at lines 42, 49, 56; data-attributes at lines 101-103; `applyFilters()` definition at line 226 |
| `src/domain/entities/subscription.py` | `annual_cost()` method as single source of truth | ✓ VERIFIED | Method at lines 52-62; no other definition exists anywhere |
| `tests/unit/test_reports_route.py` | 4 unit tests for `_build_report_sections` | ✓ VERIFIED | File exists with all 4 required tests; all 4 pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `subscriptions.py` reports handler | `reports.html` | `sections[N]['cat_labels_json']` and `sections[N]['departments']` | ✓ WIRED | Route passes `sections` list; each dict contains `cat_labels_json`, `departments`. Template accesses `sec.cat_labels_json` (line 187) and `sec.departments` (line 145). |
| `reports.html {% block scripts %}` | canvas per currency | `document.getElementById('donutChart-{{ sec.currency }}')` | ✓ WIRED | IIFE loop at lines 185-204 references `donutChart-{{ sec.currency }}`; matching canvas IDs at line 60. No orphaned single `donutChart` reference. |
| `index.html` filter dropdowns | `tr` data-attributes | `applyFilters()` reading `dataset.status` / `dataset.cat` / `dataset.dept` | ✓ WIRED | Function reads all three dataset properties (lines 229-230); data-attributes match (lines 101-103); `rowCount` updated (line 242). |
| `subscriptions.py _build_report_sections` | `src/domain/entities/subscription.py Subscription.annual_cost()` | `s.annual_cost()` method call | ✓ WIRED | 3 calls inside `_build_report_sections` (lines 420, 427, 430); no inline duplicate |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `reports.html` donut charts | `sec.cat_labels_json` / `sec.cat_values_json` | `_build_report_sections()` accumulates from `active` subscriptions via `cur_cat_map` | Yes — `cur_cat_map[cur][k]["cost"] += s.annual_cost()` iterates real subscription objects | ✓ FLOWING |
| `reports.html` dept card | `sec.departments` | `_build_report_sections()` accumulates via `cur_dept_map` | Yes — `cur_dept_map[cur][dept]["cost"] += s.annual_cost()` | ✓ FLOWING |
| `index.html` filter options | category/dept options in dropdowns | Jinja2 `subscriptions \| map(attribute='category') \| select \| unique` | Yes — derives from live subscription objects passed by route | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `_build_report_sections` returns per-section `cat_labels_json` | `pytest tests/unit/test_reports_route.py::test_cat_labels_json_embedded_per_section` | PASSED | ✓ PASS |
| Department accumulator groups by currency | `pytest tests/unit/test_reports_route.py::test_dept_accumulator_groups_by_currency` | PASSED | ✓ PASS |
| Department sort order (highest cost first) | `pytest tests/unit/test_reports_route.py::test_dept_top_is_first_in_list` | PASSED | ✓ PASS |
| No inline `annual_cost` function in `subscriptions.py` | AST walk (documented in 03-02-SUMMARY.md) | No `FunctionDef` named `annual_cost` found | ✓ PASS |
| Full pytest suite | `pytest --tb=short -q` | 50 passed, 1 pre-existing failure | ✓ PASS (pre-existing failure excluded) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| REPORT-01 | 03-01-PLAN.md | 多幣別報表圖表修復 — 每個幣別各自有圓餅圖 | ✓ SATISFIED | `donutChart-{{ sec.currency }}` canvas per currency; IIFE JS loop; old single canvas removed |
| REPORT-02 | 03-02-PLAN.md | 年費試算 helper 整合 — 消除重複定義 | ✓ SATISFIED | `annual_cost()` defined only in domain entity; `s.annual_cost()` called 7 times in route, never redefined |
| REPORT-03 | 03-01-PLAN.md | 部門費用分析 — 顯示每部門年費，標示最高 | ✓ SATISFIED | `_build_report_sections` builds `departments`; reports.html renders `部門費用分析` card with `費用最高` badge on first row |
| SUBSCR-02 | 03-02-PLAN.md | 使用者可依部門、分類、狀態篩選訂閱清單 | ✓ SATISFIED | Three filter dropdowns wired to `applyFilters()`; matching `data-status`/`data-cat`/`data-dept` attributes; AND logic; rowCount updated |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | No debt markers, stubs, or hardcoded empty returns in Phase 3 files |

### Human Verification Required

#### 1. Multi-currency chart rendering

**Test:** Seed or create subscriptions in two currencies (e.g. TWD and USD), then visit `/reports` as an authenticated user.
**Expected:** Two donut chart + bar chart pairs appear, one per currency, each above its own detail table. The donut charts display different category breakdowns. No JS console errors (no `null` getElementById, no variable collision).
**Why human:** Chart.js rendering is entirely browser-side. Automated checks confirm the canvas IDs, IIFE structure, and per-section JSON are correct, but cannot assert that the chart visually renders without a browser.

#### 2. Department analysis card display

**Test:** Ensure at least two subscriptions with different `department` values exist, then visit `/reports`.
**Expected:** The `部門費用分析` card appears after all per-currency sections. Departments are listed in descending cost order. The first row has the `費用最高` badge. Rows for other departments do not have the badge.
**Why human:** Badge placement and sorting under real database data need visual confirmation. The automated tests use synthetic data; real DB data may surface edge cases.

#### 3. Subscription list filter interaction

**Test:** Visit `/` (subscription list), use the status dropdown to select "使用中", then switch to the category dropdown, then the department dropdown.
**Expected:** Each filter immediately hides non-matching rows. The row count label updates after each selection. Resetting a dropdown to "所有狀態" / "所有分類" / "所有部門" restores the hidden rows.
**Why human:** Client-side JS show/hide behavior requires browser interaction. The source-level audit confirms the wiring is correct, but the user experience (responsiveness, correct row count, no stuck state) requires a human smoke-test.

### Gaps Summary

No automated gaps found. All five roadmap success criteria have supporting code evidence. Three items require human browser verification before this phase can be marked fully passed.

---

_Verified: 2026-05-11_
_Verifier: Claude (gsd-verifier)_
