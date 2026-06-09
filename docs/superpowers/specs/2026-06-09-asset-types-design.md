# Asset Types — 項目管理擴充 Design

## Goal

將 SubTrack 從純 SaaS 訂閱追蹤擴充為通用「項目管理」，支援 ERP、網域等任何有到期日的企業資產，核心工作流程不變：到期前提醒續約。

## Architecture

擴充現有 `saas_subscriptions` 模型，新增 `asset_types` 參照表供管理員自訂類型。不新建獨立模組，不更名資料表。UI 層將「SaaS 訂閱」全面改為「項目管理」。

## Tech Stack

與現有系統相同：FastAPI + SQLAlchemy async（後端）、React 19 + TanStack Query（前端）、Alembic migration。

---

## 資料模型

### 新增 `asset_types` 表

| 欄位 | 類型 | 說明 |
|------|------|------|
| `id` | INTEGER PK | |
| `name` | VARCHAR(100) UNIQUE NOT NULL | 類型名稱，例如 "SaaS"、"ERP"、"網域" |
| `created_by` | INTEGER FK → users.id | |
| `created_at` | TIMESTAMP | |

系統預設資料在 Alembic migration 中 INSERT：`SaaS`、`ERP`、`網域`。

### 修改 `saas_subscriptions` 表

1. `asset_type_id` — `INTEGER NULL FK → asset_types.id`（現有資料保留 NULL，顯示為「未分類」）
2. `login_account` — 改為 `NULLABLE`（原為 NOT NULL）

---

## 後端

### AssetType Domain Entity

```python
@dataclass
class AssetType:
    name: str
    created_by: int | None = None
    id: int | None = None
    created_at: datetime | None = None
```

### AssetTypeRepository 介面

- `list_all() -> list[AssetType]`
- `get_by_id(id) -> AssetType | None`
- `save(entity) -> AssetType`（新增 / 更新）
- `delete(id) -> None`（若有訂閱使用中則拋 `ConflictException`）

### Use Cases

- `ListAssetTypesUseCase`
- `CreateAssetTypeUseCase`
- `UpdateAssetTypeUseCase`
- `DeleteAssetTypeUseCase`（刪前檢查是否有訂閱使用，有則拋 `ConflictException`）

### API 路由 `/api/v1/asset-types`

| Method | Path | 權限 | 說明 |
|--------|------|------|------|
| GET | `/` | 所有登入者 | 列出所有類型（供表單下拉使用） |
| POST | `/` | admin | 新增類型 |
| PATCH | `/{id}` | admin | 修改名稱 |
| DELETE | `/{id}` | admin | 刪除（使用中回傳 409） |

### Subscription 變更

- `Subscription.login_account` 改為 `str | None`
- `Subscription.asset_type_id` 新增 `int | None`
- `Subscription.asset_type_name` 新增 `str | None`（join 時帶出，非資料庫欄位）
- 所有讀取訂閱的 repository query left join `asset_types`
- 新增 / 編輯訂閱的 Pydantic schema 中 `login_account` 改為 `str | None`，新增 `asset_type_id: int | None`

---

## 前端

### API 層

新增 `frontend/src/api/asset_types.ts`：
- `listAssetTypes()` → `AssetType[]`
- `createAssetType(name)` → `AssetType`
- `updateAssetType(id, name)` → `AssetType`
- `deleteAssetType(id)` → `void`

### 項目清單頁（SubscriptionsPage）

- 表格新增「類型」欄，值來自 `subscription.asset_type_name`，無值顯示「—」
- 篩選列新增「類型」`<Select>` 下拉，選項從 `listAssetTypes()` 讀取，加一個「全部類型」選項
- 頁面標題「SaaS 訂閱」→「項目管理」

### 新增 / 編輯表單

- 新增「類型（選填）」`<Select>` 欄位，選項從 `listAssetTypes()` 讀取
- `login_account` 欄位 label 改為「登入帳號（選填）」，validation 移除必填限制

### Dashboard

- 到期提醒清單每筆加類型 badge（無類型則不顯示 badge）
- 到期清單上方加「類型」篩選下拉

### SystemSettingsPage — 「項目類型」區塊

在系統設定頁新增一個區塊，僅 admin 可見：
- 顯示所有類型名稱的清單
- 每筆右側有「編輯」（inline 輸入）和「刪除」按鈕
- 底部有「新增類型」輸入欄 + 送出按鈕
- 刪除使用中的類型顯示錯誤 toast

---

## 導覽標籤更新

所有介面中「SaaS 訂閱」→「項目管理」，包含：
- `AppLayout.tsx` 側邊導覽
- `SubscriptionsPage.tsx` 頁面標題
- `DashboardPage.tsx` 相關標題
- `document.title` 若有設定

---

## Domain Exceptions 變更

在 `backend/src/domain/exceptions.py` 新增：
```python
class ConflictException(DomainException):
    def __init__(self, message: str = "資源衝突") -> None:
        self.message = message
        super().__init__(message)
```

並在 `api/exception_handlers.py` 對應 HTTP 409。

---

## 錯誤處理

- 刪除使用中類型：後端回 409，前端 toast 顯示「此類型尚有項目使用，無法刪除」
- 類型名稱重複：後端回 409，前端 toast 顯示「此名稱已存在」

---

## 測試

- `test_create_asset_type.py`：建立類型、重複名稱應報錯
- `test_update_asset_type.py`：更新名稱
- `test_delete_asset_type.py`：刪除無使用中類型、刪除使用中類型應報錯
- `test_create_subscription.py`：`login_account=None` 應成功建立
- `test_list_subscriptions.py`：回傳資料包含 `asset_type_name`
