# Table & Analytics Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在訂閱列表加入到期日欄位與 CSV 匯出、在付款紀錄頁加入 TWD 合計、在 Dashboard 趨勢圖加入自訂日期區間。

**Architecture:** 四個功能皆為純前端修改，無後端 API 變更。A 與 C 修改 SubscriptionTable / SubscriptionsPage；D 修改 PaymentRecordsPage；F 修改 DashboardPage（TrendChart 改為自行計算 monthly buckets，不再依賴 computeStats）。

**Tech Stack:** React 19, TypeScript, TanStack Query v5, Tailwind CSS v4, recharts, shadcn/ui Table

---

## File Map

| 功能 | 修改檔案 |
|------|----------|
| A — 到期日欄位 | `frontend/src/components/subscriptions/SubscriptionTable.tsx` |
| C — CSV 匯出 | `frontend/src/pages/SubscriptionsPage.tsx` |
| D — 付款合計 | `frontend/src/pages/PaymentRecordsPage.tsx` |
| F — 趨勢圖區間 | `frontend/src/pages/DashboardPage.tsx` |

---

## Task 1: A — 訂閱列表加入到期日欄位

**Files:**
- Modify: `frontend/src/components/subscriptions/SubscriptionTable.tsx`

- [ ] **Step 1: 在 SubscriptionTable.tsx 的 import 區加入 `fmtDate`**

在現有第 16 行 `import type { Subscription } from '@/types/api'` 後面加：

```tsx
import { fmtDate } from '@/lib/utils'
```

- [ ] **Step 2: 擴充 SortKey 型別，加入 `'expiry_date'`**

將：
```ts
type SortKey = 'service_name' | 'login_account' | 'department' | 'owner_name' | 'cost' | 'billing_cycle' | 'status'
```
改為：
```ts
type SortKey = 'service_name' | 'login_account' | 'department' | 'owner_name' | 'cost' | 'billing_cycle' | 'expiry_date' | 'status'
```

- [ ] **Step 3: 在 `BILLING_CYCLE_LABELS` 之前加入 `daysFromToday` helper 與 `ExpiryCell` component**

```tsx
function daysFromToday(dateStr: string): number {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const target = new Date(dateStr)
  target.setHours(0, 0, 0, 0)
  return Math.ceil((target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
}

function ExpiryCell({ dateStr }: { dateStr: string }) {
  const days = daysFromToday(dateStr)
  const formatted = fmtDate(dateStr)
  if (days < 0) return <span className="text-slate-400 line-through">{formatted}</span>
  if (days <= 14) return <span className="font-semibold text-red-600">{formatted}</span>
  if (days <= 30) return <span className="text-amber-600">{formatted}</span>
  return <span className="text-slate-500">{formatted}</span>
}
```

- [ ] **Step 4: 在 `sortValue` 函數的 switch 中加入 `expiry_date` case**

在 `case 'status': return sub.status` 前插入：
```ts
case 'expiry_date': return sub.expiry_date
```

- [ ] **Step 5: 在表格 header 的「計費週期」後、「狀態」前插入「到期日」欄**

找到：
```tsx
{th('計費週期', 'billing_cycle')}
{th('狀態', 'status')}
```
改為：
```tsx
{th('計費週期', 'billing_cycle')}
{th('到期日', 'expiry_date')}
{th('狀態', 'status')}
```

- [ ] **Step 6: 在表格 body 的計費週期 cell 後、狀態 cell 前插入到期日 cell**

找到：
```tsx
<TableCell className="text-slate-500">
  {sub.billing_cycle ? (BILLING_CYCLE_LABELS[sub.billing_cycle] ?? sub.billing_cycle) : '—'}
</TableCell>
<TableCell>
  <StatusBadge status={sub.status} />
</TableCell>
```
改為：
```tsx
<TableCell className="text-slate-500">
  {sub.billing_cycle ? (BILLING_CYCLE_LABELS[sub.billing_cycle] ?? sub.billing_cycle) : '—'}
</TableCell>
<TableCell>
  <ExpiryCell dateStr={sub.expiry_date} />
</TableCell>
<TableCell>
  <StatusBadge status={sub.status} />
</TableCell>
```

- [ ] **Step 7: 更新空結果列的 colSpan**

找到：
```tsx
<TableCell colSpan={hasActions ? 9 : 8} className="py-8 text-center text-muted-foreground">
```
改為：
```tsx
<TableCell colSpan={hasActions ? 10 : 9} className="py-8 text-center text-muted-foreground">
```

- [ ] **Step 8: TypeScript 型別檢查**

```bash
cd frontend && npx tsc --noEmit
```
預期：無錯誤輸出

- [ ] **Step 9: Commit**

```bash
git add frontend/src/components/subscriptions/SubscriptionTable.tsx
git commit -m "feat: add expiry_date column with color urgency to subscription table"
```

---

## Task 2: C — 訂閱列表 CSV 匯出

**Files:**
- Modify: `frontend/src/pages/SubscriptionsPage.tsx`

- [ ] **Step 1: 在 SubscriptionsPage.tsx 的 import 區加入 Download icon**

找到：
```tsx
import { Plus } from 'lucide-react'
```
改為：
```tsx
import { Download, Plus } from 'lucide-react'
```

- [ ] **Step 2: 在 `export default function SubscriptionsPage()` 之前加入 `downloadCSV` 函數**

```tsx
const CYCLE_LABELS_CSV: Record<string, string> = {
  monthly: '月繳', quarterly: '季繳', semi_annual: '半年繳', annual: '年繳', biennial: '兩年繳',
}
const STATUS_LABELS_CSV: Record<string, string> = {
  active: '啟用中', renewed: '已續訂', cancelled: '已取消', suspended: '已暫停',
}

function downloadCSV(items: Subscription[]) {
  const headers = ['服務名稱', '登入帳號', '部門', '負責人', '費用', '幣別', '計費週期', '到期日', '狀態']
  const rows = items.map((s) => [
    s.service_name,
    s.login_account,
    s.department ?? '',
    s.owner_name ?? '',
    s.cost ?? '',
    s.currency,
    s.billing_cycle ? (CYCLE_LABELS_CSV[s.billing_cycle] ?? s.billing_cycle) : '',
    s.expiry_date,
    STATUS_LABELS_CSV[s.status] ?? s.status,
  ])
  const csv = [headers, ...rows]
    .map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(','))
    .join('\n')
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  const d = new Date()
  a.href = url
  a.download = `subscriptions-${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}.csv`
  a.click()
  URL.revokeObjectURL(url)
}
```

也需要加入 `Subscription` 型別 import（如果尚未 import）。在現有 import 區加：
```tsx
import type { Subscription } from '@/types/api'
```

- [ ] **Step 3: 在標題列加入「匯出 CSV」按鈕**

找到：
```tsx
<div className="flex items-center justify-between">
  <h2 className="text-2xl font-bold">訂閱管理</h2>
  {currentUser?.can_create && (
    <Button onClick={() => navigate('/subscriptions/new')}>
      <Plus className="size-4" />
      新增訂閱
    </Button>
  )}
</div>
```
改為：
```tsx
<div className="flex items-center justify-between">
  <h2 className="text-2xl font-bold">訂閱管理</h2>
  <div className="flex items-center gap-2">
    <Button variant="outline" onClick={() => downloadCSV(filtered)} disabled={filtered.length === 0}>
      <Download className="size-4" />
      匯出 CSV
    </Button>
    {currentUser?.can_create && (
      <Button onClick={() => navigate('/subscriptions/new')}>
        <Plus className="size-4" />
        新增訂閱
      </Button>
    )}
  </div>
</div>
```

- [ ] **Step 4: TypeScript 型別檢查**

```bash
cd frontend && npx tsc --noEmit
```
預期：無錯誤輸出

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/SubscriptionsPage.tsx
git commit -m "feat: add CSV export button to subscriptions page"
```

---

## Task 3: D — 付款紀錄 TWD 合計列

**Files:**
- Modify: `frontend/src/pages/PaymentRecordsPage.tsx`

- [ ] **Step 1: 在 import 區加入 `TableFooter`**

找到：
```tsx
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
```
改為：
```tsx
import {
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
```

- [ ] **Step 2: 將現有的 subscriptions query 改為永遠啟用**

找到：
```tsx
const { data: subsData } = useQuery({
  queryKey: ['subscriptions', false],
  queryFn: () => listSubscriptions(false),
  enabled: canCreate,
})
```
改為：
```tsx
const { data: subsData } = useQuery({
  queryKey: ['subscriptions', false],
  queryFn: () => listSubscriptions(false),
})
```

- [ ] **Step 3: 在 `const records = data ?? []` 下方加入合計計算邏輯**

```tsx
const subMap = new Map((subsData?.items ?? []).map((s) => [s.id, s]))
let unconvertibleCount = 0
const twdTotal = records.reduce((sum, p) => {
  const amount = parseFloat(p.amount)
  if (isNaN(amount)) return sum
  if (p.currency === 'TWD') return sum + amount
  const sub = subMap.get(p.subscription_id)
  if (!sub || !sub.exchange_rate) { unconvertibleCount++; return sum }
  const rate = parseFloat(sub.exchange_rate)
  if (isNaN(rate)) { unconvertibleCount++; return sum }
  return sum + amount * rate
}, 0)
```

- [ ] **Step 4: 在 `</TableBody>` 後加入合計 footer**

找到：
```tsx
          </TableBody>
        </Table>
```
改為：
```tsx
          </TableBody>
          {records.length > 0 && (
            <TableFooter>
              <TableRow>
                <TableCell colSpan={hasActions ? 6 : 5} className="text-right tabular-nums">
                  <span className="mr-4 text-sm text-slate-500">{records.length} 筆</span>
                  <span className="font-semibold text-slate-900">
                    合計：NT$ {Math.round(twdTotal).toLocaleString('zh-TW')}
                  </span>
                  {unconvertibleCount > 0 && (
                    <span className="ml-2 text-xs text-slate-400">
                      （另有 {unconvertibleCount} 筆外幣無法換算）
                    </span>
                  )}
                </TableCell>
              </TableRow>
            </TableFooter>
          )}
        </Table>
```

- [ ] **Step 5: TypeScript 型別檢查**

```bash
cd frontend && npx tsc --noEmit
```
預期：無錯誤輸出

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/PaymentRecordsPage.tsx
git commit -m "feat: add TWD total footer to payment records table"
```

---

## Task 4: F — Dashboard 趨勢圖自訂日期區間

**Files:**
- Modify: `frontend/src/pages/DashboardPage.tsx`

- [ ] **Step 1: 在 import 區加入 `Button` 與 `PaymentRecord` 型別**

找到：
```tsx
import type { Subscription } from '@/types/api'
```
改為：
```tsx
import { Button } from '@/components/ui/button'
import type { Subscription, PaymentRecord } from '@/types/api'
```

- [ ] **Step 2: 在 `DashboardPage` 函數之前加入 `initTrendFrom`、`initTrendTo` helper 與 `computeTrend` 函數**

在 `// ── Page ──` 區塊之前（約第 288 行附近）加入：

```tsx
// ── Trend helpers ─────────────────────────────────────────────
function pad2(n: number) { return String(n).padStart(2, '0') }

function initTrendFrom(): string {
  const d = new Date()
  d.setMonth(d.getMonth() - 11)
  d.setDate(1)
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-01`
}

function initTrendTo(): string {
  const d = new Date()
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`
}

function computeTrend(
  payments: PaymentRecord[],
  subs: Subscription[],
  fromDate: string,
  toDate: string,
): { month: string; cost: number }[] {
  const subMap = new Map(subs.map((s) => [s.id, s]))
  const from = new Date(fromDate)
  const to = new Date(toDate)
  const monthlyAmounts: Record<string, number> = {}

  for (const p of payments) {
    const d = new Date(p.payment_date)
    if (d < from || d > to) continue
    const key = `${d.getFullYear()}-${pad2(d.getMonth() + 1)}`
    const amount = parseFloat(p.amount)
    if (isNaN(amount)) continue
    let amountTWD: number
    if (p.currency === 'TWD') {
      amountTWD = amount
    } else {
      const sub = subMap.get(p.subscription_id)
      if (!sub || !sub.exchange_rate) continue
      const rate = parseFloat(sub.exchange_rate)
      if (isNaN(rate)) continue
      amountTWD = amount * rate
    }
    monthlyAmounts[key] = (monthlyAmounts[key] ?? 0) + amountTWD
  }

  const result: { month: string; cost: number }[] = []
  const today = new Date()
  const cursor = new Date(from.getFullYear(), from.getMonth(), 1)
  const toMonth = new Date(to.getFullYear(), to.getMonth(), 1)

  while (cursor <= toMonth && result.length < 36) {
    const key = `${cursor.getFullYear()}-${pad2(cursor.getMonth() + 1)}`
    const yearPrefix = cursor.getFullYear() !== today.getFullYear() ? `${cursor.getFullYear()}/` : ''
    result.push({ month: `${yearPrefix}${cursor.getMonth() + 1}月`, cost: monthlyAmounts[key] ?? 0 })
    cursor.setMonth(cursor.getMonth() + 1)
  }

  return result
}
```

- [ ] **Step 3: 修改 `TrendChart` component 的 props 簽名與內部邏輯**

將現有的：
```tsx
function TrendChart({ data }: { data: DashboardStats['monthlyTrend'] }) {
  const hasData = data.some((d) => d.cost > 0)
```
改為：
```tsx
function TrendChart({
  payments,
  subs,
  fromDate,
  toDate,
}: {
  payments: PaymentRecord[]
  subs: Subscription[]
  fromDate: string
  toDate: string
}) {
  const data = computeTrend(payments, subs, fromDate, toDate)
  const hasData = data.some((d) => d.cost > 0)
```

- [ ] **Step 4: 在 `DashboardPage` 函數內加入趨勢圖日期 state（緊接在 `navigate` 宣告後）**

找到：
```tsx
  const navigate = useNavigate()
  const { data: subsData, isLoading, isError: subsError } = useQuery({
```
改為：
```tsx
  const navigate = useNavigate()
  const [trendFrom, setTrendFrom] = useState(initTrendFrom)
  const [trendTo, setTrendTo] = useState(initTrendTo)
  const [appliedFrom, setAppliedFrom] = useState(initTrendFrom)
  const [appliedTo, setAppliedTo] = useState(initTrendTo)
  const { data: subsData, isLoading, isError: subsError } = useQuery({
```

- [ ] **Step 5: 更新 JSX 中「支出趨勢」區塊，加入日期選擇器並傳新 props 給 TrendChart**

找到：
```tsx
          {/* 趨勢 */}
          <div>
            <SectionTitle label="支出趨勢" />
            <TrendChart data={stats.monthlyTrend} />
          </div>
```
改為：
```tsx
          {/* 趨勢 */}
          <div>
            <SectionTitle label="支出趨勢" />
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <input
                type="date"
                value={trendFrom}
                max={trendTo}
                onChange={(e) => setTrendFrom(e.target.value)}
                className="rounded-md border px-3 py-1.5 text-sm"
              />
              <span className="text-sm text-slate-400">至</span>
              <input
                type="date"
                value={trendTo}
                min={trendFrom}
                onChange={(e) => setTrendTo(e.target.value)}
                className="rounded-md border px-3 py-1.5 text-sm"
              />
              <Button
                size="sm"
                variant="outline"
                onClick={() => { setAppliedFrom(trendFrom); setAppliedTo(trendTo) }}
              >
                套用
              </Button>
            </div>
            <TrendChart
              payments={payments ?? []}
              subs={subsData?.items ?? []}
              fromDate={appliedFrom}
              toDate={appliedTo}
            />
          </div>
```

- [ ] **Step 6: 移除 `DashboardStats` import 中不再使用的部分（如有 TypeScript 警告）**

找到：
```tsx
import type { DashboardStats, Breakdown } from '@/lib/dashboardStats'
```
確認 `DashboardStats` 是否還有其他用途（`ExpiringTable` 的 items 型別用到 `DashboardStats['expiringSubscriptions']`）。若有，保持原樣。若 TypeScript 報 unused import，改為：
```tsx
import type { DashboardStats, Breakdown } from '@/lib/dashboardStats'
```
（通常不需要改，`DashboardStats` 仍被 `ExpiringTable` 使用。）

- [ ] **Step 7: TypeScript 型別檢查**

```bash
cd frontend && npx tsc --noEmit
```
預期：無錯誤輸出

- [ ] **Step 8: Commit**

```bash
git add frontend/src/pages/DashboardPage.tsx
git commit -m "feat: add custom date range picker to dashboard trend chart"
```

---

## Self-Review Checklist

完成所有 task 後確認：

- [ ] A: 到期日欄位出現在計費週期右側，可點標題排序，≤14 天紅色、≤30 天橘色、已過期灰色刪除線
- [ ] C: 「匯出 CSV」按鈕在「訂閱管理」標題旁，下載的 CSV 以 BOM 開頭，Excel 可正確顯示中文
- [ ] D: 付款紀錄表格底部有合計列，TWD 合計正確，有外幣無法換算時顯示提示
- [ ] F: 趨勢圖上方有 from/to 日期輸入 + 套用按鈕，套用後 X 軸更新，最多顯示 36 個月
