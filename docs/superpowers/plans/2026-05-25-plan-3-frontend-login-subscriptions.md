# Frontend：登入頁 + 訂閱管理 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 實作前端 React 應用的登入頁與完整訂閱 CRUD（列表、新增、編輯、刪除）。

**Architecture:** Zustand 管 auth 狀態（currentUser），React Query 管所有後端資料（訂閱列表、單筆查詢），axios instance 自動帶 CSRF header 與攔截 401。路由用 React Router DOM 6，ProtectedRoute 作為 auth guard，AppLayout 提供導覽列外框。

**Tech Stack:** React 19、TypeScript、React Router DOM 6、Zustand 5、TanStack React Query 5、Axios、React Hook Form 7、Zod 4、shadcn/ui（Button、Input、Card、Table、Dialog、Select、Badge）、Lucide React、Tailwind CSS。

---

## 檔案結構

**新增：**
```
frontend/
├── .env.local                                       # VITE_API_URL
└── src/
    ├── types/
    │   └── api.ts                                   # User、Subscription、ApiResponse 型別
    ├── api/
    │   ├── client.ts                                # axios instance（CSRF + 401 interceptor）
    │   ├── auth.ts                                  # login / logout / getMe
    │   └── subscriptions.ts                         # list / get / create / update / delete
    ├── stores/
    │   └── authStore.ts                             # Zustand：currentUser + setUser + clear
    ├── layouts/
    │   ├── AuthLayout.tsx                           # 登入頁外框（置中卡片）
    │   └── AppLayout.tsx                            # 主頁外框（頂部導覽列 + Outlet）
    ├── components/
    │   ├── ProtectedRoute.tsx                       # auth guard，未登入 redirect /login
    │   └── subscriptions/
    │       ├── SubscriptionTable.tsx                # 訂閱列表表格
    │       ├── DeleteConfirmDialog.tsx              # 刪除確認對話框
    │       └── SubscriptionForm.tsx                 # 新增/編輯共用表單
    └── pages/
        ├── LoginPage.tsx
        ├── SubscriptionsPage.tsx
        ├── SubscriptionNewPage.tsx
        └── SubscriptionEditPage.tsx
```

**修改：**
```
frontend/src/App.tsx    # 改為 QueryClientProvider + BrowserRouter + 路由設定
```

---

## Task 1：Foundation — 型別、API client、Auth store

**Files:**
- Create: `frontend/.env.local`
- Create: `frontend/src/types/api.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/stores/authStore.ts`

- [ ] **Step 1：建立 `.env.local`**

```
VITE_API_URL=http://localhost:8000
```

- [ ] **Step 2：建立 `src/types/api.ts`**

```typescript
export type BillingCycle = 'monthly' | 'quarterly' | 'semi_annual' | 'annual' | 'biennial'
export type Currency = 'TWD' | 'USD' | 'EUR' | 'JPY' | 'GBP' | 'CNY'
export type SubscriptionStatus = 'active' | 'renewed' | 'cancelled' | 'suspended'

export interface User {
  id: number
  email: string
  display_name: string
  role: string
  can_create: boolean
  can_update: boolean
  can_delete: boolean
}

export interface Subscription {
  id: number
  service_name: string
  login_account: string
  expiry_date: string
  notification_emails: string[]
  notification_days: number
  cost: string | null
  currency: Currency
  exchange_rate: string | null
  notes: string | null
  owner_name: string | null
  category: string | null
  department: string | null
  billing_cycle: BillingCycle | null
  payment_account: string | null
  auto_renew: boolean
  trial_end_date: string | null
  next_billing_date: string | null
  status: SubscriptionStatus
  created_at: string
  updated_at: string
}

export interface ApiResponse<T> {
  success: boolean
  data: T | null
  message: string
  meta: Record<string, unknown> | null
}

export interface ListMeta {
  total: number
  limit: number
  offset: number
}

export interface ListResponse<T> {
  success: boolean
  data: T[]
  meta: ListMeta
}
```

- [ ] **Step 3：建立 `src/api/client.ts`**

```typescript
import axios from 'axios'
import { useAuthStore } from '@/stores/authStore'

function getCsrfToken(): string {
  const match = document.cookie.match(/csrf_token=([^;]+)/)
  return match ? decodeURIComponent(match[1]) : ''
}

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000',
  withCredentials: true,
})

api.interceptors.request.use((config) => {
  const method = config.method?.toUpperCase()
  if (method && ['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)) {
    config.headers['x-csrf-token'] = getCsrfToken()
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().clear()
    }
    return Promise.reject(error)
  },
)
```

- [ ] **Step 4：建立 `src/stores/authStore.ts`**

```typescript
import { create } from 'zustand'
import type { User } from '@/types/api'

interface AuthState {
  currentUser: User | null
  setUser: (user: User) => void
  clear: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  currentUser: null,
  setUser: (user) => set({ currentUser: user }),
  clear: () => set({ currentUser: null }),
}))
```

- [ ] **Step 5：確認 TypeScript 無錯誤**

```powershell
cd frontend
npx tsc --noEmit
```

預期：無錯誤輸出。

- [ ] **Step 6：Commit**

```powershell
git add frontend/.env.local frontend/src/types/api.ts frontend/src/api/client.ts frontend/src/stores/authStore.ts
git commit -m "feat(frontend): add types, axios client, and auth store"
```

---

## Task 2：App.tsx routing + Layouts + ProtectedRoute

**Files:**
- Replace: `frontend/src/App.tsx`
- Create: `frontend/src/layouts/AuthLayout.tsx`
- Create: `frontend/src/layouts/AppLayout.tsx`
- Create: `frontend/src/components/ProtectedRoute.tsx`

- [ ] **Step 1：建立 `src/layouts/AuthLayout.tsx`**

```tsx
import type { ReactNode } from 'react'

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30">
      <div className="w-full max-w-sm px-4">{children}</div>
    </div>
  )
}
```

- [ ] **Step 2：建立 `src/layouts/AppLayout.tsx`**

```tsx
import { Outlet, useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { logout } from '@/api/auth'
import { useAuthStore } from '@/stores/authStore'
import { Button } from '@/components/ui/button'
import { useToast } from '@/hooks/use-toast'

export default function AppLayout() {
  const navigate = useNavigate()
  const { currentUser, clear } = useAuthStore()
  const { toast } = useToast()

  const { mutate: doLogout } = useMutation({
    mutationFn: logout,
    onSuccess: () => {
      clear()
      navigate('/login', { replace: true })
    },
    onError: () => {
      toast({ title: '登出失敗', variant: 'destructive' })
    },
  })

  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b bg-background px-6 py-3">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <span className="text-lg font-semibold">SubTrack</span>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">{currentUser?.display_name}</span>
            <Button variant="ghost" size="sm" onClick={() => doLogout()}>
              登出
            </Button>
          </div>
        </div>
      </header>
      <main className="flex-1 px-6 py-8">
        <div className="mx-auto max-w-7xl">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
```

- [ ] **Step 3：建立 `src/components/ProtectedRoute.tsx`**

```tsx
import { Navigate, Outlet } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getMe } from '@/api/auth'
import { useAuthStore } from '@/stores/authStore'

export default function ProtectedRoute() {
  const { currentUser, setUser } = useAuthStore()

  const { isLoading } = useQuery({
    queryKey: ['me'],
    queryFn: async () => {
      const user = await getMe()
      setUser(user)
      return user
    },
    enabled: currentUser === null,
    retry: false,
    staleTime: Infinity,
  })

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <span className="text-muted-foreground">載入中...</span>
      </div>
    )
  }

  if (!currentUser) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}
```

- [ ] **Step 4：替換 `src/App.tsx`**

```tsx
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from '@/components/ui/toaster'
import ProtectedRoute from '@/components/ProtectedRoute'
import AppLayout from '@/layouts/AppLayout'
import LoginPage from '@/pages/LoginPage'
import SubscriptionsPage from '@/pages/SubscriptionsPage'
import SubscriptionNewPage from '@/pages/SubscriptionNewPage'
import SubscriptionEditPage from '@/pages/SubscriptionEditPage'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000 } },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<AppLayout />}>
              <Route index element={<Navigate to="/subscriptions" replace />} />
              <Route path="/subscriptions" element={<SubscriptionsPage />} />
              <Route path="/subscriptions/new" element={<SubscriptionNewPage />} />
              <Route path="/subscriptions/:id/edit" element={<SubscriptionEditPage />} />
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

注意：`LoginPage`、`SubscriptionsPage`、`SubscriptionNewPage`、`SubscriptionEditPage` 在後續 task 建立。目前 App.tsx 會有 TypeScript import 錯誤，下一步解決。

- [ ] **Step 5：建立空白佔位頁（讓 TypeScript 通過）**

暫時建立四個空頁面，後續 task 再填入完整內容：

```tsx
// src/pages/LoginPage.tsx
export default function LoginPage() { return <div>Login</div> }
```

```tsx
// src/pages/SubscriptionsPage.tsx
export default function SubscriptionsPage() { return <div>Subscriptions</div> }
```

```tsx
// src/pages/SubscriptionNewPage.tsx
export default function SubscriptionNewPage() { return <div>New</div> }
```

```tsx
// src/pages/SubscriptionEditPage.tsx
export default function SubscriptionEditPage() { return <div>Edit</div> }
```

- [ ] **Step 6：確認 TypeScript 與 dev server**

```powershell
cd frontend
npx tsc --noEmit
npm run dev
```

預期：dev server 啟動於 http://localhost:5173，開瀏覽器確認不會崩潰（顯示任意內容即可）。

- [ ] **Step 7：Commit**

```powershell
git add frontend/src/App.tsx frontend/src/layouts/ frontend/src/components/ProtectedRoute.tsx frontend/src/pages/
git commit -m "feat(frontend): add routing, layouts, and ProtectedRoute"
```

---

## Task 3：Auth API + LoginPage

**Files:**
- Create: `frontend/src/api/auth.ts`
- Replace: `frontend/src/pages/LoginPage.tsx`

- [ ] **Step 1：建立 `src/api/auth.ts`**

```typescript
import { api } from './client'
import type { ApiResponse, User } from '@/types/api'

export async function login(email: string, password: string): Promise<User> {
  const { data } = await api.post<ApiResponse<User>>('/api/v1/auth/login', { email, password })
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

export async function logout(): Promise<void> {
  await api.post('/api/v1/auth/logout')
}

export async function getMe(): Promise<User> {
  const { data } = await api.get<ApiResponse<User>>('/api/v1/auth/me')
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}
```

- [ ] **Step 2：替換 `src/pages/LoginPage.tsx`**

```tsx
import { Navigate, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation } from '@tanstack/react-query'
import { login } from '@/api/auth'
import { useAuthStore } from '@/stores/authStore'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useToast } from '@/hooks/use-toast'
import AuthLayout from '@/layouts/AuthLayout'

const schema = z.object({
  email: z.string().min(1, '請輸入 Email'),
  password: z.string().min(1, '請輸入密碼'),
})

type FormValues = z.infer<typeof schema>

export default function LoginPage() {
  const navigate = useNavigate()
  const { currentUser, setUser } = useAuthStore()
  const { toast } = useToast()

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  const { mutate, isPending } = useMutation({
    mutationFn: ({ email, password }: FormValues) => login(email, password),
    onSuccess: (user) => {
      setUser(user)
      navigate('/subscriptions', { replace: true })
    },
    onError: () => {
      toast({ title: '登入失敗', description: '帳號或密碼錯誤', variant: 'destructive' })
    },
  })

  if (currentUser) return <Navigate to="/subscriptions" replace />

  return (
    <AuthLayout>
      <Card>
        <CardHeader>
          <CardTitle className="text-center text-xl">SubTrack 登入</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit((data) => mutate(data))} className="space-y-4">
            <div className="space-y-1">
              <label htmlFor="email" className="text-sm font-medium">
                Email
              </label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="user@example.com"
                {...register('email')}
              />
              {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
            </div>
            <div className="space-y-1">
              <label htmlFor="password" className="text-sm font-medium">
                密碼
              </label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                {...register('password')}
              />
              {errors.password && (
                <p className="text-xs text-destructive">{errors.password.message}</p>
              )}
            </div>
            <Button type="submit" className="w-full" disabled={isPending}>
              {isPending ? '登入中...' : '登入'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </AuthLayout>
  )
}
```

- [ ] **Step 3：手動測試登入頁**

確認後端有在跑（`uvicorn api.main:app --port 8000 --reload`，在 `backend/` 目錄）。

開 http://localhost:5173/login：
- 頁面顯示 SubTrack 登入卡片
- 填入錯誤帳密 → toast 顯示「登入失敗」
- 填入 `admin@test.com` / `testpass123` → 成功跳轉 `/subscriptions`（目前顯示佔位文字）

- [ ] **Step 4：Commit**

```powershell
git add frontend/src/api/auth.ts frontend/src/pages/LoginPage.tsx
git commit -m "feat(frontend): add auth API and login page"
```

---

## Task 4：Subscriptions API + 列表元件

**Files:**
- Create: `frontend/src/api/subscriptions.ts`
- Create: `frontend/src/components/subscriptions/DeleteConfirmDialog.tsx`
- Create: `frontend/src/components/subscriptions/SubscriptionTable.tsx`

- [ ] **Step 1：建立 `src/api/subscriptions.ts`**

```typescript
import { api } from './client'
import type { ApiResponse, ListResponse, Subscription } from '@/types/api'

export async function listSubscriptions(
  showCancelled = false,
): Promise<{ items: Subscription[]; total: number }> {
  const { data } = await api.get<ListResponse<Subscription>>('/api/v1/subscriptions', {
    params: { limit: 500, offset: 0, show_cancelled: showCancelled },
  })
  return { items: data.data, total: data.meta.total }
}

export async function getSubscription(id: number): Promise<Subscription> {
  const { data } = await api.get<ApiResponse<Subscription>>(`/api/v1/subscriptions/${id}`)
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

export async function createSubscription(payload: Record<string, unknown>): Promise<Subscription> {
  const { data } = await api.post<ApiResponse<Subscription>>('/api/v1/subscriptions', payload)
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

export async function updateSubscription(
  id: number,
  payload: Record<string, unknown>,
): Promise<Subscription> {
  const { data } = await api.put<ApiResponse<Subscription>>(
    `/api/v1/subscriptions/${id}`,
    payload,
  )
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

export async function deleteSubscription(id: number): Promise<void> {
  await api.delete(`/api/v1/subscriptions/${id}`)
}
```

- [ ] **Step 2：建立 `src/components/subscriptions/DeleteConfirmDialog.tsx`**

```tsx
import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Trash2 } from 'lucide-react'
import { deleteSubscription } from '@/api/subscriptions'
import { useToast } from '@/hooks/use-toast'

interface Props {
  subscriptionId: number
  serviceName: string
}

export default function DeleteConfirmDialog({ subscriptionId, serviceName }: Props) {
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()
  const { toast } = useToast()

  const { mutate, isPending } = useMutation({
    mutationFn: () => deleteSubscription(subscriptionId),
    onSuccess: () => {
      setOpen(false)
      queryClient.invalidateQueries({ queryKey: ['subscriptions'] })
      toast({ title: `「${serviceName}」已刪除` })
    },
    onError: () => {
      toast({ title: '刪除失敗', variant: 'destructive' })
    },
  })

  return (
    <>
      <Button variant="ghost" size="icon" onClick={() => setOpen(true)}>
        <Trash2 className="size-4 text-destructive" />
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>確認刪除</DialogTitle>
            <DialogDescription>
              確定要刪除「{serviceName}」嗎？此操作無法復原。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)} disabled={isPending}>
              取消
            </Button>
            <Button variant="destructive" onClick={() => mutate()} disabled={isPending}>
              {isPending ? '刪除中...' : '確認刪除'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
```

- [ ] **Step 3：建立 `src/components/subscriptions/SubscriptionTable.tsx`**

```tsx
import { useNavigate } from 'react-router-dom'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { AlertCircle, Pencil } from 'lucide-react'
import DeleteConfirmDialog from './DeleteConfirmDialog'
import type { Subscription } from '@/types/api'

function daysUntil(dateStr: string): number {
  const expiry = new Date(dateStr)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  expiry.setHours(0, 0, 0, 0)
  return Math.ceil((expiry.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
}

function ExpiryCell({ date }: { date: string }) {
  const days = daysUntil(date)
  if (days <= 30) {
    return (
      <span className="flex items-center gap-1 font-medium text-red-600">
        <AlertCircle className="size-4" />
        {date}
      </span>
    )
  }
  if (days <= 60) {
    return <span className="text-orange-500">{date}</span>
  }
  return <span>{date}</span>
}

function StatusBadge({ status }: { status: string }) {
  if (status === 'active') {
    return (
      <Badge className="border-transparent bg-green-100 text-green-800 hover:bg-green-100">
        啟用中
      </Badge>
    )
  }
  if (status === 'cancelled') {
    return <Badge variant="secondary">已取消</Badge>
  }
  return <Badge variant="secondary">{status}</Badge>
}

function formatCost(cost: string | null, currency: string): string {
  if (!cost) return '—'
  return `${currency} ${cost}`
}

interface Props {
  subscriptions: Subscription[]
}

export default function SubscriptionTable({ subscriptions }: Props) {
  const navigate = useNavigate()

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>服務名稱</TableHead>
          <TableHead>帳號</TableHead>
          <TableHead>部門</TableHead>
          <TableHead>負責人</TableHead>
          <TableHead>費用</TableHead>
          <TableHead>到期日</TableHead>
          <TableHead>狀態</TableHead>
          <TableHead className="text-right">操作</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {subscriptions.length === 0 && (
          <TableRow>
            <TableCell colSpan={8} className="py-8 text-center text-muted-foreground">
              沒有訂閱資料
            </TableCell>
          </TableRow>
        )}
        {subscriptions.map((sub) => (
          <TableRow key={sub.id}>
            <TableCell className="font-medium">{sub.service_name}</TableCell>
            <TableCell className="text-muted-foreground">{sub.login_account || '—'}</TableCell>
            <TableCell>{sub.department || '—'}</TableCell>
            <TableCell>{sub.owner_name || '—'}</TableCell>
            <TableCell>{formatCost(sub.cost, sub.currency)}</TableCell>
            <TableCell>
              <ExpiryCell date={sub.expiry_date} />
            </TableCell>
            <TableCell>
              <StatusBadge status={sub.status} />
            </TableCell>
            <TableCell className="text-right">
              <div className="flex justify-end gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => navigate(`/subscriptions/${sub.id}/edit`)}
                >
                  <Pencil className="size-4" />
                </Button>
                <DeleteConfirmDialog subscriptionId={sub.id} serviceName={sub.service_name} />
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
```

- [ ] **Step 4：確認 TypeScript 無錯誤**

```powershell
cd frontend
npx tsc --noEmit
```

- [ ] **Step 5：Commit**

```powershell
git add frontend/src/api/subscriptions.ts frontend/src/components/subscriptions/
git commit -m "feat(frontend): add subscriptions API and list components"
```

---

## Task 5：SubscriptionsPage（列表頁）

**Files:**
- Replace: `frontend/src/pages/SubscriptionsPage.tsx`

- [ ] **Step 1：替換 `src/pages/SubscriptionsPage.tsx`**

```tsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { listSubscriptions } from '@/api/subscriptions'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import SubscriptionTable from '@/components/subscriptions/SubscriptionTable'
import { Plus } from 'lucide-react'

export default function SubscriptionsPage() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [showCancelled, setShowCancelled] = useState(false)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['subscriptions', showCancelled],
    queryFn: () => listSubscriptions(showCancelled),
  })

  const subscriptions = data?.items ?? []
  const filtered = subscriptions.filter((s) =>
    s.service_name.toLowerCase().includes(search.toLowerCase()),
  )

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">訂閱管理</h2>
        <Button onClick={() => navigate('/subscriptions/new')}>
          <Plus className="size-4" />
          新增訂閱
        </Button>
      </div>

      <div className="flex items-center gap-4">
        <Input
          placeholder="搜尋服務名稱..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-sm"
        />
        <label className="flex cursor-pointer items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={showCancelled}
            onChange={(e) => setShowCancelled(e.target.checked)}
            className="size-4"
          />
          顯示已取消
        </label>
      </div>

      {isLoading && <p className="text-muted-foreground">載入中...</p>}
      {isError && <p className="text-destructive">載入失敗，請重新整理頁面</p>}
      {!isLoading && !isError && <SubscriptionTable subscriptions={filtered} />}
    </div>
  )
}
```

- [ ] **Step 2：手動測試列表頁**

確認後端在跑。登入後：
- 訂閱列表顯示（若無資料顯示「沒有訂閱資料」）
- 搜尋框即時過濾
- 勾選「顯示已取消」後重新載入，包含已取消訂閱

- [ ] **Step 3：Commit**

```powershell
git add frontend/src/pages/SubscriptionsPage.tsx
git commit -m "feat(frontend): add subscriptions list page"
```

---

## Task 6：SubscriptionForm（共用表單元件）

**Files:**
- Create: `frontend/src/components/subscriptions/SubscriptionForm.tsx`

- [ ] **Step 1：建立 `src/components/subscriptions/SubscriptionForm.tsx`**

```tsx
import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { Subscription } from '@/types/api'

const BILLING_CYCLES = ['monthly', 'quarterly', 'semi_annual', 'annual', 'biennial'] as const
const BILLING_CYCLE_LABELS: Record<string, string> = {
  monthly: '每月',
  quarterly: '每季',
  semi_annual: '每半年',
  annual: '每年',
  biennial: '每兩年',
}

const CURRENCIES = ['TWD', 'USD', 'EUR', 'JPY', 'GBP', 'CNY'] as const
const STATUSES = ['active', 'renewed', 'cancelled', 'suspended'] as const
const STATUS_LABELS: Record<string, string> = {
  active: '啟用中',
  renewed: '已續約',
  cancelled: '已取消',
  suspended: '暫停',
}

const schema = z.object({
  service_name: z.string().min(1, '服務名稱為必填'),
  expiry_date: z.string().min(1, '到期日為必填'),
  login_account: z.string().min(1, '帳號為必填'),
  owner_name: z.string().min(1, '負責人為必填'),
  department: z.string().min(1, '部門為必填'),
  billing_cycle: z.enum(BILLING_CYCLES, { message: '請選擇計費週期' }),
  cost: z.string().optional(),
  currency: z.enum(CURRENCIES).default('TWD'),
  exchange_rate: z.string().optional(),
  payment_account: z.string().optional(),
  auto_renew: z.boolean().default(false),
  trial_end_date: z.string().optional(),
  next_billing_date: z.string().optional(),
  notification_emails: z.string().optional(),
  notification_days: z.string().default('30'),
  status: z.enum(STATUSES).default('active'),
  notes: z.string().optional(),
})

type FormValues = z.infer<typeof schema>

function buildPayload(values: FormValues): Record<string, unknown> {
  return {
    service_name: values.service_name,
    login_account: values.login_account,
    expiry_date: values.expiry_date,
    owner_name: values.owner_name,
    department: values.department,
    billing_cycle: values.billing_cycle,
    cost: values.cost || undefined,
    currency: values.currency,
    exchange_rate: values.currency !== 'TWD' && values.exchange_rate ? values.exchange_rate : undefined,
    payment_account: values.payment_account || undefined,
    auto_renew: values.auto_renew,
    trial_end_date: values.trial_end_date || undefined,
    next_billing_date: values.next_billing_date || undefined,
    notification_emails: values.notification_emails
      ? values.notification_emails
          .split(',')
          .map((e) => e.trim())
          .filter(Boolean)
      : [],
    notification_days: parseInt(values.notification_days) || 30,
    status: values.status,
    notes: values.notes || undefined,
  }
}

export function toFormValues(sub: Subscription): FormValues {
  return {
    service_name: sub.service_name,
    login_account: sub.login_account,
    expiry_date: sub.expiry_date,
    owner_name: sub.owner_name ?? '',
    department: sub.department ?? '',
    billing_cycle: sub.billing_cycle ?? 'monthly',
    cost: sub.cost ?? '',
    currency: sub.currency,
    exchange_rate: sub.exchange_rate ?? '',
    payment_account: sub.payment_account ?? '',
    auto_renew: sub.auto_renew,
    trial_end_date: sub.trial_end_date ?? '',
    next_billing_date: sub.next_billing_date ?? '',
    notification_emails: sub.notification_emails.join(', '),
    notification_days: String(sub.notification_days),
    status: sub.status,
    notes: sub.notes ?? '',
  }
}

interface Props {
  defaultValues?: FormValues
  onSubmit: (payload: Record<string, unknown>) => void
  isPending: boolean
  submitLabel: string
}

function FormField({
  label,
  error,
  children,
  required,
}: {
  label: string
  error?: string
  children: React.ReactNode
  required?: boolean
}) {
  return (
    <div className="space-y-1">
      <label className="text-sm font-medium">
        {label}
        {required && <span className="ml-1 text-destructive">*</span>}
      </label>
      {children}
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  )
}

export default function SubscriptionForm({
  defaultValues,
  onSubmit,
  isPending,
  submitLabel,
}: Props) {
  const navigate = useNavigate()
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: defaultValues ?? {
      currency: 'TWD',
      auto_renew: false,
      notification_days: '30',
      status: 'active',
    },
  })

  useEffect(() => {
    if (defaultValues) reset(defaultValues)
  }, [defaultValues, reset])

  const currency = watch('currency')

  return (
    <form onSubmit={handleSubmit((v) => onSubmit(buildPayload(v)))} className="space-y-8">
      {/* 必填欄位 */}
      <section className="space-y-4">
        <h3 className="text-base font-semibold">基本資訊</h3>
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField label="服務名稱" error={errors.service_name?.message} required>
            <Input {...register('service_name')} placeholder="GitHub" />
          </FormField>

          <FormField label="到期日" error={errors.expiry_date?.message} required>
            <Input type="date" {...register('expiry_date')} />
          </FormField>

          <FormField label="帳號" error={errors.login_account?.message} required>
            <Input {...register('login_account')} placeholder="user@corp.com" />
          </FormField>

          <FormField label="負責人" error={errors.owner_name?.message} required>
            <Input {...register('owner_name')} placeholder="王小明" />
          </FormField>

          <FormField label="部門" error={errors.department?.message} required>
            <Input {...register('department')} placeholder="工程部" />
          </FormField>

          <FormField label="計費週期" error={errors.billing_cycle?.message} required>
            <Select
              defaultValue={defaultValues?.billing_cycle}
              onValueChange={(v) => setValue('billing_cycle', v as FormValues['billing_cycle'], { shouldValidate: true })}
            >
              <SelectTrigger>
                <SelectValue placeholder="請選擇" />
              </SelectTrigger>
              <SelectContent>
                {BILLING_CYCLES.map((c) => (
                  <SelectItem key={c} value={c}>
                    {BILLING_CYCLE_LABELS[c]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FormField>
        </div>
      </section>

      {/* 費用 */}
      <section className="space-y-4">
        <h3 className="text-base font-semibold">費用</h3>
        <div className="grid gap-4 sm:grid-cols-3">
          <FormField label="費用" error={errors.cost?.message}>
            <Input type="number" step="0.01" min="0" {...register('cost')} placeholder="1200" />
          </FormField>

          <FormField label="幣別">
            <Select
              defaultValue={defaultValues?.currency ?? 'TWD'}
              onValueChange={(v) => setValue('currency', v as FormValues['currency'])}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {CURRENCIES.map((c) => (
                  <SelectItem key={c} value={c}>
                    {c}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FormField>

          {currency !== 'TWD' && (
            <FormField label="匯率（1 外幣 = ? TWD）" error={errors.exchange_rate?.message}>
              <Input
                type="number"
                step="0.000001"
                min="0"
                {...register('exchange_rate')}
                placeholder="31.5"
              />
            </FormField>
          )}
        </div>
      </section>

      {/* 其他資訊 */}
      <section className="space-y-4">
        <h3 className="text-base font-semibold">其他資訊</h3>
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField label="付款帳號">
            <Input {...register('payment_account')} placeholder="公司信用卡末四碼 1234" />
          </FormField>

          <FormField label="狀態">
            <Select
              defaultValue={defaultValues?.status ?? 'active'}
              onValueChange={(v) => setValue('status', v as FormValues['status'])}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {STATUSES.map((s) => (
                  <SelectItem key={s} value={s}>
                    {STATUS_LABELS[s]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FormField>

          <FormField label="試用到期日">
            <Input type="date" {...register('trial_end_date')} />
          </FormField>

          <FormField label="下次計費日">
            <Input type="date" {...register('next_billing_date')} />
          </FormField>
        </div>

        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" className="size-4" {...register('auto_renew')} />
          自動續費
        </label>
      </section>

      {/* 通知 */}
      <section className="space-y-4">
        <h3 className="text-base font-semibold">通知設定</h3>
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField label="通知信箱（多個請用逗號分隔）">
            <Input
              {...register('notification_emails')}
              placeholder="admin@corp.com, it@corp.com"
            />
          </FormField>
          <FormField label="到期前幾天通知">
            <Input type="number" min="1" {...register('notification_days')} />
          </FormField>
        </div>
      </section>

      {/* 備註 */}
      <section className="space-y-2">
        <h3 className="text-base font-semibold">備註</h3>
        <textarea
          {...register('notes')}
          rows={3}
          placeholder="備注事項..."
          className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-base placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
        />
      </section>

      <div className="flex gap-3">
        <Button type="submit" disabled={isPending}>
          {isPending ? '儲存中...' : submitLabel}
        </Button>
        <Button type="button" variant="outline" onClick={() => navigate('/subscriptions')}>
          取消
        </Button>
      </div>
    </form>
  )
}
```

- [ ] **Step 2：確認 TypeScript 無錯誤**

```powershell
cd frontend
npx tsc --noEmit
```

- [ ] **Step 3：Commit**

```powershell
git add frontend/src/components/subscriptions/SubscriptionForm.tsx
git commit -m "feat(frontend): add shared SubscriptionForm component"
```

---

## Task 7：New + Edit 頁面

**Files:**
- Replace: `frontend/src/pages/SubscriptionNewPage.tsx`
- Replace: `frontend/src/pages/SubscriptionEditPage.tsx`

- [ ] **Step 1：替換 `src/pages/SubscriptionNewPage.tsx`**

```tsx
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createSubscription } from '@/api/subscriptions'
import { useToast } from '@/hooks/use-toast'
import SubscriptionForm from '@/components/subscriptions/SubscriptionForm'

export default function SubscriptionNewPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { toast } = useToast()

  const { mutate, isPending } = useMutation({
    mutationFn: (payload: Record<string, unknown>) => createSubscription(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subscriptions'] })
      toast({ title: '訂閱已建立' })
      navigate('/subscriptions')
    },
    onError: () => {
      toast({ title: '建立失敗，請確認欄位後重試', variant: 'destructive' })
    },
  })

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">新增訂閱</h2>
      <SubscriptionForm onSubmit={mutate} isPending={isPending} submitLabel="建立" />
    </div>
  )
}
```

- [ ] **Step 2：替換 `src/pages/SubscriptionEditPage.tsx`**

```tsx
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getSubscription, updateSubscription } from '@/api/subscriptions'
import { useToast } from '@/hooks/use-toast'
import SubscriptionForm, { toFormValues } from '@/components/subscriptions/SubscriptionForm'

export default function SubscriptionEditPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { toast } = useToast()

  const subId = Number(id)

  const { data: subscription, isLoading, isError } = useQuery({
    queryKey: ['subscription', subId],
    queryFn: () => getSubscription(subId),
    enabled: !isNaN(subId),
  })

  const { mutate, isPending } = useMutation({
    mutationFn: (payload: Record<string, unknown>) => updateSubscription(subId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subscriptions'] })
      queryClient.invalidateQueries({ queryKey: ['subscription', subId] })
      toast({ title: '訂閱已更新' })
      navigate('/subscriptions')
    },
    onError: () => {
      toast({ title: '更新失敗，請確認欄位後重試', variant: 'destructive' })
    },
  })

  if (isLoading) return <p className="text-muted-foreground">載入中...</p>
  if (isError || !subscription) {
    return <p className="text-destructive">找不到此訂閱，請返回列表</p>
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">編輯訂閱</h2>
      <SubscriptionForm
        defaultValues={toFormValues(subscription)}
        onSubmit={mutate}
        isPending={isPending}
        submitLabel="儲存"
      />
    </div>
  )
}
```

- [ ] **Step 3：確認 TypeScript 無錯誤**

```powershell
cd frontend
npx tsc --noEmit
```

- [ ] **Step 4：端對端手動測試**

確認後端在跑。執行 `npm run dev`，測試以下流程：

1. **登入**：開 http://localhost:5173/login，用 `admin@test.com` / `testpass123` 登入 → 跳轉列表頁
2. **新增**：點「新增訂閱」→ 填入必填欄位（服務名稱、到期日、帳號、負責人、部門、計費週期）→ 點「建立」→ toast 顯示「訂閱已建立」→ 返回列表，新訂閱出現
3. **編輯**：點訂閱的鉛筆圖示 → 修改服務名稱 → 點「儲存」→ toast 顯示「訂閱已更新」→ 返回列表，名稱已更新
4. **刪除**：點垃圾桶圖示 → 確認對話框 → 確認 → toast 顯示「已刪除」→ 列表自動更新
5. **搜尋**：搜尋框輸入服務名稱 → 即時過濾
6. **登出**：點右上角「登出」→ 返回登入頁

- [ ] **Step 5：Commit**

```powershell
git add frontend/src/pages/SubscriptionNewPage.tsx frontend/src/pages/SubscriptionEditPage.tsx
git commit -m "feat(frontend): add new and edit subscription pages"
```

- [ ] **Step 6：Push**

```powershell
git push origin main
```

---

## 完成驗證清單

- [ ] 登入頁顯示正常，錯誤帳密顯示 toast 錯誤
- [ ] 登入成功跳轉訂閱列表
- [ ] 列表顯示所有欄位（服務名稱、帳號、部門、負責人、費用、到期日、狀態）
- [ ] 到期日 ≤30 天顯示紅色警示，31–60 天橘色
- [ ] 搜尋框即時過濾
- [ ] 「顯示已取消」切換後重新撈資料
- [ ] 新增訂閱、必填驗證、成功 toast
- [ ] 編輯訂閱、現有資料預填、成功 toast
- [ ] 刪除訂閱、確認對話框、成功 toast
- [ ] 登出後跳回登入頁，重整不會自動登入
