import { useState } from 'react'
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
import { AlertCircle, ChevronDown, ChevronUp, ChevronsUpDown, Pencil } from 'lucide-react'
import SubscriptionDetailDialog from './SubscriptionDetailDialog'
import BatchRenewDialog from './BatchRenewDialog'
import { useAuthStore } from '@/stores/authStore'
import { fmtDate } from '@/lib/utils'
import type { Subscription } from '@/types/api'

type SortKey = 'service_name' | 'login_account' | 'department' | 'owner_name' | 'cost' | 'expiry_date' | 'status'
type SortDir = 'asc' | 'desc'

function daysUntil(dateStr: string): number {
  const expiry = new Date(dateStr)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  expiry.setHours(0, 0, 0, 0)
  return Math.ceil((expiry.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
}

function ExpiryCell({ date, notificationDays }: { date: string; notificationDays: number }) {
  const days = daysUntil(date)
  const display = fmtDate(date)
  if (days <= notificationDays) {
    return (
      <span className="flex items-center gap-1 font-medium text-red-600">
        <AlertCircle className="size-4" />
        {display}
      </span>
    )
  }
  if (days <= notificationDays * 2) {
    return <span className="text-orange-500">{display}</span>
  }
  return <span>{display}</span>
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

function sortValue(sub: Subscription, key: SortKey): string | number {
  switch (key) {
    case 'service_name': return sub.service_name
    case 'login_account': return sub.login_account || ''
    case 'department': return sub.department || ''
    case 'owner_name': return sub.owner_name || ''
    case 'cost': return parseFloat(sub.cost || '0')
    case 'expiry_date': return sub.expiry_date
    case 'status': return sub.status
  }
}

function sortSubscriptions(items: Subscription[], key: SortKey, dir: SortDir): Subscription[] {
  return [...items].sort((a, b) => {
    const av = sortValue(a, key)
    const bv = sortValue(b, key)
    if (typeof av === 'number' && typeof bv === 'number') {
      return dir === 'asc' ? av - bv : bv - av
    }
    const cmp = String(av).localeCompare(String(bv), 'zh-TW')
    return dir === 'asc' ? cmp : -cmp
  })
}

function SortIcon({ col, sortKey, sortDir }: { col: SortKey; sortKey: SortKey; sortDir: SortDir }) {
  if (col !== sortKey) return <ChevronsUpDown className="ml-1 inline size-3.5 text-muted-foreground/50" />
  return sortDir === 'asc'
    ? <ChevronUp className="ml-1 inline size-3.5" />
    : <ChevronDown className="ml-1 inline size-3.5" />
}

interface Props {
  subscriptions: Subscription[]
}

export default function SubscriptionTable({ subscriptions }: Props) {
  const navigate = useNavigate()
  const { currentUser } = useAuthStore()
  const [sortKey, setSortKey] = useState<SortKey>('expiry_date')
  const [sortDir, setSortDir] = useState<SortDir>('asc')
  const [detailSub, setDetailSub] = useState<Subscription | null>(null)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [batchOpen, setBatchOpen] = useState(false)

  const canUpdate = currentUser?.can_update ?? false
  const hasActions = canUpdate

  function handleSort(col: SortKey) {
    if (col === sortKey) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(col)
      setSortDir('asc')
    }
  }

  const sorted = sortSubscriptions(subscriptions, sortKey, sortDir)

  function th(label: string, col: SortKey) {
    return (
      <TableHead
        className="cursor-pointer select-none whitespace-nowrap hover:text-foreground"
        onClick={() => handleSort(col)}
      >
        {label}
        <SortIcon col={col} sortKey={sortKey} sortDir={sortDir} />
      </TableHead>
    )
  }

  return (
    <>
      {selectedIds.size > 0 && (
        <div className="mb-3 flex items-center justify-end">
          <Button onClick={() => setBatchOpen(true)}>
            續訂 ({selectedIds.size})
          </Button>
        </div>
      )}

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-10">
              <input
                type="checkbox"
                className="size-4"
                checked={selectedIds.size === sorted.length && sorted.length > 0}
                ref={(el) => { if (el) el.indeterminate = selectedIds.size > 0 && selectedIds.size < sorted.length }}
                onChange={(e) => {
                  setSelectedIds(e.target.checked ? new Set(sorted.map(s => s.id)) : new Set())
                }}
              />
            </TableHead>
            {th('服務名稱', 'service_name')}
            {th('帳號', 'login_account')}
            {th('部門', 'department')}
            {th('負責人', 'owner_name')}
            {th('費用', 'cost')}
            {th('到期日', 'expiry_date')}
            {th('狀態', 'status')}
            {hasActions && <TableHead className="w-12" />}
          </TableRow>
        </TableHeader>
        <TableBody>
          {sorted.length === 0 && (
            <TableRow>
              <TableCell colSpan={hasActions ? 9 : 8} className="py-8 text-center text-muted-foreground">
                沒有訂閱資料
              </TableCell>
            </TableRow>
          )}
          {sorted.map((sub) => (
            <TableRow
              key={sub.id}
              className="cursor-pointer"
              onClick={() => setDetailSub(sub)}
            >
              <TableCell className="w-10" onClick={(e) => e.stopPropagation()}>
                <input
                  type="checkbox"
                  className="size-4"
                  checked={selectedIds.has(sub.id)}
                  onChange={(e) => {
                    setSelectedIds(prev => {
                      const next = new Set(prev)
                      if (e.target.checked) { next.add(sub.id) } else { next.delete(sub.id) }
                      return next
                    })
                  }}
                />
              </TableCell>
              <TableCell className="font-medium">{sub.service_name}</TableCell>
              <TableCell className="text-muted-foreground">{sub.login_account || '—'}</TableCell>
              <TableCell>{sub.department || '—'}</TableCell>
              <TableCell>{sub.owner_name || '—'}</TableCell>
              <TableCell>{formatCost(sub.cost, sub.currency)}</TableCell>
              <TableCell>
                <ExpiryCell date={sub.expiry_date} notificationDays={sub.notification_days} />
              </TableCell>
              <TableCell>
                <StatusBadge status={sub.status} />
              </TableCell>
              {hasActions && (
                <TableCell className="text-right" onClick={(e) => e.stopPropagation()}>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => navigate(`/subscriptions/${sub.id}/edit`)}
                  >
                    <Pencil className="size-4" />
                  </Button>
                </TableCell>
              )}
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <SubscriptionDetailDialog
        subscription={detailSub}
        open={detailSub !== null}
        onOpenChange={(open) => { if (!open) setDetailSub(null) }}
      />

      <BatchRenewDialog
        open={batchOpen}
        onOpenChange={setBatchOpen}
        subscriptions={sorted.filter(s => selectedIds.has(s.id))}
        onSuccess={() => setSelectedIds(new Set())}
      />
    </>
  )
}
