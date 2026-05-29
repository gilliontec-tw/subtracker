import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from '@/components/ui/toaster'
import ProtectedRoute from '@/components/ProtectedRoute'
import AppLayout from '@/layouts/AppLayout'
import LoginPage from '@/pages/LoginPage'
import SubscriptionsPage from '@/pages/SubscriptionsPage'
import SubscriptionNewPage from '@/pages/SubscriptionNewPage'
import SubscriptionEditPage from '@/pages/SubscriptionEditPage'
import UsersPage from '@/pages/UsersPage'
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
              <Route index element={<Navigate to="/subscriptions" replace />} />
              <Route path="/subscriptions" element={<SubscriptionsPage />} />
              <Route path="/subscriptions/new" element={<SubscriptionNewPage />} />
              <Route path="/subscriptions/:id/edit" element={<SubscriptionEditPage />} />
              <Route path="/users" element={<UsersPage />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      <Toaster />
    </QueryClientProvider>
  )
}
