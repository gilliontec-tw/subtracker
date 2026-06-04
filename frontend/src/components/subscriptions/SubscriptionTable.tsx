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
import { ChevronDown, ChevronUp, ChevronsUpDown, Pencil } from 'lucide-react'
import SubscriptionDetailDialog from './SubscriptionDetailDialog'
import BatchRenewDialog from './BatchRenewDialog'
import { useAuthStore } from '@/stores/authStore'
import type { Subscription } from '@/types/api'
import { fmtDate } from '@/lib/utils'

type SortKey = 'service_name' | 'login_account' | 'department' | 'owner_name' | 'cost' | 'billing_cycle' | 'expiry_date' | 'status'
type SortDir = 'asc' | 'desc'

function daysFromToday(dateStr: string): number {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const target = new Date(dateStr)
  target.setHours(0, 0, 0, 0)
  return Math.ceil((target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
}

function ExpiryCell({ dateStr }: { dateStr: string }) {
  const days = daysFromToday(dateStr)
  const formatted = fmtDate(dateStr)
  if (days < 0) return <span className="text-slate-400 line-through">{formatted}</span>
  if (days <= 14) return <span className="font-semibold text-red-600">{formatted}</span>
  if (days <= 30) return <span className="text-amber-600">{formatted}</span>
  return <span className="text-slate-500">{formatted}</span>
}

const BILLING_CYCLE_LABELS: Record<string, string> = {
  monthly: '月繳',
  quarterly: '季繳',
  semi_annual: '半年繳',
  annual: '年繳',
  biennial: '兩年繳',
}

const STATUS_TEXT: Record<string, { label: string; className: string }> = {
  active:    { label: '啟用中', className: 'font-medium text-emerald-600' },
  suspended: { label: '停用', className: 'text-slate-400' },
}

function StatusBadge({ status }: { status: string }) {
  const s = STATUS_TEXT[status]
  return (
    <span className={s?.className ?? 'text-slate-500'}>
      {s?.label ?? status}
    </span>
  )
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
    case 'billing_cycle': return sub.billing_cycle || ''
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
  const [sortKey, setSortKey] = useState<SortKey>('service_name')
  const [sortDir, setSortDir] = useState<SortDir>('asc')
  const [detailSub, setDetailSub] = useState<Subscription | null>(null)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [batchOpen, setBatchOpen] = useState(false)

  const canUpdate = (currentUser?.can_update || currentUser?.role === 'admin') ?? false
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

  // Derive active selection: only ids that still exist in the current subscriptions list.
  // This ensures stale selections are silently dropped when the subscriptions prop changes
  // (e.g. after a filter update), without needing an effect or ref.
  const currentIdSet = new Set(sorted.map((s) => s.id))
  const activeSelectedIds = new Set([...selectedIds].filter((id) => currentIdSet.has(id)))

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
      {activeSelectedIds.size > 0 && (
        <div className="mb-3 flex items-center justify-end">
          <Button onClick={() => setBatchOpen(true)}>
            續訂 ({activeSelectedIds.size})
          </Button>
        </div>
      )}

      <div className="overflow-x-auto rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-10" title="勾選後可批次執行續訂">
              <input
                type="checkbox"
                className="size-4 cursor-pointer"
                checked={activeSelectedIds.size === sorted.length && sorted.length > 0}
                ref={(el) => { if (el) el.indeterminate = activeSelectedIds.size > 0 && activeSelectedIds.size < sorted.length }}
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
            {th('計費週期', 'billing_cycle')}
            {th('到期日', 'expiry_date')}
            {th('狀態', 'status')}
            {hasActions && <TableHead className="w-12" />}
          </TableRow>
        </TableHeader>
        <TableBody>
          {sorted.length === 0 && (
            <TableRow>
              <TableCell colSpan={hasActions ? 10 : 9} className="py-8 text-center text-muted-foreground">
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
                  checked={activeSelectedIds.has(sub.id)}
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
              <TableCell className="text-slate-500">
                {sub.billing_cycle ? (BILLING_CYCLE_LABELS[sub.billing_cycle] ?? sub.billing_cycle) : '—'}
              </TableCell>
              <TableCell>
                <ExpiryCell dateStr={sub.expiry_date} />
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
      </div>

      <SubscriptionDetailDialog
        subscription={detailSub}
        open={detailSub !== null}
        onOpenChange={(open) => { if (!open) setDetailSub(null) }}
      />

      <BatchRenewDialog
        open={batchOpen}
        onOpenChange={setBatchOpen}
        subscriptions={sorted.filter(s => activeSelectedIds.has(s.id))}
        onSuccess={() => setSelectedIds(new Set())}
      />
    </>
  )
}
