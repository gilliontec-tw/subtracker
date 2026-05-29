# Payment Records Design

## Goal

Add payment record tracking for subscriptions. Users can log manual payments against a subscription, view per-subscription history in the detail dialog, and browse all payments globally with date range and service name filters.

## Architecture

Flat routing under `/api/v1/payments`. No DB schema changes — `payment_records` table already exists with all required columns. Follows the same clean architecture pattern as subscriptions: domain entity → repository ABC → SQLAlchemy implementation → use cases → Pydantic schemas → router.

## Data Model

### PaymentRecord (domain entity)
```python
@dataclass
class PaymentRecord:
    subscription_id: int
    payment_date: date
    amount: Decimal
    currency: str
    source: str = "manual"        # always "manual" for UI-created records
    notes: str | None = None
    id: int | None = None
    created_at: datetime | None = None
    created_by: int | None = None
    service_name: str | None = None   # populated by JOIN queries; not stored in DB
```

No DB changes required. Existing `payment_records` table columns: `id`, `subscription_id`, `payment_date`, `amount`, `currency`, `source`, `notes`, `created_at`, `created_by`.

### Response shape
```json
{
  "id": 1,
  "subscription_id": 42,
  "service_name": "GitHub",
  "payment_date": "2026-05-29",
  "amount": "1200.00",
  "currency": "TWD",
  "notes": "年繳",
  "source": "manual",
  "created_at": "2026-05-29T15:30:00+00:00"
}
```

## API

### GET /api/v1/payments
- Auth: `get_current_user`
- Query params (two modes):
  - `subscription_id: int` — returns all payments for that subscription (used by detail dialog)
  - `from_date: date` + `to_date: date` + `service_name: str` (optional) — returns filtered list (used by global page)
- Returns: `ApiResponse[list[PaymentRecordResponse]]`, ordered by `payment_date DESC`

### POST /api/v1/payments
- Auth: `require_can_create`
- Body: `{ subscription_id, payment_date, amount, currency, notes? }`
- Returns: `ApiResponse[PaymentRecordResponse]`, status 201

### PUT /api/v1/payments/{id}
- Auth: `require_can_update`
- Body: `{ payment_date?, amount?, currency?, notes? }` (all optional)
- Returns: `ApiResponse[PaymentRecordResponse]`

### DELETE /api/v1/payments/{id}
- Auth: `require_can_delete`
- Returns: `ApiResponse[None]`

## Files

### New
| File | Purpose |
|------|---------|
| `backend/src/domain/entities/payment_record.py` | PaymentRecord dataclass |
| `backend/src/domain/repositories/payment_record_repository.py` | ABC: `save()`, `get()`, `list_by_subscription()`, `list_by_filters()`, `delete()` |
| `backend/src/infrastructure/database/repositories/payment_record_repository.py` | SQLAlchemy async impl; list queries JOIN saas_subscriptions for service_name; excludes soft-deleted subscriptions |
| `backend/src/application/use_cases/create_payment_record.py` | Receives `actor_user_id: int` via constructor; validates subscription exists (not soft-deleted), sets source="manual" and created_by=actor_user_id, saves |
| `backend/src/application/use_cases/update_payment_record.py` | Validates payment exists, applies partial updates, saves |
| `backend/src/application/use_cases/delete_payment_record.py` | Validates payment exists, deletes |
| `backend/src/application/use_cases/list_payment_records.py` | Routes to list_by_subscription or list_by_filters based on params |
| `backend/src/api/v1/schemas/payment_record.py` | PaymentRecordCreate, PaymentRecordUpdate, PaymentRecordResponse |
| `backend/src/api/v1/routers/payments.py` | 4 endpoints (GET list, POST, PUT /{id}, DELETE /{id}) |
| `frontend/src/api/payment_records.ts` | listBySubscription, listByFilters, create, update, remove |
| `frontend/src/components/payments/PaymentRecordList.tsx` | Table for detail dialog: 付款日期、金額、幣別、備註、操作; "新增付款" button |
| `frontend/src/components/payments/PaymentRecordFormDialog.tsx` | Create/edit dialog: 付款日期、金額、幣別 (Select)、備註 (optional) |
| `frontend/src/pages/PaymentRecordsPage.tsx` | Global page with date range + service name filter |

### Modified
| File | Change |
|------|--------|
| `backend/src/api/main.py` | Register payments router |
| `frontend/src/components/subscriptions/SubscriptionDetailDialog.tsx` | Add PaymentRecordList section at bottom |
| `frontend/src/layouts/AppLayout.tsx` | Add "付款紀錄" nav link (all authenticated users) |
| `frontend/src/App.tsx` | Add `/payments` route inside ProtectedRoute + AppLayout |

## Frontend

### SubscriptionDetailDialog — payment section
- Renders below subscription fields
- Table columns: 付款日期 | 金額 | 幣別 | 備註 | 操作
- "新增付款" button (visible when `can_create`)
- Per-row actions: 編輯 (`can_update`), 刪除 (`can_delete`)
- TanStack Query key: `['payments', 'subscription', subscriptionId]`

### PaymentRecordsPage (`/payments`)
- Date range inputs (from / to) + service name text input + "查詢" button
- Default range: today-30 → today; query fires only on button click
- Table columns: 付款日期 | 訂閱名稱 | 金額 | 幣別 | 備註 | 操作
- Per-row actions: 編輯 (`can_update`), 刪除 (`can_delete`)
- No create button
- TanStack Query key: `['payments', 'global', fromDate, toDate, serviceName]`

### PaymentRecordFormDialog
- Fields: 付款日期 (date input, required), 金額 (number input, required), 幣別 (Select: TWD/USD/EUR/JPY/GBP, default TWD), 備註 (textarea, optional)
- Used for both create (receives `subscriptionId`) and edit (receives existing `PaymentRecord`)
- On success: invalidate relevant query keys

## Permissions
Reuses existing subscription permission flags:
- View: any authenticated user
- Create: `can_create` (or admin)
- Edit: `can_update` (or admin)
- Delete: `can_delete` (or admin)

## Testing

Unit tests (mock repos):
- `CreatePaymentRecordUseCase` — valid subscription → saves with source="manual" and created_by set
- `CreatePaymentRecordUseCase` — soft-deleted subscription → raises NotFoundException
- `UpdatePaymentRecordUseCase` — existing payment → applies partial updates correctly
- `UpdatePaymentRecordUseCase` — non-existent payment → raises NotFoundException
- `DeletePaymentRecordUseCase` — non-existent payment → raises NotFoundException
- `ListPaymentRecordsUseCase` — subscription_id path → calls list_by_subscription
- `ListPaymentRecordsUseCase` — date range path → calls list_by_filters
