# SubTrack — Table & Analytics Enhancements

**Date:** 2026-06-03
**Scope:** 前端 4 個獨立功能增強，無後端 API 變更

---

## 功能範圍

| ID | 功能 | 影響檔案 |
|----|------|----------|
| A | 訂閱列表加入到期日欄位（含排序與顏色警示） | `SubscriptionTable.tsx` |
| C | 訂閱列表 CSV 匯出 | `SubscriptionsPage.tsx`, `SubscriptionTable.tsx` |
| D | 付款紀錄 TWD 合計列 | `PaymentRecordsPage.tsx` |
| F | Dashboard 趨勢圖自訂日期區間 | `DashboardPage.tsx` |

---

## A — 訂閱列表：到期日欄位

### 位置
在現有「計費週期」欄右側插入「到期日」欄，兩欄並存。欄順序：
`服務名稱 | 帳號 | 部門 | 負責人 | 費用 | 計費週期 | 到期日 | 狀態 | 操作`

### 排序
`SortKey` union 新增 `'expiry_date'`。`sortValue` 中回傳 `sub.expiry_date`（字串 ISO 格式，lexicographic 排序即正確）。

### 顏色警示（與 Dashboard 一致）
- 到期日 > 30 天：`text-slate-500`（一般色）
- 到期日 ≤ 30 天：`text-amber-600`
- 到期日 ≤ 14 天：`text-red-600 font-semibold`
- 已過期（daysLeft < 0）：`text-slate-400 line-through`（已過期不高亮）

計算 daysLeft 用與 `dashboardStats.ts` 相同的 `daysFromToday` 邏輯（inline，不 import，避免循環依賴）。

---

## C — 訂閱列表：CSV 匯出

### 觸發位置
`SubscriptionsPage.tsx` 的標題列，「新增訂閱」按鈕左側加「匯出 CSV」按鈕（`variant="outline"`）。匯出的是目前 `filtered`（已套用搜尋/篩選）的陣列。

### CSV 欄位（依序）
`服務名稱, 登入帳號, 部門, 負責人, 費用, 幣別, 計費週期, 到期日, 狀態`

計費週期輸出中文標籤（`月繳/季繳/半年繳/年繳/兩年繳`），空值輸出空字串。

### 實作方式
純前端：用 `Blob` + `URL.createObjectURL` 觸發下載，檔名 `subscriptions-YYYY-MM-DD.csv`。UTF-8 BOM（`﻿`）開頭，確保 Excel 正確顯示中文。無需新 API。

### 按鈕可見性
所有登入使用者皆可匯出（不限 can_create/admin），因為查看列表本就是基本權限。

---

## D — 付款紀錄：TWD 合計列

### 位置
表格 `<tfoot>` 加合計列，顯示在最後一筆資料下方。

### 合計邏輯
與 `dashboardStats.ts` 的 `historicalTotal` 相同：
- 幣別為 TWD：直接累加
- 非 TWD：查找對應訂閱的 `exchange_rate` 換算
- 無法換算（找不到訂閱或無匯率）：累加 `unconvertibleCount`

顯示格式：`合計：NT$ 123,456`，若有無法換算筆數，後方加灰色小字 `（另有 X 筆外幣無法換算）`。

### 資料來源
`PaymentRecordsPage` 已有 `data`（當前篩選結果）。需要另外取得訂閱列表來查 exchange_rate。複用現有 `['subscriptions', false]` query（`listSubscriptions(false)`），`enabled: true`（不限 canCreate）。

### 空結果
0 筆時不顯示 tfoot（或顯示 `合計：NT$ 0`）。顯示 `NT$ 0`，保持佔位。

---

## F — Dashboard 趨勢圖：自訂日期區間

### UI
趨勢圖卡片標題列右側加兩個 `<input type="date">`（from / to），初始值：
- from：今天往前推 12 個月（第一天）
- to：今天

加一個小「套用」按鈕讓使用者確認（避免每次 keystroke 就重算）。

### 資料過濾
`DashboardPage` 已把所有付款資料存在 `payments`（`listByFilters()` 不帶參數），前端過濾即可，不需要新 query。

`TrendChart` component 接收新 props `fromDate: string` / `toDate: string` / `payments: PaymentRecord[]` / `subs: Subscription[]`，內部依此範圍決定要產生哪些月份 bucket 並過濾 payments。非 TWD 付款用 `subs` 的 exchange_rate 換算，邏輯與 `computeStats` 的 `monthlyAmounts` 段相同。

### X 軸顯示
依所選區間動態顯示月份。若區間 ≤ 12 個月，格式同現在（`1月`/`2026/1月`）；若 > 12 個月，同樣加年份前綴。最多支援 36 個月（超過則 clamp to 36M）。

### 狀態管理
`DashboardPage` 新增 `trendFrom` / `trendTo` state，初始為 12M 前到今天。`TrendChart` 接收這兩個值，`computeStats` 不變（仍負責其他統計）；趨勢圖改為在 component 內自行計算 monthly buckets，獨立於 `computeStats`。

---

## 不在範圍內

- 後端 API 變更
- 付款紀錄 CSV 匯出（未選）
- auto_renew 顯示（未選）
- 訂閱列表分頁

---

## 實作順序建議

1. **A** — 到期日欄位（改動 SubscriptionTable，其他功能不依賴它）
2. **C** — CSV 匯出（依賴 A 完成後才能含到期日欄位）
3. **D** — 付款合計（獨立，可與 A/C 並行）
4. **F** — 趨勢圖區間（獨立，可與 A/C/D 並行）
