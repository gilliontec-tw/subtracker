# Plan 2: Subscription CRUD 設計規格

**日期：** 2026-05-20
**狀態：** 待實作

---

## 目標

實作訂閱的完整 CRUD 後端 API，包含 domain entity、use case 層、repository 介面與 SQL 實作、API endpoints、以及單元與整合測試。

付款紀錄（renewal）和 Admin 使用者管理分別在 Plan 3、Plan 4 實作。

---

## 架構

採用 clean architecture，依賴方向由外向內：

```
router → use case → repository interface ← SQL implementation
```

每層只依賴下方的層，domain 層不引用任何 infrastructure 或 api 的程式碼。

---

## 檔案結構

**新增：**

```
backend/
└── src/
    ├── domain/
    │   ├── entities/
    │   │   └── subscription.py
    │   └── repositories/
    │       └── subscription_repository.py
    ├── application/
    │   └── use_cases/
    │       ├── list_subscriptions.py
    │       ├── get_subscription.py
    │       ├── create_subscription.py
    │       ├── update_subscription.py
    │       └── delete_subscription.py
    ├── infrastructure/
    │   └── database/
    │       └── repositories/
    │           └── subscription_repository.py
    └── api/
        └── v1/
            ├── routers/
            │   └── subscriptions.py
            └── schemas/
                └── subscription.py
tests/
├── unit/
│   ├── test_subscription_entity.py
│   ├── test_list_subscriptions_use_case.py
│   ├── test_get_subscription_use_case.py
│   ├── test_create_subscription_use_case.py
│   ├── test_update_subscription_use_case.py
│   └── test_delete_subscription_use_case.py
└── integration/
    └── test_subscription_endpoints.py
```

**修改：**

- `src/api/main.py` — include subscriptions router
- `src/api/dependencies.py` — 新增 `require_can_create`、`require_can_update`、`require_can_delete`

---

## Domain Entity

`src/domain/entities/subscription.py`：

```python
@dataclass
class Subscription:
    # 必填
    service_name: str
    login_account: str
    expiry_date: date
    notification_emails: list[str]
    notification_days: int

    # 選填業務欄位
    cost: Decimal | None = None
    currency: str = "TWD"          # 固定，不開放修改
    notes: str | None = None
    owner_name: str | None = None
    category: str | None = None
    department: str | None = None
    billing_cycle: str | None = None   # monthly|quarterly|semi_annual|annual|biennial
    payment_account: str | None = None
    auto_renew: bool = False
    trial_end_date: date | None = None
    next_billing_date: date | None = None
    status: str = "active"             # active|renewed|cancelled|suspended

    # 系統欄位
    id: int | None = None
    deleted_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
```

`currency` 固定為 `"TWD"`，CreateUseCase 強制覆寫此值，不接受前端傳入。

---

## Repository Interface

`src/domain/repositories/subscription_repository.py` 繼承 `BaseRepository[Subscription, int]`。

**序列化責任：** `notification_emails` 在 entity 層是 `list[str]`，在 DB 是 JSON-encoded `TEXT`。`SqlSubscriptionRepository` 負責 `json.dumps` / `json.loads` 轉換，上層（use case、router）只看到 `list[str]`。

| 方法 | 說明 |
|------|------|
| `list_paginated(limit, offset, show_cancelled)` | 回傳 `(list[Subscription], total: int)`。預設 filter `deleted_at IS NULL`。`show_cancelled=False` 時額外 filter `status != 'cancelled'`。排序固定 `expiry_date ASC`。 |
| `get_by_id(id)` | 繼承自 base，僅回傳 `deleted_at IS NULL` 的紀錄 |
| `save(entity)` | 繼承自 base，id=None → insert，id 有值 → update |
| `delete(id)` | Override base，設定 `deleted_at = now()`（soft delete），不實際刪除列 |

---

## Use Cases

所有 use case 採用同一模式：`__init__` 注入 repository，`execute()` 執行操作。

### ListSubscriptionsUseCase

- 輸入：`limit: int`、`offset: int`、`show_cancelled: bool`
- 呼叫：`repo.list_paginated()`
- 回傳：`(list[Subscription], total: int)`

### GetSubscriptionUseCase

- 輸入：`subscription_id: int`
- 呼叫：`repo.get_by_id()`
- 若無結果 → raise `NotFoundException`
- 回傳：`Subscription`

### CreateSubscriptionUseCase

- 輸入：所有建立所需欄位
- 強制 `currency = "TWD"`
- 呼叫：`repo.save(entity)`（id=None）
- 回傳：`Subscription`

### UpdateSubscriptionUseCase

- 輸入：`subscription_id: int` + 各欄位（皆選填）
- 先 `get_by_id` 確認存在，否則 `NotFoundException`
- 只更新有傳入的欄位，其餘保持原值
- 呼叫：`repo.save(entity)`（id 有值）
- 回傳：`Subscription`

### DeleteSubscriptionUseCase

- 輸入：`subscription_id: int`
- 先 `get_by_id` 確認存在，否則 `NotFoundException`
- 呼叫：`repo.delete(id)`（設 `deleted_at`）
- 回傳：None

---

## API Endpoints

**Base path：** `/api/v1/subscriptions`

| Method | Path | Use Case | 權限 |
|--------|------|----------|------|
| GET | `/` | ListSubscriptions | 任何已登入使用者 |
| POST | `/` | CreateSubscription | `require_can_create` |
| GET | `/{id}` | GetSubscription | 任何已登入使用者 |
| PUT | `/{id}` | UpdateSubscription | `require_can_update` |
| DELETE | `/{id}` | DeleteSubscription | `require_can_delete` |

### Query Parameters（GET /）

| 參數 | 類型 | 預設 | 說明 |
|------|------|------|------|
| `limit` | int | 50 | 每頁筆數 |
| `offset` | int | 0 | 偏移量 |
| `show_cancelled` | bool | false | 是否顯示已取消 |

### Response Format

**GET /（列表）：**
```json
{
  "success": true,
  "data": [ ...SubscriptionResponse ],
  "meta": { "total": 42, "limit": 50, "offset": 0 }
}
```

**其餘單筆操作：**
```json
{
  "success": true,
  "data": { ...SubscriptionResponse },
  "message": ""
}
```

### Schemas

**SubscriptionCreate**（POST body）：
- `service_name: str`（必填）
- `expiry_date: date`（必填）
- `login_account: str`（選填，預設空字串）
- `notification_emails: list[str]`（選填，預設空 list）
- `notification_days: int`（選填，預設 30）
- 其餘欄位全部選填

**SubscriptionUpdate**（PUT body）：所有欄位選填，只更新有傳的欄位。

**SubscriptionResponse**：完整欄位，含 `id`、`created_at`、`updated_at`，不含 `deleted_at`。

---

## 權限 Dependencies

新增至 `src/api/dependencies.py`：

```python
async def require_can_create(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role in ("admin", "manager") or current_user.can_create:
        return current_user
    raise ForbiddenException()

async def require_can_update(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role in ("admin", "manager") or current_user.can_update:
        return current_user
    raise ForbiddenException()

async def require_can_delete(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role in ("admin", "manager") or current_user.can_delete:
        return current_user
    raise ForbiddenException()
```

---

## 測試策略

### 單元測試（無需 DB）

每個 use case 對應一個測試檔，用 `MagicMock` mock repository：

| 測試檔 | 測試重點 |
|--------|----------|
| `test_list_subscriptions_use_case.py` | 分頁參數正確傳給 repo、show_cancelled 作用 |
| `test_get_subscription_use_case.py` | id 不存在時拋 NotFoundException |
| `test_create_subscription_use_case.py` | currency 強制為 TWD |
| `test_update_subscription_use_case.py` | 更新不存在的 id 拋 NotFoundException；只更新傳入欄位 |
| `test_delete_subscription_use_case.py` | 確認呼叫 soft delete 而非真刪；不存在時拋 NotFoundException |

### 整合測試（需要 DB + Redis）

`tests/integration/test_subscription_endpoints.py`：

- 完整 CRUD 流程：建立 → 取得 → 更新 → 刪除後 GET → 404
- 未登入 → 401
- `can_create=False` 的 user POST → 403
- `can_update=False` 的 user PUT → 403
- `can_delete=False` 的 user DELETE → 403
- `show_cancelled=false` 時不顯示 cancelled 訂閱
