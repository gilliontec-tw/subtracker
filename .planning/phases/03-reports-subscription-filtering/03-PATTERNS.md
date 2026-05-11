# Phase 3: Reports & Subscription Filtering - Pattern Map

**Mapped:** 2026-05-11
**Files analyzed:** 4 (2 modify, 1 read-only verify, 1 reference-only)
**Analogs found:** 4 / 4

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/interfaces/web/routes/subscriptions.py` | route/controller | request-response | same file — `reports` handler (lines 404-451) | exact (extend existing handler) |
| `src/interfaces/web/templates/reports.html` | template | request-response | same file — existing per-currency `{% for sec in sections %}` loop (lines 78-122) | exact (move chart block inside same loop) |
| `src/interfaces/web/templates/index.html` | template | request-response | same file — `applyFilters()` JS and filter dropdowns (lines 226-244) | exact (read-only verification only) |
| `src/domain/entities/subscription.py` | entity/model | CRUD | same file — `annual_cost()` method | exact (reference-only, method already exists) |

---

## Pattern Assignments

### `src/interfaces/web/routes/subscriptions.py` — `/reports` handler (REPORT-01, REPORT-02, REPORT-03)

**Analog:** same file — existing `reports` handler and `dashboard` handler

#### REPORT-02 verification: `annual_cost()` usage (lines 418-420)

The route already calls `subscription.annual_cost()` in three places. No inline duplicate exists. The handler is clean:

```python
# lines 418-420 — already correct
cur_cat_map[cur][k]["cost"] += s.annual_cost()
cur_cat_map[cur][k]["count"] += 1
cur_totals[cur] += s.annual_cost()
```

**Action:** Verify-only. No removal needed — `annual_cost()` from the domain entity is already the only cost calculation mechanism used.

#### REPORT-01 fix: move chart data into each section dict (lines 422-451)

Current broken pattern — chart data built for `sections[0]` only and passed as top-level template vars:

```python
# lines 442-451 — current broken pattern (only covers first currency)
first_cats = sections[0]["categories"] if sections else []
return templates.TemplateResponse("reports.html", {
    "request": request,
    "current_user": current_user,
    "sections": sections,
    "cat_colors": CAT_COLORS,
    "cat_colors_json": json.dumps(CAT_COLORS, ensure_ascii=False),
    "cat_labels_json": json.dumps([c["name"] for c in first_cats], ensure_ascii=False),
    "cat_values_json": json.dumps([round(c["cost"], 2) for c in first_cats]),
})
```

**Fixed pattern:** embed `cat_labels_json`, `cat_values_json`, `cat_colors_json` into each section dict inside the `sections` build loop (lines 422-440), then remove the three top-level `cat_*_json` vars from the `TemplateResponse` call.

Section dict assembly pattern (lines 422-440) — extend to embed chart data per section:

```python
sections = []
for cur in sorted(cur_totals, key=lambda c: -cur_totals[c]):
    total = cur_totals[cur]
    cats = sorted(
        [{"name": k, "cost": v["cost"], "count": v["count"]}
         for k, v in cur_cat_map[cur].items()],
        key=lambda c: -c["cost"],
    )
    for c in cats:
        c["monthly"] = c["cost"] / 12
        c["avg"] = c["cost"] / c["count"] if c["count"] else 0
        c["pct"] = round(c["cost"] / total * 100, 1) if total else 0
    sections.append({
        "currency": cur,
        "categories": cats,
        "total_annual": total,
        "total_monthly": total / 12,
        "count": sum(c["count"] for c in cats),
        # ADD these three — embed chart data per currency:
        "cat_labels_json": json.dumps([c["name"] for c in cats], ensure_ascii=False),
        "cat_values_json": json.dumps([round(c["cost"], 2) for c in cats]),
        "cat_colors_json": json.dumps(CAT_COLORS, ensure_ascii=False),
    })
```

Updated `TemplateResponse` call — remove the three now-redundant top-level vars:

```python
return templates.TemplateResponse("reports.html", {
    "request": request,
    "current_user": current_user,
    "sections": sections,
    "cat_colors": CAT_COLORS,
    # REMOVE: cat_colors_json, cat_labels_json, cat_values_json (now in each sec)
})
```

#### REPORT-03: department cost analysis data (new addition to `reports` handler)

**Pattern:** Follow the same per-currency grouping pattern already used for `cur_cat_map` (lines 411-420), but group by `department` instead of `category`.

Add a `cur_dept_map` parallel to `cur_cat_map` in the same accumulation loop:

```python
# Add alongside existing cur_cat_map loop (after line 420)
cur_dept_map: dict[str, dict] = {}
for s in active:
    cur = s.currency or "TWD"
    dept = s.department or "未分類"
    if cur not in cur_dept_map:
        cur_dept_map[cur] = defaultdict(lambda: {"cost": 0.0, "count": 0})
    cur_dept_map[cur][dept]["cost"] += s.annual_cost()
    cur_dept_map[cur][dept]["count"] += 1
```

Then in the `sections` build loop, add a `departments` list to each section dict (same sort pattern as `cats`):

```python
# Add inside the sections loop after cats is assembled
depts_raw = cur_dept_map.get(cur, {})
depts = sorted(
    [{"name": k, "cost": v["cost"], "count": v["count"]}
     for k, v in depts_raw.items()],
    key=lambda d: -d["cost"],
)
for d in depts:
    d["monthly"] = d["cost"] / 12
    d["pct"] = round(d["cost"] / total * 100, 1) if total else 0

# Then add to sections.append({...}):
"departments": depts,
```

**Data flow note:** `cur_dept_map` must be populated in the same loop as `cur_cat_map` — either merge into the existing `for s in active` loop or add a second loop over the same list. Merging is preferred to avoid iterating twice.

---

### `src/interfaces/web/templates/reports.html` — chart and dept section (REPORT-01, REPORT-03)

**Analog:** same file — existing `{% for sec in sections %}` loop (lines 78-122) and existing chart block (lines 52-75)

#### REPORT-01: move chart block inside the per-currency loop

Current broken chart block (lines 52-75) — renders once, hardcoded to `sections[0]`, single canvas id:

```html
<!-- Charts (based on largest-currency section) -->
<div class="chart-grid-2">
  <div class="chart-card">
    <h3>分類佔比 <span ...>{{ sections[0].currency }}</span></h3>
    <div class="chart-sub">{{ sections[0].currency }} 訂閱年度費用分布</div>
    <div style="position:relative;height:200px;">
      <canvas id="donutChart"></canvas>       {# BUG: hardcoded single id #}
    </div>
  </div>
  <div class="chart-card">
    <h3>分類金額排行 <span ...>{{ sections[0].currency }}</span></h3>
    ...
    {% for c in sections[0].categories %}     {# BUG: hardcoded to first section #}
    ...
    {% endfor %}
  </div>
</div>
```

**Fixed pattern:** move the entire `chart-grid-2` block inside `{% for sec in sections %}`, replacing `sections[0]` with `sec` and using `donutChart-{{ sec.currency }}` as the canvas id:

```html
{% for sec in sections %}
<div class="chart-grid-2">
  <div class="chart-card">
    <h3>分類佔比 <span style="font-size:11px;font-weight:400;color:var(--muted);">{{ sec.currency }}</span></h3>
    <div class="chart-sub">{{ sec.currency }} 訂閱年度費用分布</div>
    <div style="position:relative;height:200px;">
      <canvas id="donutChart-{{ sec.currency }}"></canvas>
    </div>
  </div>
  <div class="chart-card">
    <h3>分類金額排行 <span style="font-size:11px;font-weight:400;color:var(--muted);">{{ sec.currency }}</span></h3>
    <div class="chart-sub">由高到低，找出可議價的支出大戶</div>
    {% set max_cost = sec.categories[0].cost if sec.categories else 1 %}
    {% for c in sec.categories %}
    <div class="bar-row">
      <div class="bar-label">{{ c.name }}</div>
      <div class="bar-track">
        <div class="bar-fill" style="width:{{ (c.cost / max_cost * 100)|round(1) }}%;background:{{ cat_colors.get(c.name, '#B0AEC4') }};"></div>
      </div>
      <div class="bar-value">${{ "{:,.0f}".format(c.cost) }}</div>
    </div>
    {% endfor %}
  </div>
</div>

<!-- Per-currency detail table (already inside this loop) -->
<div class="card">
  ...
</div>
{% endfor %}
```

The per-currency detail table (lines 78-122) is already inside `{% for sec in sections %}` — keep it there, just add the `chart-grid-2` block above it inside the same loop iteration.

#### REPORT-01: JS chart init in `{% block scripts %}` — loop per currency

Current broken JS (lines 138-161) — single `new Chart(document.getElementById('donutChart'), ...)` using top-level `catLabels`/`catValues` vars:

```javascript
// Current (broken — only renders for first currency)
const CAT_COLORS = {{ cat_colors_json|safe }};
const catLabels = {{ cat_labels_json|safe }};
const catValues = {{ cat_values_json|safe }};

new Chart(document.getElementById('donutChart'), {
  type: 'doughnut',
  data: {
    labels: catLabels,
    datasets: [{ data: catValues, backgroundColor: catLabels.map(l => CAT_COLORS[l]||'#B0AEC4'), borderWidth: 0, hoverOffset: 4 }]
  },
  options: {
    cutout: '65%',
    plugins: {
      legend: { position: 'right', labels: { font: { size: 11 }, color: '#7A7891', boxWidth: 10, padding: 10 } },
      tooltip: { callbacks: { label: ctx => ` $${ctx.parsed.toLocaleString()}` } }
    }
  }
});
```

**Fixed pattern:** loop in Jinja2 over `sections`, using `sec.cat_labels_json`, `sec.cat_values_json`, `sec.cat_colors_json` (embedded per section by route), and `donutChart-{{ sec.currency }}` as the element id:

```javascript
{% block scripts %}
{% if sections %}
<script>
const CAT_COLORS = {{ sections[0].cat_colors_json|safe }};   {# same dict for all currencies #}

{% for sec in sections %}
(function() {
  const labels = {{ sec.cat_labels_json|safe }};
  const values = {{ sec.cat_values_json|safe }};
  new Chart(document.getElementById('donutChart-{{ sec.currency }}'), {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{ data: values, backgroundColor: labels.map(l => CAT_COLORS[l]||'#B0AEC4'), borderWidth: 0, hoverOffset: 4 }]
    },
    options: {
      cutout: '65%',
      plugins: {
        legend: { position: 'right', labels: { font: { size: 11 }, color: '#7A7891', boxWidth: 10, padding: 10 } },
        tooltip: { callbacks: { label: ctx => ` $${ctx.parsed.toLocaleString()}` } }
      }
    }
  });
})();
{% endfor %}
</script>
{% endif %}
{% endblock %}
```

The IIFE `(function() { ... })()` wrapper prevents variable name collision across loop iterations.

#### REPORT-03: department cost section — new card at bottom

**Placement:** After the `{% endfor %}` closing tag of the per-currency detail tables loop (after line 122), before the `{% else %}` empty state block.

**Pattern:** Copy the existing category detail table card structure (lines 78-122), substituting `departments` for `categories` and using zh-TW label `部門費用分析`. Top department highlighted with a `費用最高` badge:

```html
<!-- Department cost analysis section -->
<div class="card" style="margin-top:24px;">
  <div class="card-header">
    <h3 class="card-title">部門費用分析</h3>
  </div>
  {% for sec in sections %}
  {% if sec.departments %}
  <div style="margin-bottom:16px;">
    <div style="font-size:12px;font-weight:600;color:var(--muted);margin-bottom:8px;">{{ sec.currency }}</div>
    <table>
      <thead>
        <tr>
          <th>部門</th>
          <th class="right">年度費用</th>
          <th class="right">月均</th>
          <th class="right">佔比</th>
          <th class="right">訂閱數</th>
        </tr>
      </thead>
      <tbody>
        {% for d in sec.departments %}
        <tr>
          <td>
            <strong>{{ d.name }}</strong>
            {% if loop.first %}
            <span class="badge badge-soft" style="margin-left:6px;font-size:10px;">費用最高</span>
            {% endif %}
          </td>
          <td class="right tabnum">${{ "{:,.0f}".format(d.cost) }} <span class="muted" style="font-size:11px;">{{ sec.currency }}</span></td>
          <td class="right tabnum muted">${{ "{:,.0f}".format(d.monthly) }}</td>
          <td class="right"><span class="badge badge-soft">{{ d.pct }}%</span></td>
          <td class="right tabnum">{{ d.count }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  {% endif %}
  {% endfor %}
</div>
```

---

### `src/interfaces/web/templates/index.html` — SUBSCR-02 verification (read-only)

**No code changes expected.** Verification confirms three filter controls with `applyFilters()` wired correctly.

#### Filter dropdowns (lines 42-62)

```html
<select class="input input-sm" id="statusFilter" style="width:auto" onchange="applyFilters()">
  <option value="">所有狀態</option>
  <option value="active">使用中</option>
  <option value="renewed">已續約</option>
  <option value="cancelled">已取消</option>
  <option value="suspended">暫停</option>
</select>
<select class="input input-sm" id="catFilter" style="width:auto" onchange="applyFilters()">
  <option value="">所有分類</option>
  {% set cats = subscriptions | map(attribute='category') | select | unique | list %}
  {% for cat in cats | sort %}<option value="{{ cat }}">{{ cat }}</option>{% endfor %}
</select>
<select class="input input-sm" id="deptFilter" style="width:auto" onchange="applyFilters()">
  <option value="">所有部門</option>
  {% set depts = subscriptions | map(attribute='department') | select | unique | list %}
  {% for dept in depts | sort %}<option value="{{ dept }}">{{ dept }}</option>{% endfor %}
</select>
```

#### Row data-attributes that filters read (lines 99-105)

```html
<tr
  data-name="{{ (s.login_account ~ ' ' ~ s.service_name) | lower }}"
  data-status="{{ s.status.value }}"
  data-cat="{{ s.category or '' }}"
  data-dept="{{ s.department or '' }}"
  data-days="{{ days }}"
>
```

#### `applyFilters()` JS function (lines 226-244)

```javascript
function applyFilters() {
  const q    = document.getElementById('searchBox').value.toLowerCase();
  const st   = document.getElementById('statusFilter').value;
  const cat  = document.getElementById('catFilter').value;
  const dept = document.getElementById('deptFilter').value;
  let visible = 0;
  document.querySelectorAll('#subTable tbody tr').forEach(tr => {
    const match =
      (!q    || tr.dataset.name.includes(q)) &&
      (!st   || tr.dataset.status === st) &&
      (!cat  || tr.dataset.cat === cat) &&
      (!dept || tr.dataset.dept === dept) &&
      (!showDue || parseInt(tr.dataset.days) <= 30);
    tr.style.display = match ? '' : 'none';
    if (match) visible++;
  });
  document.getElementById('rowCount').textContent = '共 ' + visible + ' 筆';
  updateBulkBtn();
}
```

**Verification checklist for SUBSCR-02 smoke-test:**
- `data-status` matches `statusFilter` values: `active`, `renewed`, `cancelled`, `suspended` — confirmed
- `data-cat` matches `catFilter` option values (derived from `s.category`) — confirmed
- `data-dept` matches `deptFilter` option values (derived from `s.department`) — confirmed
- All three fire `applyFilters()` on `onchange` — confirmed

---

### `src/domain/entities/subscription.py` — `annual_cost()` reference (REPORT-02)

**Reference-only. No changes to this file.**

#### `annual_cost()` method (lines 52-62)

```python
def annual_cost(self) -> float:
    if self.cost is None:
        return 0.0
    multipliers = {
        "monthly":     12,
        "quarterly":   4,
        "semi_annual": 2,
        "annual":      1,
        "biennial":    0.5,
    }
    return float(self.cost) * multipliers.get(self.billing_cycle or "annual", 1)
```

This is the single source of truth for cost normalization. The reports route already calls it exclusively (confirmed at lines 418, 420). REPORT-02 is a verify-only task.

---

## Shared Patterns

### Per-currency loop pattern
**Source:** `src/interfaces/web/routes/subscriptions.py` lines 423-440 and `src/interfaces/web/templates/reports.html` lines 78-122
**Apply to:** REPORT-01 (chart loop), REPORT-03 (dept section)

The `sections` list is already sorted by descending annual cost (largest currency first). Both the route data assembly and the template iterate `sections` in the same order. New data (chart JSON, departments list) must be embedded in each section dict — not passed as separate top-level template vars.

### Jinja2 `{% for sec in sections %}` + `{% block scripts %}` loop coordination
**Source:** `src/interfaces/web/templates/reports.html` — the existing per-currency table loop (lines 78-122) is in `{% block content %}`, and the chart JS is in `{% block scripts %}`
**Apply to:** REPORT-01 fix — both the canvas `<div>` (content block) and the `new Chart(...)` call (scripts block) must be looped over `sections` using the same `sec.currency` key

### `json.dumps(..., ensure_ascii=False)` for Jinja2 embedding
**Source:** `src/interfaces/web/routes/subscriptions.py` lines 77-78, 448-450
**Apply to:** All JSON data passed to templates via `|safe` filter — use `ensure_ascii=False` for zh-TW labels

```python
# Correct pattern for zh-TW string data in JSON:
json.dumps([c["name"] for c in cats], ensure_ascii=False)
# Numeric-only JSON does not need ensure_ascii=False but it is harmless:
json.dumps([round(c["cost"], 2) for c in cats])
```

### `defaultdict(lambda: {"cost": 0.0, "count": 0})` accumulator
**Source:** `src/interfaces/web/routes/subscriptions.py` lines 417-419
**Apply to:** REPORT-03 department accumulator — identical pattern, swap `category` for `department`

```python
cur_cat_map[cur] = defaultdict(lambda: {"cost": 0.0, "count": 0})
cur_cat_map[cur][k]["cost"] += s.annual_cost()
cur_cat_map[cur][k]["count"] += 1
```

### `loop.first` badge for top-ranked item
**Source:** Jinja2 built-in — consistent with existing badge patterns across the template set (e.g., `reports.html` lines 40-48 highlight `sections[0].categories[0]`)
**Apply to:** REPORT-03 department table — `{% if loop.first %}` marks the top department with `費用最高` badge

---

## No Analog Found

All files have direct analogs within the existing codebase. No files require falling back to external reference patterns.

---

## Key Findings for Planner

1. **REPORT-01 is a two-part fix:** (a) route — embed `cat_labels_json`, `cat_values_json`, `cat_colors_json` into each section dict; (b) template — move `chart-grid-2` block and JS `new Chart(...)` call inside the per-currency `{% for sec in sections %}` loop using `donutChart-{{ sec.currency }}` ids. The bar chart (Jinja2 bar-row loop) naturally follows by moving inside the same loop iteration.

2. **REPORT-02 is verify-only:** The route handler already calls `subscription.annual_cost()` exclusively at lines 418 and 420. There is no inline duplicate `annual_cost` function in the file. REPORT-02 requires a code-read confirmation only.

3. **REPORT-03 data assembly pattern** mirrors the existing `cur_cat_map` pattern exactly — same `defaultdict` accumulator, same sort-by-descending-cost, same per-section dict extension. The only additions are `cur_dept_map` accumulation and a `departments` key in each section dict.

4. **IIFE pattern required for JS loop:** Multiple `new Chart(...)` calls in a Jinja2 `{% for %}` loop must each be wrapped in `(function() { ... })()` to avoid `labels`/`values` variable collisions across iterations.

5. **SUBSCR-02 is already complete:** `applyFilters()` reads `data-status`, `data-cat`, `data-dept` from each `<tr>`, matching the three filter dropdown values exactly. The implementation is correct. Document as passed in the plan SUMMARY; no code changes.

6. **`cat_colors_json` top-level var can be removed** from the `TemplateResponse` call after REPORT-01 is applied — it is replaced by `sec.cat_colors_json` inside each section dict. `cat_colors` (the Python dict, not JSON) must remain for the Jinja2 `cat_colors.get(c.name, '#B0AEC4')` calls in the bar-row loop.

---

## Metadata

**Analog search scope:** `src/interfaces/web/routes/`, `src/interfaces/web/templates/`, `src/domain/entities/`
**Files read:** 5 source files
**Pattern extraction date:** 2026-05-11
