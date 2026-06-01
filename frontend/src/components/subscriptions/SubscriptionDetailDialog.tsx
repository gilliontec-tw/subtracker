import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import PaymentRecordList from '@/components/payments/PaymentRecordList'
import { fmtDate } from '@/lib/utils'
import type { Subscription } from '@/types/api'

const BILLING_CYCLE_LABELS: Record<string, string> = {
  monthly: '每月',
  quarterly: '每季',
  semi_annual: '半年',
  annual: '每年',
  biennial: '兩年',
}

const STATUS_LABELS: Record<string, string> = {
  active: '啟用中',
  renewed: '已續約',
  cancelled: '已取消',
  suspended: '暫停',
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[120px_1fr] gap-2 border-b py-2 last:border-0">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-sm">{value ?? '—'}</span>
    </div>
  )
}

interface Props {
  subscription: Subscription | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export default function SubscriptionDetailDialog({ subscription: sub, open, onOpenChange }: Props) {
  if (!sub) return null

  const costStr = sub.cost
    ? `${sub.currency} ${sub.cost}${sub.exchange_rate ? ` (匯率 ${sub.exchange_rate})` : ''}`
    : null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] w-full max-w-4xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{sub.service_name}</DialogTitle>
        </DialogHeader>

        <div className="mt-2 flex flex-col gap-6 md:flex-row">
          {/* 左欄：訂閱資料 */}
          <div className="min-w-0 flex-1">
            <Row label="登入帳號" value={sub.login_account || null} />
            <Row
              label="狀態"
              value={
                <Badge
                  variant={sub.status === 'active' ? undefined : 'secondary'}
                  className={
                    sub.status === 'active'
                      ? 'border-transparent bg-green-100 text-green-800 hover:bg-green-100'
                      : ''
                  }
                >
                  {STATUS_LABELS[sub.status] ?? sub.status}
                </Badge>
              }
            />
            <Row label="到期日" value={fmtDate(sub.expiry_date)} />
            <Row label="計費週期" value={sub.billing_cycle ? BILLING_CYCLE_LABELS[sub.billing_cycle] : null} />
            <Row label="自動續費" value={sub.auto_renew ? '是' : '否'} />
            <Row label="試用到期日" value={fmtDate(sub.trial_end_date)} />
            <Row label="下次帳單日" value={fmtDate(sub.next_billing_date)} />
            <Row label="費用" value={costStr} />
            <Row label="付款帳號" value={sub.payment_account} />
            <Row label="負責人" value={sub.owner_name} />
            <Row label="部門" value={sub.department} />
            <Row label="分類" value={sub.category} />
            <Row
              label="通知信箱"
              value={sub.notification_emails.length > 0 ? sub.notification_emails.join(', ') : null}
            />
            <Row label="提前通知天數" value={`${sub.notification_days} 天`} />
            <Row label="備註" value={sub.notes} />
            <Row label="建立時間" value={fmtDate(sub.created_at)} />
            <Row label="最後更新" value={fmtDate(sub.updated_at)} />
          </div>

          {/* 右欄：付款紀錄（唯讀） */}
          <div className="border-t pt-4 md:w-72 md:shrink-0 md:border-l md:border-t-0 md:pl-6 md:pt-0">
            <PaymentRecordList subscriptionId={sub.id} readOnly />
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
