/**
 * components/ProtectedRoute.tsx — 登入狀態守衛
 *
 * 作為路由的 wrapper，確保子頁面只有在登入後才能訪問。
 *
 * 流程：
 *  1. 若 authStore 中已有 currentUser（本次 session 已驗證過）→ 直接放行
 *  2. 若 currentUser 為 null → 呼叫 GET /auth/me 向後端確認 cookie 是否有效
 *  3. /auth/me 成功 → 將使用者資料寫入 authStore 後放行
 *  4. /auth/me 失敗（401）→ 顯示 → 導向 /login
 *
 * staleTime: Infinity 確保同一 session 只呼叫一次 /auth/me，
 * 不會因切換頁面而重複驗證。
 */
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
    enabled: currentUser === null, // 已有使用者資料時跳過，避免重複請求
    retry: false,
    staleTime: Infinity,           // 整個 session 只驗證一次
  })

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <span className="text-muted-foreground">載入中...</span>
      </div>
    )
  }

  // isLoading 結束但 currentUser 仍為 null，表示 /auth/me 失敗（未登入）
  if (!currentUser) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}
