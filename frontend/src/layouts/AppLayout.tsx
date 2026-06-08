import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
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

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    isActive
      ? 'text-white font-semibold border-b-2 border-white/80 pb-0.5 transition-colors'
      : 'text-white/85 transition-colors hover:text-white font-medium'

  const desktopNavLinks = (
    <>
      <NavLink to="/dashboard" className={navLinkClass}>總覽</NavLink>
      <NavLink to="/subscriptions" className={navLinkClass}>訂閱列表</NavLink>
      <NavLink to="/payments" className={navLinkClass}>付款紀錄</NavLink>
      {currentUser?.role === 'admin' && (
        <>
          <NavLink to="/users" className={navLinkClass}>使用者管理</NavLink>
          <NavLink to="/audit-log" className={navLinkClass}>稽核日誌</NavLink>
          <NavLink to="/settings" className={navLinkClass}>系統設定</NavLink>
        </>
      )}
    </>
  )

  const mobileNavLinks = (
    <>
      <NavLink to="/dashboard" className={navLinkClass} onClick={() => setMobileOpen(false)}>總覽</NavLink>
      <NavLink to="/subscriptions" className={navLinkClass} onClick={() => setMobileOpen(false)}>訂閱列表</NavLink>
      <NavLink to="/payments" className={navLinkClass} onClick={() => setMobileOpen(false)}>付款紀錄</NavLink>
      {currentUser?.role === 'admin' && (
        <>
          <NavLink to="/users" className={navLinkClass} onClick={() => setMobileOpen(false)}>使用者管理</NavLink>
          <NavLink to="/audit-log" className={navLinkClass} onClick={() => setMobileOpen(false)}>稽核日誌</NavLink>
          <NavLink to="/settings" className={navLinkClass} onClick={() => setMobileOpen(false)}>系統設定</NavLink>
        </>
      )}
    </>
  )

  return (
    <div className="flex min-h-screen flex-col">
      <header style={{ backgroundColor: '#00a8e8' }}>
        <div className="mx-auto max-w-7xl px-4 sm:px-6">
          <div className="flex h-14 items-center justify-between">
            <div className="flex items-center gap-6">
              <span className="text-lg font-bold tracking-tight text-white">SubTrack</span>
              <nav className="hidden items-center gap-5 text-sm sm:flex">
                {desktopNavLinks}
              </nav>
            </div>
            <div className="flex items-center gap-1 sm:gap-2">
              <span className="hidden text-sm text-white/60 sm:block">
                {currentUser?.display_name}
              </span>
              <Button
                variant="ghost"
                size="sm"
                className="text-white/80 hover:bg-white/15 hover:text-white"
                onClick={() => setPwOpen(true)}
              >
                修改密碼
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="text-white/80 hover:bg-white/15 hover:text-white"
                onClick={() => doLogout()}
              >
                登出
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="text-white hover:bg-white/15 sm:hidden"
                onClick={() => setMobileOpen((o) => !o)}
              >
                {mobileOpen ? <X className="size-5" /> : <Menu className="size-5" />}
              </Button>
            </div>
          </div>
        </div>

        {mobileOpen && (
          <div className="border-t border-white/20 px-4 py-3 sm:hidden">
            <p className="mb-2 text-xs text-white/50">{currentUser?.display_name}</p>
            <nav className="flex flex-col gap-3 text-sm">
              {mobileNavLinks}
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

      <main className="flex-1 bg-slate-50 px-4 py-6 sm:px-6 sm:py-8">
        <div className="mx-auto max-w-7xl">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
