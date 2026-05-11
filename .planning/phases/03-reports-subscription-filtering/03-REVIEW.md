---
phase: 03-reports-subscription-filtering
reviewed: 2026-05-11T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - src/interfaces/web/routes/subscriptions.py
  - src/interfaces/web/templates/reports.html
  - tests/unit/test_reports_route.py
  - src/domain/entities/config_option.py
  - src/domain/repositories/config_option_repository.py
  - src/infrastructure/database/sql_config_option_repository.py
findings:
  critical: 2
  warning: 4
  info: 2
  total: 8
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-05-11T00:00:00Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

The phase-03 changes add a reports page with per-currency chart data and a department analysis section, plus a new `ConfigOption` domain entity and its SQL repository. The logic in `_build_report_sections` is well-structured and extracted for testability. The `delete` method in the SQL repository and the use of `|safe` in the template are the primary risk areas. Two correctness bugs (delete ordering, chart canvas collision) and two security-adjacent issues (XSS via unsanitised `|safe` output) require attention before shipping.

---

## Critical Issues

### CR-01: XSS via user-controlled category/department names emitted through `|safe` in reports.html

**File:** `src/interfaces/web/templates/reports.html:183,187,188`

**Issue:** Three Jinja2 `|safe` expressions embed JSON that contains category and department names pulled directly from the database. Those strings originate from user-supplied `category` and `department` fields on subscriptions (free-text, no whitelist enforcement in the route or entity). If a subscription is created with a category name containing `</script><script>alert(1)</script>`, that string ends up inside `json.dumps(...)` which does **not** escape the `</` sequence by default, so it is injected verbatim into the `<script>` block, bypassing the Jinja2 auto-escape context entirely.

Concrete path:
1. `category` field stored as `</script><img src=x onerror=alert(1)>`.
2. `json.dumps([category_name], ensure_ascii=False)` → `["</script><img ...>"]`.
3. Template line 187: `const labels = {{ sec.cat_labels_json|safe }};` — the `|safe` suppresses Jinja2 HTML-escaping, and the `</script>` in the JSON string terminates the surrounding `<script>` tag.

The same risk applies to `cat_colors_json` (line 183) through the `CAT_COLORS` dict whose keys are hardcoded Chinese strings, but `cat_labels_json` and `cat_values_json` are built from DB data.

**Fix:** Use `json.dumps(..., ensure_ascii=True)` (dropping `ensure_ascii=False`) so all non-ASCII characters — including any injected script payload — are escaped as `\uXXXX`, and additionally escape forward-slashes:

```python
import re

def _safe_json(data) -> str:
    """JSON-encode and escape </  to prevent script-injection."""
    return re.sub(r'</', r'<\/', json.dumps(data, ensure_ascii=True))
```

Replace every `json.dumps(..., ensure_ascii=False)` call in `_build_report_sections` and at the dashboard level with `_safe_json(...)`. This is the standard mitigation used by Django's `escapejs` and Flask's `tojson` filter, both of which escape `</` → `<\/`.

---

### CR-02: `delete()` deletes children then tries to delete parent — but parent's children are not flushed before the parent `get()`, causing a foreign-key integrity error on some RDBMS configurations

**File:** `src/infrastructure/database/sql_config_option_repository.py:75-83`

**Issue:** The delete implementation first bulk-deletes children (line 77-79), then fetches the parent with `session.get()` (line 80) and calls `session.delete()` (line 82), with a single `commit()` at the end. On SQL Server with foreign-key constraints (no FK is currently defined in `ConfigOptionModel`, but the schema intent implies a self-referential relationship), this is fragile. More concretely: the `.delete()` call on the query (line 79) executes a `DELETE` SQL immediately (SQLAlchemy bulk-delete bypasses the Unit of Work). Then `session.get()` (line 80) may return a stale cached parent object whose `children` list still references the already-deleted child rows. If any in-flight reference or cascade is configured later, this ordering causes silent data inconsistency.

Additionally, if `option_id` does not exist, the children `.delete()` still runs (a no-op is fine), but the subsequent `session.commit()` at line 83 is called unconditionally even when no parent was found, which is a wasted round-trip and masks the "ID not found" case entirely — callers have no way to distinguish a successful delete from a no-op on a non-existent ID.

**Fix:**

```python
def delete(self, option_id: int) -> None:
    # Delete children first (bulk delete executes immediately in SQLAlchemy)
    self._session.query(ConfigOptionModel).filter(
        ConfigOptionModel.parent_id == option_id
    ).delete(synchronize_session="fetch")   # keep session cache coherent
    model = self._session.get(ConfigOptionModel, option_id)
    if model is None:
        return  # nothing to commit; don't swallow missing-ID silently in callers
    self._session.delete(model)
    self._session.commit()
```

The critical addition is `synchronize_session="fetch"` (or `"evaluate"`) so SQLAlchemy invalidates its identity-map entries for the deleted children before the subsequent `get()` call. Without it, the session may serve stale objects from its cache.

---

## Warnings

### WR-01: Canvas `id` collision when currency code contains characters invalid in HTML IDs

**File:** `src/interfaces/web/templates/reports.html:61,189`

**Issue:** The donut chart canvas element is given the ID `donutChart-{{ sec.currency }}` (line 61). Currency values come from the subscription `currency` field, which is a free-text `String(10)` column with no server-side whitelist. If a user stores a currency like `USD EUR` (with a space), the generated ID `donutChart-USD EUR` is invalid HTML (spaces are not allowed in `id` attributes), and `document.getElementById('donutChart-USD EUR')` returns `null`, causing a JavaScript runtime error (Chart.js receives a `null` element). If two subscriptions share the same currency string differing only in case (e.g. `usd` vs `USD`), the section building groups them separately, producing two canvas elements with the same ID — only the first is found by `getElementById`.

**Fix:** Sanitise the currency value when inserting it into the ID:

```html
<canvas id="donutChart-{{ sec.currency | replace(' ', '_') | replace('/', '_') }}"></canvas>
```

And synchronise the selector in the script block:

```javascript
document.getElementById('donutChart-{{ sec.currency | replace(" ", "_") | replace("/", "_") }}')
```

A stronger fix is to use `loop.index` instead:

```html
<canvas id="donutChart-{{ loop.index }}"></canvas>
```

```javascript
document.getElementById('donutChart-{{ loop.index }}')
```

---

### WR-02: `get_tree` builds children into `ConfigOption` objects returned from `_to_entity`, but `_to_entity` always returns objects with an empty `children` list — tree building works by mutating those objects, which is correct, but the objects returned from `get_by_type` are also used directly by callers who expect no children populated

**File:** `src/infrastructure/database/sql_config_option_repository.py:41-52`

**Issue:** `get_tree` calls `get_by_type` which calls `_to_entity` for each row. `_to_entity` constructs a `ConfigOption` with `children=[]` (the dataclass default). `get_tree` then populates `parent.children.append(o)`. This is safe because `ConfigOption` uses `field(default_factory=list)` so each instance has its own list. However, `get_by_type` is also called independently by routes (e.g. `config_repo.get_by_type("category")` in `create_form`). Those calls return flat `ConfigOption` objects without children, which is correct. The risk is that if `get_tree` is ever called first and the session caches results, a subsequent `get_by_type` call in the same session would return the same Python objects (via SQLAlchemy's identity map), and those objects would have their `children` list already populated from the earlier `get_tree` call — leading to unexpected data. In practice this is unlikely within a single request but is a hidden coupling.

**Fix:** In `_to_entity`, explicitly pass `children=[]` (already implicitly done), but add a note. More importantly, `get_tree` should work on a fresh copy:

```python
def get_tree(self, type: str) -> list[ConfigOption]:
    import copy
    all_opts = [copy.copy(o) for o in self.get_by_type(type)]
    ...
```

Or isolate tree-building into a separate query that doesn't reuse the `get_by_type` path.

---

### WR-03: `bulk_renew` passes `notifications_enabled` as a keyword argument to `uc.execute()` — but `UpdateSubscriptionUseCase.execute()` may not accept that parameter

**File:** `src/interfaces/web/routes/subscriptions.py:520`

**Issue:** The `bulk_renew` handler passes `notifications_enabled=sub.notifications_enabled` (line 520) to the update use case. All other call-sites of the update use case (`edit_submit`, etc.) do not pass this parameter. If `UpdateSubscriptionUseCase.execute()` does not declare `notifications_enabled` as a parameter, this will raise a `TypeError` at runtime when bulk-renew is invoked. Since the edit form has no `notifications_enabled` field, this field would also be reset to whatever default the use case applies, silently overriding user data.

**Fix:** Audit `UpdateSubscriptionUseCase.execute()` signature and align the call-sites. If the parameter is accepted, add it to all other call-sites so it is preserved on edit. If it is not accepted, remove it from the bulk-renew call.

---

### WR-04: `_build_report_sections` computes `count` as the sum of category counts, not the count of distinct subscriptions — subscriptions without a `department` are counted in "未分類" for the dept table but are excluded from `sec.count` only if they have no category either

**File:** `src/interfaces/web/routes/subscriptions.py:462`

**Issue:** `sec["count"]` is computed as `sum(c["count"] for c in cats)` (line 462). Every subscription lands in exactly one category bucket (or "未分類"), so this count equals the total number of active subscriptions for that currency. Meanwhile, `sec.departments` separately counts subscriptions by department. These two counts can diverge if a subscription has a category but no department (excluded from dept analysis), or vice versa. The template displays `sec.count` as "N 個訂閱" next to the dept table (line 131-132), but the dept rows may sum to a different total. This confuses the reader.

**Fix:** Track the total subscription count separately in `_build_report_sections`:

```python
sections.append({
    ...
    "count": sum(c["count"] for c in cats),
    "dept_count": sum(d["count"] for d in depts),
    ...
})
```

And display `sec.dept_count` in the department section header instead of `sec.count`.

---

## Info

### IN-01: `ConfigOptionModel` has no database-level foreign-key constraint on `parent_id`

**File:** `src/infrastructure/database/models.py:64`

**Issue:** `parent_id` is defined as a plain `Column(Integer, nullable=True)` with no `ForeignKey("config_options.id")`. This means orphaned child rows can be created if a parent is deleted outside of the `SqlConfigOptionRepository.delete()` path (e.g. direct SQL, migrations). The `get_tree` method silently drops orphans (`by_id.get(o.parent_id)` returns `None` and the child is ignored). There is no data integrity enforcement at the DB layer.

**Fix:**

```python
parent_id = Column(Integer, ForeignKey("config_options.id", ondelete="CASCADE"), nullable=True)
```

This also makes the application-level child-deletion in `SqlConfigOptionRepository.delete()` redundant (the CASCADE handles it), simplifying the delete method.

---

### IN-02: Test `test_top_level_cat_labels_json_removed_from_template_response` does not test what its name claims

**File:** `tests/unit/test_reports_route.py:94-118`

**Issue:** The test name says it verifies "The TemplateResponse context must not have cat_labels_json at top level." But the test does not inspect the TemplateResponse at all — it calls `_build_report_sections` directly and checks that per-section keys exist. The actual TemplateResponse context (returned by the `reports` route handler) is never instantiated or inspected. If a developer were to accidentally re-add `cat_labels_json` as a top-level template variable in the route handler, this test would not catch it.

**Fix:** Either rename the test to match what it actually tests (`test_section_dicts_contain_chart_json_keys`), or add an integration-style check that calls the route handler and inspects the template context keys.

---

_Reviewed: 2026-05-11T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
