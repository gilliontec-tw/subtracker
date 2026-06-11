/**
 * pages/SystemSettingsPage.tsx — 系統設定頁面（僅管理員可存取）
 *
 * 分為兩大區塊：
 *  1. 系統設定表單（SMTP 郵件、App URL、通知排程）
 *  2. 項目類型管理（AssetTypesSection）
 *
 * SMTP 密碼特殊處理：
 *  - 讀取時後端不回傳明文，只回傳 smtp_password_set（boolean）
 *  - 表單預設空字串，留空送出表示「不更新密碼」
 *  - encryption_key_configured 為 false 時顯示警告，表示後端未設定加密金鑰，密碼無法儲存
 *
 * 測試寄信功能：使用表單「目前填入的值」寄測試信，不需要先儲存。
 */
import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useAuthStore } from '@/stores/authStore'
import { getSystemSettings, updateSystemSettings, testSmtpEmail } from '@/api/admin_settings'
import { listAssetTypes, createAssetType, updateAssetType, deleteAssetType } from '@/api/asset_types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useToast } from '@/hooks/use-toast'
import { Pencil, Trash2, Check, X } from 'lucide-react'

/** 系統設定表單的驗證規則 */
const schema = z.object({
  smtp_host: z.string(),
  smtp_port: z.number().int().min(1).max(65535),
  smtp_user: z.string(),
  smtp_password: z.string(),
  smtp_from: z.string(),
  smtp_sender_name: z.string(),
  app_url: z.string(),
  notification_cron_hour: z.number().int().min(0).max(23),
  notification_cron_minute: z.number().int().min(0).max(59),
})

type FormValues = z.infer<typeof schema>

/** 表單欄位包裝：label + 輸入框 + 提示文字 + 錯誤訊息 */
function FormField({
  label,
  error,
  children,
  hint,
}: {
  label: string
  error?: string
  children: React.ReactNode
  hint?: string
}) {
  return (
    <div className="space-y-1">
      <label className="text-sm font-medium">{label}</label>
      {children}
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  )
}

/**
 * 項目類型管理區塊（獨立元件）。
 * 支援新增、行內編輯（Enter 確認 / Escape 取消）、刪除。
 * 刪除時若有訂閱正在使用該類型，後端回傳錯誤，透過 toast 顯示。
 */
function AssetTypesSection() {
  const { toast } = useToast()
  const queryClient = useQueryClient()
  const [newName, setNewName] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editingName, setEditingName] = useState('')

  const { data: types = [] } = useQuery({
    queryKey: ['asset-types'],
    queryFn: listAssetTypes,
  })

  const { mutate: doCreate, isPending: isCreating } = useMutation({
    mutationFn: () => createAssetType(newName.trim()),
    onSuccess: () => {
      setNewName('')
      queryClient.invalidateQueries({ queryKey: ['asset-types'] })
    },
    onError: (err: Error) => toast({ title: err.message, variant: 'destructive' }),
  })

  const { mutate: doUpdate } = useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) => updateAssetType(id, name),
    onSuccess: () => {
      setEditingId(null)
      queryClient.invalidateQueries({ queryKey: ['asset-types'] })
    },
    onError: (err: Error) => toast({ title: err.message, variant: 'destructive' }),
  })

  const { mutate: doDelete } = useMutation({
    mutationFn: (id: number) => deleteAssetType(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['asset-types'] }),
    onError: (err: Error) => toast({ title: err.message, variant: 'destructive' }),
  })

  /** 進入行內編輯模式，預填現有名稱 */
  function startEdit(id: number, name: string) {
    setEditingId(id)
    setEditingName(name)
  }

  return (
    <section className="space-y-4">
      <h3 className="text-base font-semibold">項目類型</h3>
      <div className="rounded-lg border divide-y">
        {types.map((t) => (
          <div key={t.id} className="flex items-center gap-2 px-4 py-2.5">
            {editingId === t.id ? (
              // 編輯模式：輸入框 + 確認 / 取消按鈕
              <>
                <Input
                  value={editingName}
                  onChange={(e) => setEditingName(e.target.value)}
                  className="h-7 flex-1 text-sm"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') doUpdate({ id: t.id, name: editingName.trim() })
                    if (e.key === 'Escape') setEditingId(null)
                  }}
                  autoFocus
                />
                <Button variant="ghost" size="icon" className="size-7" onClick={() => doUpdate({ id: t.id, name: editingName.trim() })}>
                  <Check className="size-3.5" />
                </Button>
                <Button variant="ghost" size="icon" className="size-7" onClick={() => setEditingId(null)}>
                  <X className="size-3.5" />
                </Button>
              </>
            ) : (
              // 顯示模式：名稱 + 編輯 / 刪除按鈕
              <>
                <span className="flex-1 text-sm">{t.name}</span>
                <Button variant="ghost" size="icon" className="size-7" onClick={() => startEdit(t.id, t.name)}>
                  <Pencil className="size-3.5" />
                </Button>
                <Button variant="ghost" size="icon" className="size-7 text-destructive hover:text-destructive" onClick={() => doDelete(t.id)}>
                  <Trash2 className="size-3.5" />
                </Button>
              </>
            )}
          </div>
        ))}
        {types.length === 0 && (
          <p className="px-4 py-3 text-sm text-muted-foreground">尚無類型，請在下方新增</p>
        )}
      </div>
      {/* 新增類型輸入框，Enter 或點擊新增按鈕送出 */}
      <div className="flex gap-2">
        <Input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="新類型名稱"
          className="max-w-xs"
          onKeyDown={(e) => { if (e.key === 'Enter' && newName.trim()) doCreate() }}
        />
        <Button type="button" variant="outline" disabled={!newName.trim() || isCreating} onClick={() => doCreate()}>
          新增
        </Button>
      </div>
    </section>
  )
}

export default function SystemSettingsPage() {
  const currentUser = useAuthStore((s) => s.currentUser)
  const { toast } = useToast()
  const queryClient = useQueryClient()

  const { data: settings, isLoading } = useQuery({
    queryKey: ['system-settings'],
    queryFn: getSystemSettings,
  })

  const {
    register,
    handleSubmit,
    reset,
    getValues,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      smtp_host: '',
      smtp_port: 587,
      smtp_user: '',
      smtp_password: '',
      smtp_from: '',
      smtp_sender_name: 'SubTrack',
      app_url: '',
      notification_cron_hour: 8,
      notification_cron_minute: 0,
    },
  })

  // 設定載入後填入表單，smtp_password 故意留空（顯示 hint 說明留空不變）
  useEffect(() => {
    if (settings) {
      reset({
        smtp_host: settings.smtp_host,
        smtp_port: settings.smtp_port,
        smtp_user: settings.smtp_user,
        smtp_password: '',
        smtp_from: settings.smtp_from,
        smtp_sender_name: settings.smtp_sender_name,
        app_url: settings.app_url,
        notification_cron_hour: settings.notification_cron_hour,
        notification_cron_minute: settings.notification_cron_minute,
      })
    }
  }, [settings, reset])

  /** 儲存設定，smtp_password 空字串視為不更新（由後端判斷） */
  const { mutate: doSave, isPending: isSaving } = useMutation({
    mutationFn: (values: FormValues) =>
      updateSystemSettings({
        smtp_host: values.smtp_host,
        smtp_port: values.smtp_port || undefined,
        smtp_user: values.smtp_user,
        smtp_password: values.smtp_password || undefined,
        smtp_from: values.smtp_from,
        smtp_sender_name: values.smtp_sender_name,
        app_url: values.app_url,
        notification_cron_hour: values.notification_cron_hour,
        notification_cron_minute: values.notification_cron_minute,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['system-settings'] })
      toast({ title: '設定已儲存' })
    },
    onError: (err: Error) => toast({ title: err.message, variant: 'destructive' }),
  })

  /**
   * 測試寄信：取用表單「目前填入的值」（不需先儲存），
   * 直接呼叫後端試寄一封測試信到 smtp_from 信箱。
   */
  const { mutate: doTestEmail, isPending: isTesting } = useMutation({
    mutationFn: () => {
      const v = getValues()
      return testSmtpEmail({
        smtp_host: v.smtp_host,
        smtp_port: v.smtp_port,
        smtp_user: v.smtp_user,
        smtp_password: v.smtp_password || undefined,
        smtp_from: v.smtp_from,
        smtp_sender_name: v.smtp_sender_name,
      })
    },
    onSuccess: (msg) => toast({ title: msg }),
    onError: (err: Error) => toast({ title: err.message, variant: 'destructive' }),
  })

  // 非管理員直接導回 Dashboard
  if (currentUser?.role !== 'admin') return <Navigate to="/dashboard" replace />
  if (isLoading) return <div className="text-muted-foreground">載入中...</div>

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-6 text-xl font-semibold">系統設定</h1>

      <form onSubmit={handleSubmit((v) => doSave(v))} className="space-y-8">

        {/* 郵件伺服器設定 */}
        <section className="space-y-5">
          <h3 className="text-base font-semibold">郵件伺服器（SMTP）</h3>

          {/* 伺服器連線 */}
          <div className="rounded-lg border p-4 space-y-4">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">伺服器連線</p>
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField label="主機位址（Host）" error={errors.smtp_host?.message}>
                <Input {...register('smtp_host')} placeholder="smtp.gmail.com" />
              </FormField>
              <FormField label="連接埠（Port）" error={errors.smtp_port?.message}>
                <Input type="number" {...register('smtp_port', { valueAsNumber: true })} placeholder="587" />
              </FormField>
            </div>
          </div>

          {/* 登入認證 */}
          <div className="rounded-lg border p-4 space-y-4">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">登入認證</p>
            {/* encryption_key_configured 為 false 時表示後端未設定加密金鑰，密碼無法透過 UI 儲存 */}
            {settings && !settings.encryption_key_configured && (
              <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                未設定 <code>SETTINGS_ENCRYPTION_KEY</code>，密碼只能從 .env 讀取，無法透過此頁面修改。
              </div>
            )}
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField label="帳號（用於登入郵件伺服器）" error={errors.smtp_user?.message}>
                <Input {...register('smtp_user')} placeholder="service@corp.com" />
              </FormField>
              <FormField
                label="密碼（用於登入郵件伺服器）"
                error={errors.smtp_password?.message}
                hint={settings?.smtp_password_set ? '留空則不變' : '尚未設定'}
              >
                <Input
                  type="password"
                  autoComplete="new-password"
                  {...register('smtp_password')}
                  placeholder={settings?.smtp_password_set ? '留空則不變' : '請輸入密碼'}
                />
              </FormField>
            </div>
          </div>

          {/* 寄件人設定 */}
          <div className="rounded-lg border p-4 space-y-4">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">寄件人設定</p>
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField
                label="寄件人地址（From）"
                error={errors.smtp_from?.message}
                hint="顯示在收件人信件的寄件地址"
              >
                <Input {...register('smtp_from')} placeholder="service@corp.com" />
              </FormField>
              <FormField
                label="寄件人顯示名稱"
                error={errors.smtp_sender_name?.message}
                hint='收件人看到的名稱，例如「SubTrack」'
              >
                <Input {...register('smtp_sender_name')} placeholder="SubTrack" />
              </FormField>
            </div>
          </div>

          <Button
            type="button"
            variant="outline"
            disabled={isTesting}
            onClick={() => doTestEmail()}
          >
            {isTesting ? '寄送中...' : '測試寄信'}
          </Button>
        </section>

        {/* 應用程式設定 */}
        <section className="space-y-4">
          <h3 className="text-base font-semibold">應用程式設定</h3>
          <FormField
            label="App URL"
            error={errors.app_url?.message}
            hint="用於產生邀請連結和重設密碼連結，例如 http://192.168.1.7"
          >
            <Input {...register('app_url')} placeholder="http://192.168.1.7" />
          </FormField>
        </section>

        {/* 通知排程設定 */}
        <section className="space-y-4">
          <h3 className="text-base font-semibold">通知排程</h3>
          <p className="text-sm text-muted-foreground">每天固定時間發送到期提醒信件。</p>
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField
              label="發送時間：小時（0–23）"
              error={errors.notification_cron_hour?.message}
            >
              <Input type="number" min={0} max={23} {...register('notification_cron_hour', { valueAsNumber: true })} />
            </FormField>

            <FormField
              label="發送時間：分鐘（0–59）"
              error={errors.notification_cron_minute?.message}
            >
              <Input type="number" min={0} max={59} {...register('notification_cron_minute', { valueAsNumber: true })} />
            </FormField>
          </div>
        </section>

        <div className="border-t pt-6">
          <Button type="submit" disabled={isSaving}>
            {isSaving ? '儲存中...' : '儲存所有設定'}
          </Button>
        </div>
      </form>

      {/* 項目類型管理（獨立元件，與上方表單的儲存邏輯分開） */}
      <div className="mt-10 border-t pt-8">
        <AssetTypesSection />
      </div>
    </div>
  )
}
