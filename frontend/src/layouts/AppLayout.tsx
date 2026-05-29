import { Link, Outlet, useNavigate } from 'react-router-dom'
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
          <div className="flex items-center gap-6">
            <span className="text-lg font-semibold">SubTrack</span>
            <nav className="flex items-center gap-4 text-sm">
              <Link
                to="/subscriptions"
                className="text-muted-foreground transition-colors hover:text-foreground"
              >
                訂閱列表
              </Link>
              {currentUser?.role === 'admin' && (
                <Link
                  to="/users"
                  className="text-muted-foreground transition-colors hover:text-foreground"
                >
                  使用者管理
                </Link>
              )}
            </nav>
          </div>
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
