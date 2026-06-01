import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listBySubscription, deletePayment } from '@/api/payment_records'
import { Button } from '@/components/ui/button'
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
import { Pencil, Trash2, Plus } from 'lucide-react'
import PaymentRecordFormDialog from './PaymentRecordFormDialog'
import { useAuthStore } from '@/stores/authStore'
import { useToast } from '@/hooks/use-toast'
import { fmtDate } from '@/lib/utils'
import type { PaymentRecord } from '@/types/api'

interface Props {
  subscriptionId: number
  readOnly?: boolean
}

export default function PaymentRecordList({ subscriptionId, readOnly = false }: Props) {
  const { currentUser } = useAuthStore()
  const { toast } = useToast()
  const queryClient = useQueryClient()
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<PaymentRecord | undefined>(undefined)
  const [deletingId, setDeletingId] = useState<number | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['payments', 'subscription', subscriptionId],
    queryFn: () => listBySubscription(subscriptionId),
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
  const canCreate = !readOnly && (currentUser?.can_create || currentUser?.role === 'admin')
  const canUpdate = !readOnly && (currentUser?.can_update || currentUser?.role === 'admin')
  const canDelete = !readOnly && (currentUser?.can_delete || currentUser?.role === 'admin')
  const hasActions = canUpdate || canDelete

  return (
    <div className="mt-4 border-t pt-4">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-sm font-medium">付款紀錄</span>
        {canCreate && (
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => {
              setEditing(undefined)
              setFormOpen(true)
            }}
          >
            <Plus className="mr-1 size-3" />
            新增付款
          </Button>
        )}
      </div>

      {isLoading && <p className="text-xs text-muted-foreground">載入中...</p>}
      {!isLoading && records.length === 0 && (
        <p className="py-2 text-xs text-muted-foreground">尚無付款紀錄</p>
      )}
      {!isLoading && records.length > 0 && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="text-xs">付款日期</TableHead>
              <TableHead className="text-xs">金額</TableHead>
              <TableHead className="text-xs">幣別</TableHead>
              <TableHead className="text-xs">備註</TableHead>
              {hasActions && <TableHead className="text-right text-xs">操作</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {records.map((r) => (
              <TableRow key={r.id}>
                <TableCell className="text-xs">{fmtDate(r.payment_date)}</TableCell>
                <TableCell className="text-xs">{r.amount}</TableCell>
                <TableCell className="text-xs">{r.currency}</TableCell>
                <TableCell className="text-xs">{r.notes ?? '—'}</TableCell>
                {hasActions && (
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      {canUpdate && (
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="size-6"
                          onClick={() => {
                            setEditing(r)
                            setFormOpen(true)
                          }}
                        >
                          <Pencil className="size-3" />
                        </Button>
                      )}
                      {canDelete && (
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="size-6"
                          onClick={() => setDeletingId(r.id)}
                        >
                          <Trash2 className="size-3 text-destructive" />
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
        subscriptionId={subscriptionId}
        record={editing}
      />

      <Dialog open={deletingId !== null} onOpenChange={(open) => { if (!open) setDeletingId(null) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>確認刪除</DialogTitle>
            <DialogDescription>確定要刪除此付款紀錄嗎？此操作無法復原。</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setDeletingId(null)} disabled={isDeleting}>
              取消
            </Button>
            <Button
              type="button"
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
