import { useState } from 'react'
import { Link, Outlet, useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { logout } from '@/api/auth'
import { useAuthStore } from '@/stores/authStore'
import { Button } from '@/components/ui/button'
import { useToast } from '@/hooks/use-toast'
import { Menu, X } from 'lucide-react'

export default function AppLayout() {
  const navigate = useNavigate()
  const { currentUser, clear } = useAuthStore()
  const { toast } = useToast()
  const [mobileOpen, setMobileOpen] = useState(false)

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

  const navLinks = (
    <>
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

  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b bg-background">
        <div className="mx-auto max-w-7xl px-4 sm:px-6">
          <div className="flex h-14 items-center justify-between">
            <div className="flex items-center gap-6">
              <span className="text-lg font-semibold">SubTrack</span>
              <nav className="hidden items-center gap-4 text-sm sm:flex">
                {navLinks}
              </nav>
            </div>
            <div className="flex items-center gap-2 sm:gap-4">
              <span className="hidden text-sm text-muted-foreground sm:block">
                {currentUser?.display_name}
              </span>
              <Button variant="ghost" size="sm" onClick={() => doLogout()}>
                登出
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="sm:hidden"
                onClick={() => setMobileOpen((o) => !o)}
              >
                {mobileOpen ? <X className="size-5" /> : <Menu className="size-5" />}
              </Button>
            </div>
          </div>
        </div>

        {/* Mobile nav */}
        {mobileOpen && (
          <div className="border-t px-4 py-3 sm:hidden">
            <p className="mb-2 text-xs text-muted-foreground">{currentUser?.display_name}</p>
            <nav className="flex flex-col gap-3 text-sm">
              {navLinks}
            </nav>
          </div>
        )}
      </header>

      <main className="flex-1 px-4 py-6 sm:px-6 sm:py-8">
        <div className="mx-auto max-w-7xl">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
