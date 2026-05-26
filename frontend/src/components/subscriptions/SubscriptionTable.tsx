import { useNavigate } from 'react-router-dom'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { AlertCircle, Pencil } from 'lucide-react'
import DeleteConfirmDialog from './DeleteConfirmDialog'
import type { Subscription } from '@/types/api'

function daysUntil(dateStr: string): number {
  const expiry = new Date(dateStr)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  expiry.setHours(0, 0, 0, 0)
  return Math.ceil((expiry.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
}

function ExpiryCell({ date }: { date: string }) {
  const days = daysUntil(date)
  if (days <= 30) {
    return (
      <span className="flex items-center gap-1 font-medium text-red-600">
        <AlertCircle className="size-4" />
        {date}
      </span>
    )
  }
  if (days <= 60) {
    return <span className="text-orange-500">{date}</span>
  }
  return <span>{date}</span>
}

function StatusBadge({ status }: { status: string }) {
  if (status === 'active') {
    return (
      <Badge className="border-transparent bg-green-100 text-green-800 hover:bg-green-100">
        啟用中
      </Badge>
    )
  }
  if (status === 'cancelled') {
    return <Badge variant="secondary">已取消</Badge>
  }
  return <Badge variant="secondary">{status}</Badge>
}

function formatCost(cost: string | null, currency: string): string {
  if (!cost) return '—'
  return `${currency} ${cost}`
}

interface Props {
  subscriptions: Subscription[]
}

export default function SubscriptionTable({ subscriptions }: Props) {
  const navigate = useNavigate()

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>服務名稱</TableHead>
          <TableHead>帳號</TableHead>
          <TableHead>部門</TableHead>
          <TableHead>負責人</TableHead>
          <TableHead>費用</TableHead>
          <TableHead>到期日</TableHead>
          <TableHead>狀態</TableHead>
          <TableHead className="text-right">操作</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {subscriptions.length === 0 && (
          <TableRow>
            <TableCell colSpan={8} className="py-8 text-center text-muted-foreground">
              沒有訂閱資料
            </TableCell>
          </TableRow>
        )}
        {subscriptions.map((sub) => (
          <TableRow key={sub.id}>
            <TableCell className="font-medium">{sub.service_name}</TableCell>
            <TableCell className="text-muted-foreground">{sub.login_account || '—'}</TableCell>
            <TableCell>{sub.department || '—'}</TableCell>
            <TableCell>{sub.owner_name || '—'}</TableCell>
            <TableCell>{formatCost(sub.cost, sub.currency)}</TableCell>
            <TableCell>
              <ExpiryCell date={sub.expiry_date} />
            </TableCell>
            <TableCell>
              <StatusBadge status={sub.status} />
            </TableCell>
            <TableCell className="text-right">
              <div className="flex justify-end gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => navigate(`/subscriptions/${sub.id}/edit`)}
                >
                  <Pencil className="size-4" />
                </Button>
                <DeleteConfirmDialog subscriptionId={sub.id} serviceName={sub.service_name} />
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
