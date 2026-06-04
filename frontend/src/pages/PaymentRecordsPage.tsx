import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listByFilters, deletePayment } from '@/api/payment_records'
import { listSubscriptions } from '@/api/subscriptions'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Download, Pencil, Plus, Trash2 } from 'lucide-react'
import { fmtDate } from '@/lib/utils'
import PaymentRecordFormDialog from '@/components/payments/PaymentRecordFormDialog'
import { useAuthStore } from '@/stores/authStore'
import { useToast } from '@/hooks/use-toast'
import type { PaymentRecord } from '@/types/api'

function exportCSV(records: PaymentRecord[]) {
  const headers = ['付款日期', '訂閱名稱', '部門', '帳號', '幣別', '金額', '備註']
  const rows = records.map((r) => [
    r.payment_date,
    r.service_name ?? '',
    r.department ?? '',
    r.login_account ?? '',
    r.currency,
    r.amount,
    r.notes ?? '',
  ])
  const csv = [headers, ...rows]
    .map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(','))
    .join('\n')
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `付款記錄_${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

export default function PaymentRecordsPage() {
  const [fromDate, setFromDate] = useState('')
  const [toDate, setToDate] = useState('')
  const [serviceName, setServiceName] = useState('')
  const [queryParams, setQueryParams] = useState({
    from: '',
    to: '',
    service: '',
  })
  const [editing, setEditing] = useState<PaymentRecord | undefined>(undefined)
  const [formOpen, setFormOpen] = useState(false)
  const [deletingId, setDeletingId] = useState<number | null>(null)

  const { currentUser } = useAuthStore()
  const { toast } = useToast()
  const queryClient = useQueryClient()

  const canCreate = currentUser?.can_create || currentUser?.role === 'admin'
  const canUpdate = currentUser?.can_update || currentUser?.role === 'admin'
  const canDelete = currentUser?.can_delete || currentUser?.role === 'admin'
  const hasActions = canUpdate || canDelete

  const { data: subsData } = useQuery({
    queryKey: ['subscriptions', false],
    queryFn: () => listSubscriptions(false),
  })
  const activeSubscriptions = subsData?.items ?? []

  const { data, isLoading, isError } = useQuery({
    queryKey: ['payments', 'global', queryParams.from, queryParams.to, queryParams.service],
    queryFn: () =>
      listByFilters(
        queryParams.from || undefined,
        queryParams.to || undefined,
        queryParams.service || undefined,
      ),
  })

  const { mutate: doDelete, isPending: isDeleting } = useMutation({
    mutationFn: deletePayment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['payments'] })
      toast({ title: '付款紀錄已刪除' })
      setDeletingId(null)
    },
    onError: () => {
      toast({ title: '刪除失敗', variant: 'destructive' })
      setDeletingId(null)
    },
  })

  const records = data ?? []

  const subMap = new Map(activeSubscriptions.map((s) => [s.id, s]))
  let unconvertibleCount = 0
  const twdTotal = records.reduce((sum, p) => {
    const amount = parseFloat(p.amount)
    if (isNaN(amount)) return sum
    if (p.currency === 'TWD') return sum + amount
    const sub = subMap.get(p.subscription_id)
    if (!sub || !sub.exchange_rate) { unconvertibleCount++; return sum }
    const rate = parseFloat(sub.exchange_rate)
    if (isNaN(rate)) { unconvertibleCount++; return sum }
    return sum + amount * rate
  }, 0)

  const colSpan = hasActions ? 8 : 7

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">付款紀錄</h2>
        <div className="flex gap-2">
          {records.length > 0 && (
            <Button variant="outline" onClick={() => exportCSV(records)}>
              <Download className="mr-1 size-4" />
              匯出 CSV
            </Button>
          )}
          {canCreate && (
            <Button onClick={() => { setEditing(undefined); setFormOpen(true) }}>
              <Plus className="size-4" />
              新增付款
            </Button>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <input
          type="date"
          value={fromDate}
          max={toDate}
          onChange={(e) => setFromDate(e.target.value)}
          className="rounded-md border px-3 py-1.5 text-sm"
        />
        <span className="text-sm text-muted-foreground">至</span>
        <input
          type="date"
          value={toDate}
          min={fromDate}
          onChange={(e) => setToDate(e.target.value)}
          className="rounded-md border px-3 py-1.5 text-sm"
        />
        <Input
          placeholder="訂閱名稱"
          value={serviceName}
          onChange={(e) => setServiceName(e.target.value)}
          className="max-w-40"
        />
        <Button
          onClick={() =>
            setQueryParams({ from: fromDate, to: toDate, service: serviceName })
          }
        >
          查詢
        </Button>
      </div>

      {isLoading && <p className="text-muted-foreground">載入中...</p>}
      {isError && <p className="text-destructive">載入失敗，請重新整理頁面</p>}
      {!isLoading && !isError && (
        <div className="overflow-x-auto rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="whitespace-nowrap">付款日期</TableHead>
                <TableHead className="whitespace-nowrap">訂閱名稱</TableHead>
                <TableHead className="whitespace-nowrap">部門</TableHead>
                <TableHead className="whitespace-nowrap">帳號</TableHead>
                <TableHead className="whitespace-nowrap">幣別</TableHead>
                <TableHead className="whitespace-nowrap">金額</TableHead>
                <TableHead>備註</TableHead>
                {hasActions && <TableHead className="text-right">操作</TableHead>}
              </TableRow>
            </TableHeader>
            <TableBody>
              {records.length === 0 && (
                <TableRow>
                  <TableCell
                    colSpan={colSpan}
                    className="py-8 text-center text-muted-foreground"
                  >
                    此區間內沒有付款紀錄
                  </TableCell>
                </TableRow>
              )}
              {records.map((r) => (
                <TableRow key={r.id}>
                  <TableCell className="whitespace-nowrap text-sm">{fmtDate(r.payment_date)}</TableCell>
                  <TableCell className="text-sm">{r.service_name ?? '—'}</TableCell>
                  <TableCell className="text-sm">{r.department ?? '—'}</TableCell>
                  <TableCell className="text-sm">{r.login_account ?? '—'}</TableCell>
                  <TableCell className="text-sm">{r.currency}</TableCell>
                  <TableCell className="text-sm">{r.amount}</TableCell>
                  <TableCell className="text-sm">{r.notes ?? '—'}</TableCell>
                  {hasActions && (
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        {canUpdate && (
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => {
                              setEditing(r)
                              setFormOpen(true)
                            }}
                          >
                            <Pencil className="size-4" />
                          </Button>
                        )}
                        {canDelete && (
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setDeletingId(r.id)}
                          >
                            <Trash2 className="size-4 text-destructive" />
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  )}
                </TableRow>
              ))}
            </TableBody>
            {records.length > 0 && (
              <TableFooter>
                <TableRow>
                  <TableCell colSpan={colSpan} className="text-right tabular-nums">
                    <span className="mr-4 text-sm text-slate-500">{records.length} 筆</span>
                    <span className="font-semibold text-slate-900">
                      合計：NT$ {Math.round(twdTotal).toLocaleString('zh-TW')}
                    </span>
                    {unconvertibleCount > 0 && (
                      <span className="ml-2 text-xs text-slate-400">
                        （另有 {unconvertibleCount} 筆外幣無法換算）
                      </span>
                    )}
                  </TableCell>
                </TableRow>
              </TableFooter>
            )}
          </Table>
        </div>
      )}

      <PaymentRecordFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        record={editing}
        subscriptions={!editing ? activeSubscriptions : undefined}
      />

      <Dialog
        open={deletingId !== null}
        onOpenChange={(open) => {
          if (!open) setDeletingId(null)
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>確認刪除</DialogTitle>
            <DialogDescription>確定要刪除此付款紀錄嗎？此操作無法復原。</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeletingId(null)}
              disabled={isDeleting}
            >
              取消
            </Button>
            <Button
              variant="destructive"
              onClick={() => deletingId !== null && doDelete(deletingId)}
              disabled={isDeleting}
            >
              {isDeleting ? '刪除中...' : '確認刪除'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
