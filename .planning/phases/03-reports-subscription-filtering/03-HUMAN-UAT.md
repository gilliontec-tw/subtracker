---
status: partial
phase: 03-reports-subscription-filtering
source: [03-VERIFICATION.md]
started: 2026-05-11T00:00:00Z
updated: 2026-05-11T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Multi-currency chart rendering
expected: Visit /reports with both TWD and USD subscriptions present; two distinct Chart.js donut + bar chart pairs render on the page (one per currency), each with its own canvas element (`donutChart-TWD`, `donutChart-USD`), with no JavaScript console errors.
result: [pending]

### 2. Department analysis card
expected: The `部門費用分析` card appears below the per-currency detail tables. Departments are listed in descending cost order. The top-cost department row has a `費用最高` badge, and no other rows have this badge.
result: [pending]

### 3. Subscription filter interaction
expected: On the subscription list page (/), each of the three filter dropdowns (department, category, status) correctly hides/shows table rows when changed. The row count display updates after each filter change. Selecting "all" restores all rows.
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
