# Dashboard 總覽頁 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增登入後首頁 Dashboard，顯示 5 張統計卡片（訂閱總數、即將到期、本月/下月費用、歷史付款總計）與即將到期清單，取代目前直接跳到訂閱列表的行為。

**Architecture:** 純前端實作，零後端改動。新增 `dashboardStats.ts` 純函式模組計算所有數字，`DashboardPage.tsx` 使用現有 `listSubscriptions` cache（`queryKey: ['subscriptions']`）加上一個新的 `listByFilters()` query 取得付款紀錄，在前端組合出統計結果。

**Tech Stack:** React 19, TanStack Query v5, TypeScript, shadcn/ui (`Card`, `Badge`, `Table`), Tailwind CSS v4

---

## File Map

| 動作 | 路徑 | 責任 |
|---|---|---|
| Create | `frontend/src/lib/dashboardStats.ts` | 純函式：費用換算 + 統計計算，與 React 完全解耦 |
| Create | `frontend/src/pages/DashboardPage.tsx` | Dashboard 頁面：查詢 + 組合統計 + 渲染卡片與到期清單 |
| Modify | `frontend/src/App.tsx` | 新增 `/dashboard` route；index redirect 改為 `/dashboard` |
| Modify | `frontend/src/layouts/AppLayout.tsx` | navLinks 最上方新增「總覽」連結 |

---

## Task 1: dashboardStats.ts — 純函式計算模組

**Files:**
- Create: `frontend/src/lib/dashboardStats.ts`

- [ ] **Step 1: 建立 `frontend/src/lib/` 目錄（若不存在）並建立 `dashboardStats.ts`**

建立檔案 `frontend/src/lib/dashboardStats.ts`，內容如下：

```typescript
import type { Subscription, PaymentRecord } from '@/types/api'

export interface ExpiringItem {
  id: number
  service_name: string
  expiry_date: string
  daysLeft: number
}

export interface DashboardStats {
  activeCount: number
  expiringCount: number
  thisMonthCost: number
  nextMonthCost: number
  historicalTotal: number
  expiringSubscriptions: ExpiringItem[]
}

function toCostTWD(sub: Subscription): number {
  if (sub.cost === null) return 0
  const cost = parseFloat(sub.cost)
  if (sub.currency === 'TWD' || sub.exchange_rate === null) return cost
  return cost * parseFloat(sub.exchange_rate)
}

function daysFromToday(dateStr: string): number {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const target = new Date(dateStr)
  target.setHours(0, 0, 0, 0)
  return Math.ceil((target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
}

function isInYearMonth(dateStr: string, year: number, month: number): boolean {
  const d = new Date(dateStr)
  return d.getFullYear() === year && d.getMonth() === month
}

export function computeStats(
  subscriptions: Subscription[],
  payments: PaymentRecord[],
): DashboardStats {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const thisYear = today.getFullYear()
  const thisMonth = today.getMonth()
  const nextMonthYear = thisMonth === 11 ? thisYear + 1 : thisYear
  const nextMonth = thisMonth === 11 ? 0 : thisMonth + 1

  const active = subscriptions.filter((s) => s.status === 'active')

  const expiringSubscriptions: ExpiringItem[] = active
    .map((s) => ({ ...s, daysLeft: daysFromToday(s.expiry_date) }))
    .filter((s) => s.daysLeft >= 0 && s.daysLeft <= 30)
    .map((s) => ({
      id: s.id,
      service_name: s.service_name,
      expiry_date: s.expiry_date,
      daysLeft: s.daysLeft,
    }))
    .sort((a, b) => a.daysLeft - b.daysLeft)

  const thisMonthCost = active
    .filter((s) => s.next_billing_date !== null && isInYearMonth(s.next_billing_date, thisYear, thisMonth))
    .reduce((sum, s) => sum + toCostTWD(s), 0)

  const nextMonthCost = active
    .filter((s) => s.next_billing_date !== null && isInYearMonth(s.next_billing_date, nextMonthYear, nextMonth))
    .reduce((sum, s) => sum + toCostTWD(s), 0)

  const historicalTotal = payments.reduce((sum, p) => sum + parseFloat(p.amount), 0)

  return {
    activeCount: active.length,
    expiringCount: expiringSubscriptions.length,
    thisMonthCost,
    nextMonthCost,
    historicalTotal,
    expiringSubscriptions,
  }
}
```

- [ ] **Step 2: 驗證 TypeScript 型別正確**

在 `frontend/` 目錄執行：

```bash
npx tsc --noEmit
```

Expected: 無錯誤輸出

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/dashboardStats.ts
git commit -m "feat: add dashboardStats computation module"
```

---

## Task 2: DashboardPage.tsx — Dashboard 頁面

**Files:**
- Create: `frontend/src/pages/DashboardPage.tsx`

- [ ] **Step 1: 建立 `frontend/src/pages/DashboardPage.tsx`**

```tsx
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { listSubscriptions } from '@/api/subscriptions'
import { listByFilters } from '@/api/payment_records'
import { computeStats } from '@/lib/dashboardStats'
import type { DashboardStats } from '@/lib/dashboardStats'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

function StatCard({ title, value }: { title: string; value: string }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-xl font-bold">{value}</p>
      </CardContent>
    </Card>
  )
}

function formatTWD(n: number): string {
  return `NT$ ${Math.round(n).toLocaleString('zh-TW')}`
}

function ExpiringTable({ items }: { items: DashboardStats['expiringSubscriptions'] }) {
  const navigate = useNavigate()

  if (items.length === 0) {
    return <p className="text-sm text-muted-foreground">目前沒有即將到期的訂閱</p>
  }

  return (
    <div className="rounded-md border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/50">
            <th className="px-4 py-3 text-left font-medium">服務名稱</th>
            <th className="px-4 py-3 text-left font-medium">到期日</th>
            <th className="px-4 py-3 text-left font-medium">剩餘天數</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr
              key={item.id}
              className="cursor-pointer border-b transition-colors last:border-0 hover:bg-muted/50"
              onClick={() => navigate('/subscriptions')}
            >
              <td className="px-4 py-3">{item.service_name}</td>
              <td className="px-4 py-3">{item.expiry_date}</td>
              <td className="px-4 py-3">
                <Badge variant={item.daysLeft <= 7 ? 'destructive' : 'secondary'}>
                  {item.daysLeft} 天
                </Badge>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function DashboardPage() {
  const { data: subsData } = useQuery({
    queryKey: ['subscriptions'],
    queryFn: () => listSubscriptions(),
  })

  const { data: payments } = useQuery({
    queryKey: ['payments'],
    queryFn: () => listByFilters(),
  })

  const stats = computeStats(subsData?.items ?? [], payments ?? [])

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">總覽</h1>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        <StatCard title="訂閱總數" value={`${stats.activeCount} 個`} />
        <StatCard title="即將到期" value={`${stats.expiringCount} 個`} />
        <StatCard title="本月費用" value={formatTWD(stats.thisMonthCost)} />
        <StatCard title="下月費用" value={formatTWD(stats.nextMonthCost)} />
        <StatCard title="歷史付款總計" value={formatTWD(stats.historicalTotal)} />
      </div>

      <div>
        <h2 className="mb-3 text-lg font-medium">即將到期（30 天內）</h2>
        <ExpiringTable items={stats.expiringSubscriptions} />
      </div>
    </div>
  )
}
```

- [ ] **Step 2: 驗證 TypeScript 型別正確**

在 `frontend/` 目錄執行：

```bash
npx tsc --noEmit
```

Expected: 無錯誤輸出

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/DashboardPage.tsx
git commit -m "feat: add DashboardPage with stats cards and expiring list"
```

---

## Task 3: 接線 — 路由 + 導覽列

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/layouts/AppLayout.tsx`

- [ ] **Step 1: 修改 `frontend/src/App.tsx`**

加入 import 與路由。完整修改後的 `App.tsx`：

```tsx
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from '@/components/ui/toaster'
import ProtectedRoute from '@/components/ProtectedRoute'
import AppLayout from '@/layouts/AppLayout'
import LoginPage from '@/pages/LoginPage'
import DashboardPage from '@/pages/DashboardPage'
import SubscriptionsPage from '@/pages/SubscriptionsPage'
import SubscriptionNewPage from '@/pages/SubscriptionNewPage'
import SubscriptionEditPage from '@/pages/SubscriptionEditPage'
import UsersPage from '@/pages/UsersPage'
import AuditLogPage from '@/pages/AuditLogPage'
import PaymentRecordsPage from '@/pages/PaymentRecordsPage'
import InvitePage from '@/pages/InvitePage'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000 } },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/invite/:token" element={<InvitePage />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<AppLayout />}>
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/subscriptions" element={<SubscriptionsPage />} />
              <Route path="/subscriptions/new" element={<SubscriptionNewPage />} />
              <Route path="/subscriptions/:id/edit" element={<SubscriptionEditPage />} />
              <Route path="/users" element={<UsersPage />} />
              <Route path="/audit-log" element={<AuditLogPage />} />
              <Route path="/payments" element={<PaymentRecordsPage />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      <Toaster />
    </QueryClientProvider>
  )
}
```

- [ ] **Step 2: 修改 `frontend/src/layouts/AppLayout.tsx`**

在 `navLinks` JSX 的最上方加入「總覽」連結。找到 `navLinks` 的定義（第 80–115 行），將整個 `navLinks` const 替換為：

```tsx
const navLinks = (
  <>
    <Link
      to="/dashboard"
      className="text-muted-foreground transition-colors hover:text-foreground"
      onClick={() => setMobileOpen(false)}
    >
      總覽
    </Link>
    <Link
      to="/subscriptions"
      className="text-muted-foreground transition-colors hover:text-foreground"
      onClick={() => setMobileOpen(false)}
    >
      訂閱列表
    </Link>
    <Link
      to="/payments"
      className="text-muted-foreground transition-colors hover:text-foreground"
      onClick={() => setMobileOpen(false)}
    >
      付款紀錄
    </Link>
    {currentUser?.role === 'admin' && (
      <>
        <Link
          to="/users"
          className="text-muted-foreground transition-colors hover:text-foreground"
          onClick={() => setMobileOpen(false)}
        >
          使用者管理
        </Link>
        <Link
          to="/audit-log"
          className="text-muted-foreground transition-colors hover:text-foreground"
          onClick={() => setMobileOpen(false)}
        >
          稽核日誌
        </Link>
      </>
    )}
  </>
)
```

- [ ] **Step 3: 執行 TypeScript 型別檢查**

在 `frontend/` 目錄執行：

```bash
npx tsc --noEmit
```

Expected: 無錯誤輸出

- [ ] **Step 4: 啟動 dev server 手動驗證**

在 `frontend/` 目錄執行：

```bash
npm run dev
```

瀏覽 `http://localhost:5173`，確認：
- 登入後自動跳轉到 `/dashboard`
- 導覽列最左顯示「總覽」連結
- 5 張統計卡片皆有數字顯示（即使是 NT$ 0 也算正常）
- 「即將到期（30 天內）」區塊存在，空白時顯示提示文字
- 點擊到期列表中的任一列可跳轉到 `/subscriptions`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/layouts/AppLayout.tsx
git commit -m "feat: wire dashboard route and nav link"
```
