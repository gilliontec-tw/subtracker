import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { batchRenewSubscriptions } from '@/api/subscriptions'
import { useToast } from '@/hooks/use-toast'
import { fmtDate } from '@/lib/utils'
import type { Subscription } from '@/types/api'

interface Props {
  subscriptions: Subscription[]
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: () => void
}

const CYCLE_LABELS: Record<string, string> = {
  monthly: '每月',
  quarterly: '每季',
  semi_annual: '每半年',
  annual: '每年',
  biennial: '每兩年',
}

function addCycle(dateStr: string, cycle: string): string {
  const [year, month, day] = dateStr.split('-').map(Number)
  let y = year, m = month // 1-indexed month
  switch (cycle) {
    case 'monthly':    m += 1;  break
    case 'quarterly':  m += 3;  break
    case 'semi_annual': m += 6; break
    case 'annual':     y += 1;  break
    case 'biennial':   y += 2;  break
  }
  while (m > 12) { m -= 12; y++ }
  // new Date(y, m, 0) = last day of month m (1-indexed), using 0-day-of-next-month trick
  const lastDay = new Date(y, m, 0).getDate()
  const d = Math.min(day, lastDay)
  return `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`
}

type EligibleEntry = {
  sub: Subscription
  eligible: true
  newExpiry: string
}

type IneligibleEntry = {
  sub: Subscription
  eligible: false
  reason: string
}

type Entry = EligibleEntry | IneligibleEntry

export default function BatchRenewDialog({ subscriptions, open, onOpenChange, onSuccess }: Props) {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  const entries: Entry[] = subscriptions.map((sub) => {
    if (sub.status !== 'active') {
      return { sub, eligible: false, reason: '狀態非啟用中，本次將略過' }
    }
    if (!sub.billing_cycle) {
      return { sub, eligible: false, reason: '缺少計費週期，請先編輯訂閱' }
    }
    return {
      sub,
      eligible: true,
      newExpiry: addCycle(sub.expiry_date, sub.billing_cycle),
    }
  })

  const eligibleIds = entries.filter((e): e is EligibleEntry => e.eligible).map((e) => e.sub.id)
  const eligibleCount = eligibleIds.length
  const skippedCount = entries.length - eligibleCount

  const mutation = useMutation({
    mutationFn: () => batchRenewSubscriptions(eligibleIds),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['subscriptions'] })
      toast({ title: `已續訂 ${result.renewed.length} 筆，略過 ${result.skipped.length} 筆` })
      onSuccess?.()
      onOpenChange(false)
    },
    onError: () => toast({ title: '批量續訂失敗', variant: 'destructive' }),
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>確認批量續訂</DialogTitle>
        </DialogHeader>

        <div className="space-y-2 py-2">
          {entries.map((entry) =>
            entry.eligible ? (
              <div key={entry.sub.id} className="flex items-center justify-between rounded-md border px-3 py-2 text-sm">
                <span className="font-medium">{entry.sub.service_name}</span>
                <span className="text-muted-foreground">
                  {entry.sub.billing_cycle ? CYCLE_LABELS[entry.sub.billing_cycle] ?? entry.sub.billing_cycle : ''}
                </span>
                <span className="text-muted-foreground">
                  {fmtDate(entry.sub.expiry_date)} → {fmtDate(entry.newExpiry)}
                </span>
              </div>
            ) : (
              <div key={entry.sub.id} className="flex items-center justify-between rounded-md border px-3 py-2 text-sm">
                <span className="font-medium">{entry.sub.service_name}</span>
                <span className="text-destructive">{entry.reason}</span>
              </div>
            ),
          )}
        </div>

        <p className="text-sm text-muted-foreground">
          將續訂 {eligibleCount} 筆，略過 {skippedCount} 筆
        </p>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={mutation.isPending}>
            取消
          </Button>
          <Button
            onClick={() => mutation.mutate()}
            disabled={eligibleIds.length === 0 || mutation.isPending}
          >
            {mutation.isPending ? '續訂中...' : '確認續訂'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
