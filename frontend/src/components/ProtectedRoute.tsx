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
