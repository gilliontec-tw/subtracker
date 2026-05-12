# Design Spec: Visual Redesign + 費用報表 + 通知設定

**Date:** 2026-05-04
**Scope:** Three deliverables in one spec — (1) global visual overhaul via `base.html`, (2) new 費用報表 page, (3) new 通知設定 page.

---

## 1. Global Visual Redesign (`base.html`)

### Problem
Current `base.html` uses a top navbar with 7+ inline-styled buttons in slightly different shades of blue. There is no design token system — colors, spacing, and radii are scattered across inline `style=""` attributes and an embedded `<style>` block with hard-coded hex values. The result is visually inconsistent and hard to maintain.

### Solution: Sidebar Layout + CSS Variables

Replace the top navbar with a **fixed left sidebar (220 px wide)**. All navigation items move into the sidebar. The main content area gains the freed horizontal width.

**CSS custom properties** (declared once in `<style>` inside `base.html`):

```css
:root {
  --primary:        #4F46E5;
  --primary-hover:  #4338CA;
  --bg:             #F8FAFC;
  --surface:        #FFFFFF;
  --border:         #E2E8F0;
  --text:           #1E293B;
  --muted:          #64748B;
  --success:        #10B981;
  --warning:        #F59E0B;
  --danger:         #EF4444;
  --sidebar-w:      220px;
  --radius:         10px;
}
```

**Sidebar structure:**

```
┌──────────────────────────────────────────────────────────┐
│  Sidebar (220px, fixed)  │  Main content (fluid)         │
│  ─────────────────────   │                               │
│  [Logo / Brand]          │  {% block content %}          │
│                          │                               │
│  🏠  Dashboard           │                               │
│  📦  訂閱清單            │                               │
│  📊  費用報表            │                               │
│  🔔  通知設定            │                               │
│  ── admin only ──        │                               │
│  👥  使用者管理          │                               │
│  🕵️  操作紀錄            │                               │
│                          │                               │
│  ── bottom ──            │                               │
│  [顯示名稱]              │                               │
│  ＋ 新增訂閱 (btn)       │                               │
│  🔑 修改密碼             │                               │
│  [登出]                  │                               │
└──────────────────────────┴───────────────────────────────┘
```

Active nav item: background `var(--bg)`, left border `3px solid var(--primary)`, text `var(--primary)`.

**Card / table refresh:**
- Cards: `border-radius: var(--radius)`, `box-shadow: 0 1px 3px rgba(0,0,0,0.08)`, `border: none`
- Table `<thead>`: `background: var(--bg)`, text `var(--text)` — remove the dark-blue header
- Body background: `var(--bg)`
- All Bootstrap overrides moved into the CSS variables block; zero inline `style=""` left in `base.html`

**Typography:** `font-family: 'Inter', system-ui, sans-serif` — load Inter from Google Fonts CDN (one line).

---

## 2. 費用報表 (`/reports`)

### Purpose
Show how annual SaaS spend breaks down by category to help teams decide which subscriptions to cut or renegotiate.

### Route
```
GET /reports    → requires get_current_user
```
New route added to `src/interfaces/web/routes/subscriptions.py`.

### Server-Side Data

Reuses the `annual_cost(s)` helper already in the `dashboard()` route (extracted to module-level to avoid duplication).

```python
active_subs = [s for s in all_subs if s.status.value in ("active", "renewed")]

cat_totals = defaultdict(lambda: {"cost": 0.0, "count": 0})
for s in active_subs:
    cat = s.category or "未分類"
    cat_totals[cat]["cost"] += annual_cost(s)
    cat_totals[cat]["count"] += 1

total_annual = sum(d["cost"] for d in cat_totals.values())

categories = sorted(
    [
        {
            "name": name,
            "annual_cost": round(d["cost"]),
            "monthly_cost": round(d["cost"] / 12),
            "count": d["count"],
            "pct": round(d["cost"] / total_annual * 100, 1) if total_annual else 0,
            "avg_per_sub": round(d["cost"] / d["count"]) if d["count"] else 0,
        }
        for name, d in cat_totals.items()
    ],
    key=lambda x: x["annual_cost"],
    reverse=True,
)
```

Template context variables:
- `total_annual_cost` — `round(total_annual)`
- `total_monthly_cost` — `round(total_annual / 12)`
- `top_category` — `categories[0]["name"]` if categories else `"—"`
- `chart_labels` — `json.dumps([c["name"] for c in categories])`
- `chart_values` — `json.dumps([c["annual_cost"] for c in categories])`
- `categories` — list of dicts above

### Template Layout (`reports.html`)

```
┌─────────────────────────────────────────────────────┐
│  頁面標題: 費用報表                                   │
├──────────┬──────────┬──────────────────────────────┤
│ 年度總費用│ 月均費用 │  最貴分類                     │  ← 3 KPI cards
├──────────┴──────────┴──────────────────────────────┤
│  甜甜圈圖 (col-5)  │  橫向長條圖 (col-7)            │  ← Charts
│  分類佔比           │  各分類金額由高到低             │
├────────────────────────────────────────────────────┤
│  分類明細表                                          │
│  分類 | 年度費用 | 月均 | 佔比 | 訂閱數 | 每訂閱均值 │
└────────────────────────────────────────────────────┘
```

Chart.js configuration:
- Donut: same COLORS array as dashboard, legend at bottom
- Horizontal bar: `type: 'bar'` with `indexAxis: 'y'`, single color `#818CF8` (indigo-400), bars sorted descending (already sorted server-side)

Detail table: no pagination (max ~10 category rows), no sort needed.

Empty state: if `not categories`, show a centered "尚無費用資料，請先為訂閱填入費用欄位" message.

---

## 3. 通知設定 (`/notifications/settings`)

### Purpose
Let admins configure, per subscription, whether a notification is sent, how many days in advance, and who receives it — without having to open each subscription's edit form.

### Schema Change
Add one column to `saas_subscriptions`:

```sql
ALTER TABLE saas_subscriptions
  ADD notification_enabled BIT NOT NULL DEFAULT 1;
```

Add to `Subscription` entity:
```python
notification_enabled: bool = True
```

Propagate through: `models.py` → repository `_to_entity` / `add` / `update` → `CreateSubscriptionUseCase` / `UpdateSubscriptionUseCase` (default `True`) → `CheckAndNotifyUseCase` (filter step).

`CheckAndNotifyUseCase` change: add `and s.notification_enabled` to the due_subs filter:
```python
due_subs = [s for s in subscriptions if s.notification_enabled and s.should_notify_today(today)]
```

### Routes

```
GET  /notifications/settings   → render settings page
POST /notifications/settings   → bulk update, redirect to GET ?saved=1
```

Both require `get_current_user`. POST requires `require_admin` (only admins control notification routing).

### Template Layout (`notification_settings.html`)

```
┌─────────────────────────────────────────────────────┐
│  通知設定                                             │
│  系統每天 08:00 自動發送到期提醒郵件                   │  ← description
├─────────────────────────────────────────────────────┤
│  訂閱通知設定表格                                     │
│  服務名稱 | 到期日 | 啟用 | 提前天數 | 收件人 Email   │
│  ──────────────────────────────────────────────────  │
│  [Slack]  | 2026-.. | ☑  | [7天▼]  | [a@co.com   ] │
│  [Notion] | 2026-.. | ☑  | [30天▼] | [b@co.com   ] │
│  ...                                                 │
├─────────────────────────────────────────────────────┤
│                        [儲存全部設定]                 │
└─────────────────────────────────────────────────────┘
```

Form implementation:
- Single `<form method="POST">` wraps the entire table
- Each row: `<input type="hidden" name="sub_id" value="{{ sub.id }}">` (repeated per row via array-style naming: `sub_id_{{ loop.index }}`)
- Actually simpler: `name="enabled_{{ sub.id }}"`, `name="days_{{ sub.id }}"`, `name="emails_{{ sub.id }}"` — POST handler iterates over a pre-fetched list of subscription IDs to read each field

Success state: redirect to `GET /notifications/settings?saved=1`, show dismissible Bootstrap alert "設定已儲存" at top of page if `?saved=1`.

Rows sorted by expiry date ascending (soonest first).

### POST Handler Logic

```python
@router.post("/notifications/settings")
def save_notification_settings(request: Request, ...):
    all_subs = list_uc.execute()
    for sub in all_subs:
        enabled = f"enabled_{sub.id}" in form_data  # checkbox present = True
        days_raw = form_data.get(f"days_{sub.id}")
        emails_raw = form_data.get(f"emails_{sub.id}", "")
        # validate days_raw is a valid NotificationDays value
        # call update_uc.execute(...) with only the notification fields updated,
        # all other fields taken from current sub entity
    return RedirectResponse("/notifications/settings?saved=1", status_code=303)
```

---

## File Map

| Action | File | Change |
|--------|------|--------|
| Modify | `src/domain/entities/subscription.py` | Add `notification_enabled: bool = True` |
| SQL    | SSMS | `ALTER TABLE` add `notification_enabled BIT NOT NULL DEFAULT 1` |
| Modify | `src/infrastructure/database/models.py` | Add `notification_enabled` column |
| Modify | `src/infrastructure/database/sql_subscription_repository.py` | Map `notification_enabled` in `_to_entity`, `add`, `update` |
| Modify | `src/application/use_cases/create_subscription.py` | Add `notification_enabled=True` param |
| Modify | `src/application/use_cases/update_subscription.py` | Add `notification_enabled` param |
| Modify | `src/application/use_cases/check_and_notify.py` | Filter `s.notification_enabled` in due_subs |
| Modify | `src/interfaces/web/routes/subscriptions.py` | Extract `annual_cost()` to module scope; add `GET /reports`; add `GET+POST /notifications/settings` |
| Modify | `src/interfaces/web/templates/base.html` | Sidebar layout + CSS variables + Inter font |
| Create | `src/interfaces/web/templates/reports.html` | 費用報表 template |
| Create | `src/interfaces/web/templates/notification_settings.html` | 通知設定 template |

---

## Testing

New unit tests needed:
1. `test_notification_enabled_defaults_true` — entity default
2. `test_check_and_notify_skips_disabled_subscriptions` — `notification_enabled=False` subs excluded from `due_subs`
3. `test_create_subscription_notification_enabled` — use case passes field through
4. `test_update_subscription_notification_enabled` — use case updates field

No tests needed for `/reports` route (pure aggregation, no business logic).
No tests needed for `base.html` visual changes.

---

## Out of Scope

- Phase 2B fields (`payment_account`, `auto_renew`, etc.) — covered by existing Phase 2B plan
- Mobile responsive sidebar — this is a desktop-first internal tool
- Dark mode
- Per-subscription notification *templates* (email body customization)
- Audit logging of notification setting changes
