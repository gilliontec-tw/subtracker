import { useState } from 'react'
import { Link, Outlet, useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { logout, changePassword } from '@/api/auth'
import { useAuthStore } from '@/stores/authStore'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { useToast } from '@/hooks/use-toast'
import { Menu, X } from 'lucide-react'

const pwSchema = z
  .object({
    current_password: z.string().min(1, '請輸入目前密碼'),
    new_password: z.string().min(8, '新密碼至少 8 個字元'),
    confirm_password: z.string().min(1, '請確認新密碼'),
  })
  .refine((v) => v.new_password === v.confirm_password, {
    message: '新密碼不一致',
    path: ['confirm_password'],
  })
type PwForm = z.infer<typeof pwSchema>

function Field({ label, error, children }: { label: string; error?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <label className="text-sm font-medium">{label}</label>
      {children}
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  )
}

export default function AppLayout() {
  const navigate = useNavigate()
  const { currentUser, clear } = useAuthStore()
  const { toast } = useToast()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [pwOpen, setPwOpen] = useState(false)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<PwForm>({ resolver: zodResolver(pwSchema) })

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

  const { mutate: doChangePw, isPending: isChanging } = useMutation({
    mutationFn: (v: PwForm) => changePassword(v.current_password, v.new_password),
    onSuccess: () => {
      toast({ title: '密碼已更新' })
      setPwOpen(false)
      reset()
    },
    onError: (e: Error) => {
      toast({ title: e.message || '修改失敗', variant: 'destructive' })
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
              <Button variant="ghost" size="sm" onClick={() => setPwOpen(true)}>
                修改密碼
              </Button>
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

      <Dialog open={pwOpen} onOpenChange={(o) => { setPwOpen(o); if (!o) reset() }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>修改密碼</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit((v) => doChangePw(v))} className="space-y-4 pt-2">
            <Field label="目前密碼" error={errors.current_password?.message}>
              <Input type="password" autoComplete="current-password" {...register('current_password')} />
            </Field>
            <Field label="新密碼" error={errors.new_password?.message}>
              <Input type="password" autoComplete="new-password" {...register('new_password')} />
            </Field>
            <Field label="確認新密碼" error={errors.confirm_password?.message}>
              <Input type="password" autoComplete="new-password" {...register('confirm_password')} />
            </Field>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => { setPwOpen(false); reset() }}>
                取消
              </Button>
              <Button type="submit" disabled={isChanging}>
                {isChanging ? '更新中...' : '確認修改'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <main className="flex-1 px-4 py-6 sm:px-6 sm:py-8">
        <div className="mx-auto max-w-7xl">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
