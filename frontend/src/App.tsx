/**
 * App.tsx — 應用程式根元件
 *
 * 設定全域 Provider（TanStack Query、React Router）並定義路由結構：
 *  - /login、/invite/:token：公開頁面，不需登入
 *  - 其餘路由：被 ProtectedRoute 包裹，未登入自動導向 /login
 *  - AppLayout：提供頂部導覽列與內容容器，所有受保護頁面共用
 *  - 根路由 / 自動導向 /dashboard
 *  - 未匹配路由自動導向 /（再跳至 /dashboard）
 *
 * TanStack Query 設定：
 *  - retry: 1  — API 失敗最多重試一次
 *  - staleTime: 30_000 — 資料 30 秒內不重新 fetch（減少不必要的請求）
 */
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
import SystemSettingsPage from '@/pages/SystemSettingsPage'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000 } },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* 公開頁面 */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/invite/:token" element={<InvitePage />} />

          {/* 受保護頁面：ProtectedRoute 驗證登入狀態，AppLayout 提供導覽列 */}
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
              <Route path="/settings" element={<SystemSettingsPage />} />
            </Route>
          </Route>

          {/* 未匹配路由導回首頁 */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>

      {/* Toaster 在 BrowserRouter 外層以確保任何頁面的 toast 都能顯示 */}
      <Toaster />
    </QueryClientProvider>
  )
}
