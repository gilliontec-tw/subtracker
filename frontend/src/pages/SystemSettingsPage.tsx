import { useEffect } from 'react'
import { Navigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useAuthStore } from '@/stores/authStore'
import { getSystemSettings, updateSystemSettings, testSmtpEmail } from '@/api/admin_settings'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useToast } from '@/hooks/use-toast'

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

export default function SystemSettingsPage() {
  const currentUser = useAuthStore((s) => s.currentUser)
  const { toast } = useToast()

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
    onSuccess: () => toast({ title: '設定已儲存' }),
    onError: (err: Error) => toast({ title: err.message, variant: 'destructive' }),
  })

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

  if (currentUser?.role !== 'admin') return <Navigate to="/dashboard" replace />
  if (isLoading) return <div className="text-muted-foreground">載入中...</div>

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-6 text-xl font-semibold">系統設定</h1>

      <form onSubmit={handleSubmit((v) => doSave(v))} className="space-y-8">

        {/* 郵件伺服器 */}
        <section className="space-y-4">
          <h3 className="text-base font-semibold">郵件伺服器（SMTP）</h3>

          {settings && !settings.encryption_key_configured && (
            <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              尚未設定加密金鑰（<code>SETTINGS_ENCRYPTION_KEY</code>），密碼無法儲存至資料庫，目前使用 .env 設定。
            </div>
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            <FormField label="SMTP Host" error={errors.smtp_host?.message}>
              <Input {...register('smtp_host')} placeholder="smtp.gmail.com" />
            </FormField>

            <FormField label="SMTP Port" error={errors.smtp_port?.message}>
              <Input type="number" {...register('smtp_port', { valueAsNumber: true })} placeholder="587" />
            </FormField>

            <FormField label="帳號" error={errors.smtp_user?.message}>
              <Input {...register('smtp_user')} placeholder="noreply@corp.com" />
            </FormField>

            <FormField
              label="密碼"
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

            <FormField label="寄件人 Email" error={errors.smtp_from?.message}>
              <Input {...register('smtp_from')} placeholder="noreply@corp.com" />
            </FormField>

            <FormField
              label="寄件人顯示名稱"
              error={errors.smtp_sender_name?.message}
              hint='顯示在收件人信箱，例如「SubTrack」'
            >
              <Input {...register('smtp_sender_name')} placeholder="SubTrack" />
            </FormField>
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

        {/* 通知排程 */}
        <section className="space-y-4">
          <h3 className="text-base font-semibold">通知排程</h3>
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField
              label="發送時間（小時，0–23）"
              error={errors.notification_cron_hour?.message}
            >
              <Input type="number" min={0} max={23} {...register('notification_cron_hour', { valueAsNumber: true })} />
            </FormField>

            <FormField
              label="發送時間（分鐘，0–59）"
              error={errors.notification_cron_minute?.message}
            >
              <Input type="number" min={0} max={59} {...register('notification_cron_minute', { valueAsNumber: true })} />
            </FormField>
          </div>
          <p className="text-xs text-muted-foreground">
            修改後需重新啟動 scheduler 服務才會生效（<code>docker compose restart scheduler</code>）
          </p>
        </section>

        <div className="border-t pt-6">
          <Button type="submit" disabled={isSaving}>
            {isSaving ? '儲存中...' : '儲存所有設定'}
          </Button>
        </div>
      </form>
    </div>
  )
}
