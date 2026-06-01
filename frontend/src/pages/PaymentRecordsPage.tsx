import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listByFilters, deletePayment } from '@/api/payment_records'
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
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Pencil, Trash2 } from 'lucide-react'
import PaymentRecordFormDialog from '@/components/payments/PaymentRecordFormDialog'
import { useAuthStore } from '@/stores/authStore'
import { useToast } from '@/hooks/use-toast'
import type { PaymentRecord } from '@/types/api'

function pad(n: number) {
  return String(n).padStart(2, '0')
}

function localDateStr(d: Date): string {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function defaultRange() {
  const to = new Date()
  const from = new Date()
  from.setDate(from.getDate() - 30)
  return { from: localDateStr(from), to: localDateStr(to) }
}

export default function PaymentRecordsPage() {
  const def = defaultRange()
  const [fromDate, setFromDate] = useState(def.from)
  const [toDate, setToDate] = useState(def.to)
  const [serviceName, setServiceName] = useState('')
  const [queryParams, setQueryParams] = useState({
    from: def.from,
    to: def.to,
    service: '',
  })
  const [editing, setEditing] = useState<PaymentRecord | undefined>(undefined)
  const [formOpen, setFormOpen] = useState(false)
  const [deletingId, setDeletingId] = useState<number | null>(null)

  const { currentUser } = useAuthStore()
  const { toast } = useToast()
  const queryClient = useQueryClient()

  const canUpdate = currentUser?.can_update || currentUser?.role === 'admin'
  const canDelete = currentUser?.can_delete || currentUser?.role === 'admin'
  const hasActions = canUpdate || canDelete

  const { data, isLoading, isError } = useQuery({
    queryKey: ['payments', 'global', queryParams.from, queryParams.to, queryParams.service],
    queryFn: () =>
      listByFilters(queryParams.from, queryParams.to, queryParams.service || undefined),
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

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">付款紀錄</h2>

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
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="whitespace-nowrap">付款日期</TableHead>
              <TableHead className="whitespace-nowrap">訂閱名稱</TableHead>
              <TableHead className="whitespace-nowrap">金額</TableHead>
              <TableHead className="whitespace-nowrap">幣別</TableHead>
              <TableHead>備註</TableHead>
              {hasActions && <TableHead className="text-right">操作</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {records.length === 0 && (
              <TableRow>
                <TableCell
                  colSpan={hasActions ? 6 : 5}
                  className="py-8 text-center text-muted-foreground"
                >
                  此區間內沒有付款紀錄
                </TableCell>
              </TableRow>
            )}
            {records.map((r) => (
              <TableRow key={r.id}>
                <TableCell className="whitespace-nowrap text-sm">{r.payment_date}</TableCell>
                <TableCell className="text-sm">{r.service_name ?? '—'}</TableCell>
                <TableCell className="text-sm">{r.amount}</TableCell>
                <TableCell className="text-sm">{r.currency}</TableCell>
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
        </Table>
      )}

      <PaymentRecordFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        record={editing}
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
