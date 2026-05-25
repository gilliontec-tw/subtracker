# Frontend：登入頁 + 訂閱列表 設計規格

**日期：** 2026-05-25
**狀態：** 待實作

---

## 目標

實作前端 React 應用的登入頁與訂閱管理功能，包含登入/登出、訂閱列表（含篩選搜尋）、新增、編輯、刪除。

---

## 技術棧（已安裝）

- React 19 + TypeScript + Vite
- React Router DOM 6（路由）
- Zustand 5（auth 狀態）
- TanStack React Query 5（server data fetching）
- Axios（HTTP client）
- React Hook Form + Zod（表單驗證）
- shadcn/ui + Tailwind CSS（UI 元件）
- Lucide React（圖示）

---

## 架構

**狀態分工：**
- Zustand：只存 auth 狀態（`currentUser`、`setUser`、`clear`）
- React Query：管所有後端資料（訂閱列表、單筆查詢），負責快取與自動更新

**資料流：**
```
User action → React Hook Form → axios (帶 CSRF header) → API
                                                         ↓
                                            React Query invalidate cache
                                                         ↓
                                              UI 自動更新
```

---

## 檔案結構

```
frontend/src/
├── api/
│   ├── client.ts             # axios instance，自動帶 csrf_token header
│   ├── auth.ts               # login / logout / me
│   └── subscriptions.ts      # CRUD 呼叫
├── stores/
│   └── authStore.ts          # Zustand：currentUser + setUser + clear
├── layouts/
│   ├── AuthLayout.tsx        # 登入頁外層（頁面置中卡片）
│   └── AppLayout.tsx         # 主頁外層（頂部導覽列 + 主內容區）
├── components/
│   ├── ProtectedRoute.tsx                # 未登入 → redirect /login
│   └── subscriptions/
│       ├── SubscriptionTable.tsx         # 列表表格
│       ├── SubscriptionForm.tsx          # 新增/編輯共用表單
│       └── DeleteConfirmDialog.tsx       # 刪除確認 Dialog
├── pages/
│   ├── LoginPage.tsx
│   ├── SubscriptionsPage.tsx
│   ├── SubscriptionNewPage.tsx
│   └── SubscriptionEditPage.tsx
└── types/
    └── api.ts                # Subscription、User、ApiResponse 型別
```

---

## 路由

```
/login                      → LoginPage（AuthLayout，未登入可進）
/                           → redirect → /subscriptions
/subscriptions              → SubscriptionsPage（AppLayout，需登入）
/subscriptions/new          → SubscriptionNewPage（AppLayout，需登入）
/subscriptions/:id/edit     → SubscriptionEditPage（AppLayout，需登入）
```

---

## Auth 流程

**登入：**
1. POST `/api/v1/auth/login`（email + password）
2. 後端設 `access_token`（httpOnly）和 `csrf_token`（可讀）cookie
3. 成功後 Zustand 存 `currentUser`，redirect `/subscriptions`

**CSRF：**
- axios interceptor 在每次 POST/PUT/DELETE 請求前，從 `document.cookie` 讀取 `csrf_token`，加入 `x-csrf-token` header

**頁面重整持久化：**
- App 初始化時呼叫 `/api/v1/auth/me`
- 成功 → 填入 Zustand currentUser
- 401 → 清除 Zustand，ProtectedRoute 導向 `/login`

**登出：**
- POST `/api/v1/auth/logout`
- 清除 Zustand
- redirect `/login`

**ProtectedRoute：**
- `currentUser` 存在 → 正常渲染
- `/me` 載入中 → 顯示 loading spinner
- 確認未登入 → redirect `/login`

---

## 訂閱列表

**表格欄位（左至右）：**
服務名稱 → 帳號 → 部門 → 負責人 → 費用 → 到期日 → 狀態 → 操作

**到期日視覺提示：**
- ≤ 30 天：紅色文字 + 警示圖示
- 31–60 天：橘色文字
- 其餘：正常

**狀態 Badge：**
- `active` → 綠色
- `cancelled` → 灰色
- 其他（suspended、renewed）→ 灰色，不特別區分

**列表上方控制列：**
- 搜尋框：前端 filter，即時過濾服務名稱（不打 API）
- 「顯示已取消」開關：帶 `show_cancelled` 參數重新呼叫 API

**分頁：** 第一版不做，`limit=500` 一次全撈

**操作欄：**
- 編輯按鈕 → 跳到 `/subscriptions/:id/edit`
- 刪除按鈕 → 開確認 Dialog，確認後 DELETE，成功後 React Query invalidate

---

## 新增/編輯表單

**必填欄位：**
- 服務名稱（text）
- 到期日（date input）
- 帳號（text）
- 負責人（text）
- 部門（text）
- 計費週期（select：monthly / quarterly / semi_annual / annual / biennial）

**選填欄位：**
- 費用（number）、幣別（select：TWD / USD / EUR / JPY / GBP / CNY，預設 TWD）、匯率（幣別非 TWD 時才顯示）
- 付款帳號（text）、自動續費（checkbox）
- 試用到期日（date）、下次計費日（date）
- 通知信箱（多值輸入，Enter 新增 tag）、通知天數（number，預設 30）
- 狀態（select：active / renewed / cancelled / suspended，預設 active）
- 備註（textarea）

**Zod 驗證規則：**
- `service_name`：必填，不可空白
- `expiry_date`：必填，合法日期
- `login_account`：必填
- `owner_name`：必填
- `department`：必填
- `billing_cycle`：必填，需為有效選項
- `cost`：選填，若有值必須 > 0
- `exchange_rate`：選填，若有值必須 > 0

**編輯頁：**
- 進入時 GET `/subscriptions/:id` 取現有資料
- 用 `reset()` 填入表單預設值
- PUT 時只送有值的欄位（`exclude_unset` 由後端處理）

**新增/編輯共用 `SubscriptionForm` 元件：**
- props 接收 `defaultValues`（可選）和 `onSubmit`
- 新增頁傳空 defaultValues，編輯頁傳現有資料

---

## 錯誤處理

| 情境 | 處理方式 |
|------|----------|
| 401 | axios interceptor 清除 Zustand，redirect `/login` |
| 403 | toast「權限不足」|
| 422 | toast 顯示後端錯誤訊息 |
| 500 / 網路錯誤 | toast「伺服器錯誤，請稍後再試」|
| 表單本地驗證失敗 | 欄位下方紅色錯誤文字（React Hook Form）|
| 刪除成功 | toast「已刪除」，列表自動更新 |
| 新增/編輯成功 | redirect `/subscriptions`，toast「已儲存」|

---

## 不在此版本範圍

- 分頁
- 匯出 CSV / 報表
- 使用者管理（Admin 功能，Plan 4）
- 付款紀錄（Plan 3）
- 深色模式
