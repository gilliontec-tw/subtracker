# Dashboard 總覽頁 Design Spec

## Goal

新增登入後首頁 Dashboard，讓用戶一眼掌握訂閱狀態與費用概況，取代目前直接跳到訂閱列表的行為。

## Scope

純前端實作，零後端改動。利用現有 API（`GET /api/v1/subscriptions`、`GET /api/v1/payments`）在前端計算所有統計數字。

---

## 路由與導覽

- 新增路由 `/dashboard` → `DashboardPage`
- `App.tsx` index redirect 從 `/subscriptions` 改為 `/dashboard`
- `AppLayout` 導覽列最上方新增「總覽」連結（`/dashboard`），其餘連結順序不變

---

## 頁面結構

### 統計卡片區（上方）

一排 5 張卡片，桌面橫排、手機 2 欄 grid：

| 卡片標題 | 資料來源 | 計算邏輯 |
|---|---|---|
| 訂閱總數 | `listSubscriptions` | `status === 'active'` 的數量 |
| 即將到期 | 同上 | `status === 'active'` 且 `expiry_date` 在今天起 30 天內的數量 |
| 本月費用 | 同上 | `next_billing_date` 落在當月，費用換算後加總（TWD） |
| 下月費用 | 同上 | `next_billing_date` 落在次月，費用換算後加總（TWD） |
| 歷史付款總計 | `listPayments` | 所有 payment_records 的 `amount` 加總（TWD） |

### 即將到期清單（下方）

- 取 `status === 'active'` 且 `expiry_date` 在今天起 30 天內的訂閱，依 `expiry_date` 升序排列
- 欄位：服務名稱、到期日、剩餘天數
- 剩餘天數 badge 顏色：≤ 7 天 → `destructive`（紅），≤ 30 天 → `secondary`（黃）
- 若無即將到期訂閱，顯示空白提示文字「目前沒有即將到期的訂閱」
- 點擊整列跳轉至 `/subscriptions`（使用 `useNavigate`）

---

## 費用換算規則

```
function toCostTWD(subscription):
  if cost is null → return 0
  if currency === 'TWD' or exchange_rate is null → return cost
  return cost × exchange_rate
```

幣別為 TWD 或 exchange_rate 為 null 時直接使用 cost 原值；其餘幣別乘以 exchange_rate。cost 為 null 的訂閱略過（不計入）。

---

## 資料查詢

| 查詢 key | API | 用途 |
|---|---|---|
| `['subscriptions']` | `GET /api/v1/subscriptions?limit=500&offset=0&show_cancelled=false` | 統計卡片 + 到期清單 |
| `['payments']` | `GET /api/v1/payments` | 歷史付款總計 |

兩個 `useQuery` 獨立發出，互不等待。

---

## 新增檔案

| 路徑 | 責任 |
|---|---|
| `frontend/src/pages/DashboardPage.tsx` | 頁面主體，組合卡片與清單 |
| `frontend/src/lib/dashboardStats.ts` | 純函式：`computeStats(subscriptions, payments)` 回傳所有統計數字 |

## 修改檔案

| 路徑 | 變更 |
|---|---|
| `frontend/src/App.tsx` | 新增 `DashboardPage` import + `/dashboard` route；index redirect 改為 `/dashboard` |
| `frontend/src/layouts/AppLayout.tsx` | 導覽列最上方新增「總覽」連結 |

---

## 型別定義

```typescript
// dashboardStats.ts
export interface DashboardStats {
  activeCount: number
  expiringCount: number       // 30 天內到期
  thisMonthCost: number       // TWD
  nextMonthCost: number       // TWD
  historicalTotal: number     // TWD
  expiringSubscriptions: ExpiringItem[]
}

export interface ExpiringItem {
  id: number
  service_name: string
  expiry_date: string         // ISO date string
  daysLeft: number
}
```

---

## 不在 Scope 內

- 圖表（折線圖、圓餅圖）
- 依部門 / 分類的費用分組
- 匯率換算以外的多幣別顯示
- 後端 stats API
