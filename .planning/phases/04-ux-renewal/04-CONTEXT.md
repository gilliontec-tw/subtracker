# Phase 04: UX 改版 + 批量續訂 - Context

**Gathered:** 2026-06-01
**Status:** Ready for planning

<domain>
## Phase Boundary

重設計訂閱列表的操作流程、付款紀錄入口，並新增批量續訂功能。
具體包含：
1. 訂閱列表加 checkbox + 批量「續訂」按鈕
2. 訂閱列表每行加錢袋 icon（直接開「新增付款」dialog）
3. 刪除訂閱移到編輯頁，移除列表行的垃圾桶 icon
4. 全域付款紀錄頁加入編輯、刪除功能
5. 後端新增批量續訂 API endpoint

</domain>

<decisions>
## Implementation Decisions

### 付款紀錄入口
- **D-01:** 訂閱列表每行操作欄加一個錢袋（💰）icon（使用 lucide-react `Wallet` 或 `CreditCard` 圖示），點擊直接開「新增付款」dialog（PaymentRecordFormDialog），不經過 detail dialog
- **D-02:** Detail dialog 裡的 PaymentRecordList 區塊仍保留，仍可從那裡查看歷史紀錄與編輯/刪除

### 全域付款紀錄頁
- **D-03:** `PaymentRecordsPage` 的每筆紀錄加入編輯（鉛筆 icon）和刪除（垃圾桶 icon）操作，行為與 PaymentRecordList 一致（刪除前顯示確認 dialog）
- **D-04:** 全域頁無「新增付款」按鈕，新增只能從訂閱列表的錢袋 icon 進入

### 訂閱列表操作欄重設計
- **D-05:** 移除操作欄的垃圾桶 icon（刪除訂閱改到編輯頁）
- **D-06:** 操作欄保留：鉛筆（跳到編輯頁）+ 錢袋（開新增付款 dialog）
- **D-07:** 每行加入 checkbox，列表左側加全選 checkbox（表頭）
- **D-08:** 勾選至少一筆後，搜尋欄右側出現「續訂」按鈕；無勾選時隱藏

### 刪除訂閱
- **D-09:** 訂閱編輯頁（`/subscriptions/:id/edit`）底部加一個「刪除訂閱」危險操作按鈕，點擊後顯示確認 dialog 再執行刪除

### 批量續訂流程
- **D-10:** 點「續訂」後先顯示確認視窗，列出所有勾選的訂閱名稱與「舊到期日 → 新到期日」
- **D-11:** 新到期日計算：從**原到期日**往後延，依 `billing_cycle` 計算
  - monthly → +1 個月
  - quarterly → +3 個月
  - semi_annual → +6 個月
  - annual → +1 年
  - biennial → +2 年
  - `billing_cycle` 為 null 的訂閱：在確認視窗中標示警告「缺少計費週期，請先編輯訂閱」，並從本次續訂中排除（不更新）
- **D-12:** 續訂後只更新到期日，不自動建立付款紀錄
- **D-13:** 確認執行後，所有勾選訂閱的 checkbox 自動取消
- **D-14:** 只有 `status == "active"` 的訂閱可被續訂；已取消（cancelled）/暫停（suspended）的訂閱在確認視窗中標示警告並從本次續訂排除
- **D-15:** 計費週期（`billing_cycle`）在訂閱新增/編輯**前端表單**改為必填（不能儲存空值）；後端 schema 維持可空，不做資料 migration；現有空值訂閱下次編輯時才要求補填

### Claude's Discretion
- 錢袋 icon 具體使用哪個 lucide-react icon（建議 `Wallet` 或 `CreditCard`）
- 確認視窗的 UI 佈局細節
- 續訂 API 是單一 endpoint 批量處理，還是前端依序呼叫單筆更新

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 現有前端元件
- `frontend/src/components/subscriptions/SubscriptionTable.tsx` — 訂閱列表，需加 checkbox、錢袋 icon、移除垃圾桶
- `frontend/src/components/subscriptions/SubscriptionDetailDialog.tsx` — 詳情 dialog，保留 PaymentRecordList
- `frontend/src/components/subscriptions/SubscriptionForm.tsx` — 編輯頁，需加刪除按鈕
- `frontend/src/components/payments/PaymentRecordList.tsx` — 付款紀錄列表（detail dialog 內）
- `frontend/src/components/payments/PaymentRecordFormDialog.tsx` — 新增/編輯付款 dialog
- `frontend/src/pages/PaymentRecordsPage.tsx` — 全域付款頁，需加編輯/刪除

### 現有後端
- `backend/src/api/v1/routers/subscriptions.py` — 訂閱 API，需加批量續訂 endpoint
- `backend/src/application/use_cases/update_subscription.py` — 單筆更新 use case（批量續訂可複用）

### 架構慣例
- `backend/src/api/v1/schemas/base.py` — `ApiResponse[T]` 回應包裝
- `frontend/src/api/client.ts` — axios client，withCredentials + X-CSRF-Token

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `PaymentRecordFormDialog` — 已支援 create（傳 subscriptionId）和 edit（傳 record），直接在錢袋 icon 使用
- `DeleteConfirmDialog` — 已有刪除確認 dialog，刪除訂閱的確認可複用此元件
- `useAuthStore` — currentUser 的 can_create/can_update/can_delete/role 判斷，已在 PaymentRecordList 使用
- `updateSubscription` API 函數 — 現有單筆更新，批量續訂前端可依序呼叫

### Established Patterns
- TanStack Query `invalidateQueries({ queryKey: ['subscriptions'] })` — mutation 後失效快取
- `useMutation` + `useToast` — 標準操作回饋模式
- `require_can_update` — 後端更新權限 guard
- Form 中的 `Select` 元件用 `watch` + `setValue(..., { shouldValidate: true })` 控制

### Integration Points
- SubscriptionTable state 需新增：`selectedIds: Set<number>`（勾選狀態）
- 批量續訂後需 `invalidateQueries({ queryKey: ['subscriptions'] })`
- 付款紀錄新增後需 `invalidateQueries({ queryKey: ['payments'] })`

</code_context>

<specifics>
## Specific Ideas

- 使用者明確要求：勾選方式批量續訂，不是每行一個按鈕
- 「續訂」按鈕位置：搜尋欄旁邊（表格上方），只在有勾選時顯示
- 全域付款頁的操作行為要和 detail dialog 裡的 PaymentRecordList 一致

</specifics>

<deferred>
## Deferred Ideas

- **費用 Dashboard** — 各部門費用分析、各訂閱費用趨勢圖表，使用者提及但超出本次範圍，適合作為獨立的下一個 phase

</deferred>

---

*Phase: 04-ux-renewal*
*Context gathered: 2026-06-01*
