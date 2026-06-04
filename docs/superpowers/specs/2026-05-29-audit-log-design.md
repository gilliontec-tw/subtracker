# Audit Log Design

## Goal

Add audit logging for subscription create/update/delete operations, with an admin-only frontend page to browse log entries filtered by date range.

## Architecture

Use Case layer injection: the three subscription use cases (create/update/delete) receive an `AuditLogRepository` and actor info via constructor. Routers pass `current_user` and a `SqlAuditLogRepository` instance when calling these use cases.

No DB schema changes required — the existing `audit_log` table has all needed columns: `id`, `user_id`, `action`, `resource_type`, `resource_id`, `details` (JSON text), `created_at`.

## Files

### New
| File | Purpose |
|------|---------|
| `backend/src/domain/entities/audit_entry.py` | AuditEntry dataclass |
| `backend/src/domain/repositories/audit_log_repository.py` | Abstract interface: `save()`, `list_by_date_range()` |
| `backend/src/infrastructure/database/repositories/audit_log_repository.py` | SQLAlchemy async implementation |
| `backend/src/application/use_cases/list_audit_log.py` | Query by date range, returns list[AuditEntry] |
| `backend/src/api/v1/routers/audit_log.py` | GET /api/v1/audit-log |
| `backend/src/api/v1/schemas/audit_log.py` | AuditLogResponse schema |
| `frontend/src/api/audit_log.ts` | API client function |
| `frontend/src/pages/AuditLogPage.tsx` | Admin-only page with date filter + table |

### Modified
| File | Change |
|------|--------|
| `backend/src/application/use_cases/create_subscription.py` | Add `audit_repo` + `actor_user_id` + `actor_email` to `__init__`; write entry after save |
| `backend/src/application/use_cases/update_subscription.py` | Same; compute before/after diff for changed fields only |
| `backend/src/application/use_cases/delete_subscription.py` | Same; write entry before delete |
| `backend/src/api/v1/routers/subscriptions.py` | Change `_: User` to `current_user: User` on mutating endpoints; instantiate and pass audit repo |
| `backend/src/api/main.py` | Register audit_log router |
| `frontend/src/layouts/AppLayout.tsx` | Add "稽核日誌" nav link (admin only) |
| `frontend/src/App.tsx` | Add `/audit-log` route inside ProtectedRoute + AppLayout |

## Data Model

### AuditEntry (domain entity)
```python
@dataclass
class AuditEntry:
    user_id: int | None
    action: str            # "create" | "update" | "delete"
    resource_type: str     # "subscription"
    resource_id: int
    details: dict          # see structure below
    id: int | None = None
    created_at: datetime | None = None
```

### `details` JSON structure (stored in DB `details` column)

**create:**
```json
{"user_email": "admin@example.com", "service_name": "GitHub"}
```

**update:**
```json
{
  "user_email": "admin@example.com",
  "service_name": "GitHub",
  "changes": [
    {"field": "expiry_date", "before": "2025-01-01", "after": "2026-01-01"},
    {"field": "cost", "before": "1000", "after": "1200"}
  ]
}
```
Only fields where `old_value != new_value` are included.

**delete:**
```json
{"user_email": "admin@example.com", "service_name": "GitHub"}
```

## API

### GET /api/v1/audit-log
- Auth: `require_admin`
- Query params: `from_date: date`, `to_date: date`
- Returns up to 500 entries, ordered by `created_at DESC`

**Response item:**
```json
{
  "id": 1,
  "action": "update",
  "resource_id": 42,
  "user_email": "admin@example.com",
  "service_name": "GitHub",
  "changes": [{"field": "expiry_date", "before": "2025-01-01", "after": "2026-01-01"}],
  "created_at": "2026-05-29T10:30:00+08:00"
}
```
`changes` is `null` for create and delete entries.

## Frontend

### AuditLogPage (`/audit-log`)
- Admin only (enforced by backend 403 + frontend nav visibility)
- Date range filter: two `<input type="date">` fields (from / to), default = today-30 → today
- "查詢" button triggers query; TanStack Query key: `['audit-log', fromDate, toDate]`
- Table columns: 時間 | 操作者 | 動作 | 訂閱名稱 | 變更詳情

**動作欄：** 純文字，不用顏色
- create → 新增
- update → 編輯
- delete → 刪除

**變更詳情 column:**
- create / delete: `—`
- update: each change on its own line: `expiry_date: 2025-01-01 → 2026-01-01`

## Testing

Unit tests (mock repos):
- `CreateSubscriptionUseCase` — verify audit entry written with correct action/details
- `UpdateSubscriptionUseCase` — verify diff includes only changed fields; no entry written if no changes
- `DeleteSubscriptionUseCase` — verify audit entry written with service_name in details
- `ListAuditLogUseCase` — verify date range is passed to repo
