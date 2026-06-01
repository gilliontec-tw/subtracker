import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createPayment, updatePayment } from '@/api/payment_records'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useToast } from '@/hooks/use-toast'
import type { PaymentRecord } from '@/types/api'

const CURRENCIES = ['TWD', 'USD', 'EUR', 'JPY', 'GBP', 'CNY']

function pad(n: number) {
  return String(n).padStart(2, '0')
}

function todayStr(): string {
  const d = new Date()
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

const schema = z.object({
  payment_date: z.string().min(1, '必填'),
  amount: z
    .string()
    .min(1, '必填')
    .refine((v) => !isNaN(parseFloat(v)) && parseFloat(v) > 0, '請輸入有效金額'),
  currency: z.string().min(1, '必填'),
  notes: z.string().optional(),
})

type FormValues = z.infer<typeof schema>

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  subscriptionId?: number
  record?: PaymentRecord
}

export default function PaymentRecordFormDialog({
  open,
  onOpenChange,
  subscriptionId,
  record,
}: Props) {
  const isEdit = !!record
  const { toast } = useToast()
  const queryClient = useQueryClient()

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { payment_date: todayStr(), currency: 'TWD', notes: '' },
  })

  // eslint-disable-next-line react-hooks/incompatible-library
  const currency = watch('currency')

  useEffect(() => {
    if (open) {
      reset(
        record
          ? {
              payment_date: record.payment_date,
              amount: record.amount,
              currency: record.currency,
              notes: record.notes ?? '',
            }
          : { payment_date: todayStr(), amount: '', currency: 'TWD', notes: '' },
      )
    }
  }, [open, record, reset])

  const { mutate, isPending } = useMutation({
    mutationFn: (values: FormValues) => {
      if (isEdit && record) {
        return updatePayment(record.id, {
          ...values,
          notes: values.notes || null,
        })
      }
      return createPayment({
        subscription_id: subscriptionId!,
        ...values,
        notes: values.notes || undefined,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['payments'] })
      toast({ title: isEdit ? '付款紀錄已更新' : '付款紀錄已新增' })
      onOpenChange(false)
    },
    onError: () => {
      toast({ title: isEdit ? '更新失敗' : '新增失敗', variant: 'destructive' })
    },
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>{isEdit ? '編輯付款紀錄' : '新增付款紀錄'}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit((v) => mutate(v))} className="space-y-4 pt-2">
          <div>
            <label className="text-sm font-medium">付款日期</label>
            <Input type="date" {...register('payment_date')} className="mt-1" />
            {errors.payment_date && (
              <p className="mt-1 text-xs text-destructive">{errors.payment_date.message}</p>
            )}
          </div>
          <div>
            <label className="text-sm font-medium">金額</label>
            <Input type="number" step="0.01" min="0.01" {...register('amount')} className="mt-1" />
            {errors.amount && (
              <p className="mt-1 text-xs text-destructive">{errors.amount.message}</p>
            )}
          </div>
          <div>
            <label className="text-sm font-medium">幣別</label>
            <Select
              value={currency}
              onValueChange={(v) => setValue('currency', v, { shouldValidate: true })}
            >
              <SelectTrigger className="mt-1">
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
          </div>
          <div>
            <label className="text-sm font-medium">備註</label>
            <Input {...register('notes')} className="mt-1" placeholder="選填" />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isPending}
            >
              取消
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? '儲存中...' : '儲存'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
