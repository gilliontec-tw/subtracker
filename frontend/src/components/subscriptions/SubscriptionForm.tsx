import { useEffect, useState } from 'react'
import { useAuthStore } from '@/stores/authStore'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { deleteSubscription } from '@/api/subscriptions'
import { useToast } from '@/hooks/use-toast'
import PaymentRecordList from '@/components/payments/PaymentRecordList'
import type { Subscription } from '@/types/api'

const BILLING_CYCLES = ['monthly', 'quarterly', 'semi_annual', 'annual', 'biennial'] as const
const BILLING_CYCLE_LABELS: Record<string, string> = {
  monthly: '每月',
  quarterly: '每季',
  semi_annual: '每半年',
  annual: '每年',
  biennial: '每兩年',
}

const CURRENCIES = ['TWD', 'USD', 'EUR', 'JPY', 'GBP', 'CNY'] as const
const STATUSES = ['active', 'suspended'] as const
const STATUS_LABELS: Record<string, string> = {
  active: '啟用中',
  suspended: '停用',
}

const schema = z.object({
  service_name: z.string().min(1, '服務名稱為必填'),
  expiry_date: z.string().min(1, '到期日為必填'),
  login_account: z.string().min(1, '帳號為必填'),
  owner_name: z.string().min(1, '負責人為必填'),
  department: z.string().min(1, '部門為必填'),
  billing_cycle: z.enum(BILLING_CYCLES, { error: '請選擇計費週期' }),
  cost: z.string().optional(),
  currency: z.enum(CURRENCIES).default('TWD'),
  exchange_rate: z.string().optional(),
  payment_account: z.string().optional(),
  auto_renew: z.boolean().default(false),
  trial_end_date: z.string().optional(),
  next_billing_date: z.string().optional(),
  notification_emails: z.string().optional(),
  notification_days: z.string().default('30').refine((v) => parseInt(v) > 0, '必須大於 0 天'),
  status: z.enum(STATUSES).default('active'),
  notes: z.string().optional(),
})

type FormValues = z.infer<typeof schema>

function buildPayload(values: FormValues): Record<string, unknown> {
  return {
    service_name: values.service_name,
    login_account: values.login_account,
    expiry_date: values.expiry_date,
    owner_name: values.owner_name,
    department: values.department,
    billing_cycle: values.billing_cycle,
    cost: values.cost || undefined,
    currency: values.currency,
    exchange_rate: values.currency !== 'TWD' && values.exchange_rate ? values.exchange_rate : undefined,
    payment_account: values.payment_account || undefined,
    auto_renew: values.auto_renew,
    trial_end_date: values.trial_end_date || undefined,
    next_billing_date: values.next_billing_date || undefined,
    notification_emails: values.notification_emails
      ? values.notification_emails
          .split(',')
          .map((e) => e.trim())
          .filter(Boolean)
      : [],
    notification_days: Math.max(1, parseInt(values.notification_days) || 30),
    status: values.status,
    notes: values.notes || undefined,
  }
}

// eslint-disable-next-line react-refresh/only-export-components
export function toFormValues(sub: Subscription): Partial<FormValues> {
  return {
    service_name: sub.service_name,
    login_account: sub.login_account,
    expiry_date: sub.expiry_date,
    owner_name: sub.owner_name ?? '',
    department: sub.department ?? '',
    billing_cycle: (BILLING_CYCLES as readonly string[]).includes(sub.billing_cycle ?? '')
      ? (sub.billing_cycle as FormValues['billing_cycle'])
      : undefined,
    cost: sub.cost ?? '',
    currency: sub.currency,
    exchange_rate: sub.exchange_rate ?? '',
    payment_account: sub.payment_account ?? '',
    auto_renew: sub.auto_renew,
    trial_end_date: sub.trial_end_date ?? '',
    next_billing_date: sub.next_billing_date ?? '',
    notification_emails: sub.notification_emails.join(', '),
    notification_days: String(sub.notification_days),
    status: sub.status,
    notes: sub.notes ?? '',
  }
}

interface Props {
  defaultValues?: Partial<FormValues>
  onSubmit: (payload: Record<string, unknown>) => void
  isPending: boolean
  submitLabel: string
  subscriptionId?: number
  serviceName?: string
}

function FormField({
  label,
  error,
  children,
  required,
}: {
  label: string
  error?: string
  children: React.ReactNode
  required?: boolean
}) {
  return (
    <div className="space-y-1">
      <label className="text-sm font-medium">
        {label}
        {required && <span className="ml-1 text-destructive">*</span>}
      </label>
      {children}
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  )
}

export default function SubscriptionForm({
  defaultValues,
  onSubmit,
  isPending,
  submitLabel,
  subscriptionId,
  serviceName,
}: Props) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const [deleteOpen, setDeleteOpen] = useState(false)
  const currentUser = useAuthStore((s) => s.currentUser)
  const canDelete = currentUser?.can_delete || currentUser?.role === 'admin'

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: defaultValues ?? {
      currency: 'TWD',
      auto_renew: false,
      notification_days: '30',
      status: 'active',
    },
  })

  useEffect(() => {
    if (defaultValues) reset(defaultValues)
  }, [defaultValues, reset])

  // eslint-disable-next-line react-hooks/incompatible-library
  const currency = watch('currency')
  const billingCycle = watch('billing_cycle')
  const statusVal = watch('status')

  const { mutate: deleteMutate, isPending: isDeleting } = useMutation({
    mutationFn: () => deleteSubscription(subscriptionId!),
    onSuccess: () => {
      setDeleteOpen(false)
      queryClient.invalidateQueries({ queryKey: ['subscriptions'] })
      toast({ title: `「${serviceName}」已刪除` })
      navigate('/subscriptions')
    },
    onError: () => {
      toast({ title: '刪除失敗', variant: 'destructive' })
    },
  })

  const isEditMode = subscriptionId !== undefined && serviceName !== undefined

  return (
    <form onSubmit={handleSubmit((v) => onSubmit(buildPayload(v)))} className="space-y-8">
      {/* 必填欄位 */}
      <section className="space-y-4">
        <h3 className="text-base font-semibold">基本資訊</h3>
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField label="服務名稱" error={errors.service_name?.message} required>
            <Input {...register('service_name')} placeholder="GitHub" />
          </FormField>

          <FormField label="到期日" error={errors.expiry_date?.message} required>
            <Input type="date" {...register('expiry_date')} />
          </FormField>

          <FormField label="帳號" error={errors.login_account?.message} required>
            <Input {...register('login_account')} placeholder="user@corp.com" />
          </FormField>

          <FormField label="負責人" error={errors.owner_name?.message} required>
            <Input {...register('owner_name')} placeholder="王小明" />
          </FormField>

          <FormField label="部門" error={errors.department?.message} required>
            <Input {...register('department')} placeholder="工程部" />
          </FormField>

          <FormField label="計費週期" error={errors.billing_cycle?.message} required>
            <Select
              value={billingCycle ?? ''}
              onValueChange={(v) => setValue('billing_cycle', v as FormValues['billing_cycle'], { shouldValidate: true })}
            >
              <SelectTrigger>
                <SelectValue placeholder="請選擇" />
              </SelectTrigger>
              <SelectContent>
                {BILLING_CYCLES.map((c) => (
                  <SelectItem key={c} value={c}>
                    {BILLING_CYCLE_LABELS[c]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FormField>
        </div>
      </section>

      {/* 費用 */}
      <section className="space-y-4">
        <h3 className="text-base font-semibold">費用</h3>
        <div className="grid gap-4 sm:grid-cols-3">
          <FormField label="費用" error={errors.cost?.message}>
            <Input type="number" step="0.01" min="0" {...register('cost')} placeholder="1200" />
          </FormField>

          <FormField label="幣別">
            <Select
              value={currency ?? 'TWD'}
              onValueChange={(v) => setValue('currency', v as FormValues['currency'], { shouldValidate: true })}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {CURRENCIES.map((c) => (
                  <SelectItem key={c} value={c}>
                    {c}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FormField>

          {currency !== 'TWD' && (
            <FormField label="匯率（1 外幣 = ? TWD）" error={errors.exchange_rate?.message}>
              <Input
                type="number"
                step="0.000001"
                min="0"
                {...register('exchange_rate')}
                placeholder="31.5"
              />
            </FormField>
          )}
        </div>
      </section>

      {/* 其他資訊 */}
      <section className="space-y-4">
        <h3 className="text-base font-semibold">其他資訊</h3>
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField label="付款帳號">
            <Input {...register('payment_account')} placeholder="公司信用卡末四碼 1234" />
          </FormField>

          <FormField label="狀態">
            <Select
              value={statusVal ?? 'active'}
              onValueChange={(v) => setValue('status', v as FormValues['status'], { shouldValidate: true })}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {STATUSES.map((s) => (
                  <SelectItem key={s} value={s}>
                    {STATUS_LABELS[s]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FormField>

          <FormField label="試用到期日">
            <Input type="date" {...register('trial_end_date')} />
          </FormField>

          <FormField label="下次計費日">
            <Input type="date" {...register('next_billing_date')} />
          </FormField>
        </div>

        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" className="size-4" {...register('auto_renew')} />
          自動續費
        </label>
      </section>

      {/* 通知 */}
      <section className="space-y-4">
        <h3 className="text-base font-semibold">通知設定</h3>
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField label="通知信箱（多個請用逗號分隔）">
            <Input
              {...register('notification_emails')}
              placeholder="admin@corp.com, it@corp.com"
            />
          </FormField>
          <FormField label="到期前幾天通知">
            <Input type="number" min="1" {...register('notification_days')} />
          </FormField>
        </div>
      </section>

      {/* 備註 */}
      <section className="space-y-2">
        <h3 className="text-base font-semibold">備註</h3>
        <textarea
          {...register('notes')}
          rows={3}
          placeholder="備注事項..."
          className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-base placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
        />
      </section>

      {/* 付款紀錄（僅編輯模式） */}
      {isEditMode && (
        <section className="border-t pt-6">
          <PaymentRecordList subscriptionId={subscriptionId!} />
        </section>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3 border-t pt-6">
        {isEditMode && canDelete ? (
          <Button type="button" variant="destructive" onClick={() => setDeleteOpen(true)}>
            刪除訂閱
          </Button>
        ) : <span />}
        <div className="flex gap-3">
          <Button type="submit" className="bg-green-600 hover:bg-green-700" disabled={isPending}>
            {isPending ? '儲存中...' : submitLabel}
          </Button>
          <Button type="button" variant="outline" onClick={() => navigate('/subscriptions')}>
            取消
          </Button>
        </div>
      </div>

      {/* 刪除確認 Dialog */}
      {isEditMode && (
        <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>確認刪除</DialogTitle>
              <DialogDescription>
                確定要刪除「{serviceName}」嗎？此操作無法復原。
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDeleteOpen(false)} disabled={isDeleting}>
                取消
              </Button>
              <Button variant="destructive" onClick={() => deleteMutate()} disabled={isDeleting}>
                {isDeleting ? '刪除中...' : '確認刪除'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </form>
  )
}
