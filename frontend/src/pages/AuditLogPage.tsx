import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listAuditLog } from '@/api/audit_log'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { AuditLogEntry } from '@/types/api'

const ACTION_LABELS: Record<string, string> = {
  create: '新增',
  update: '編輯',
  delete: '刪除',
}

function formatDateTime(iso: string): string {
  return iso.slice(0, 16).replace('T', ' ')
}

function defaultRange(): { from: string; to: string } {
  const to = new Date()
  const from = new Date()
  from.setDate(from.getDate() - 30)
  return {
    from: from.toISOString().slice(0, 10),
    to: to.toISOString().slice(0, 10),
  }
}

function ChangesCell({ entry }: { entry: AuditLogEntry }) {
  if (!entry.changes || entry.changes.length === 0) return <span>—</span>
  return (
    <div className="space-y-0.5">
      {entry.changes.map((c) => (
        <div key={c.field} className="text-xs">
          <span className="font-medium">{c.field}</span>: {c.before} → {c.after}
        </div>
      ))}
    </div>
  )
}

export default function AuditLogPage() {
  const def = defaultRange()
  const [fromDate, setFromDate] = useState(def.from)
  const [toDate, setToDate] = useState(def.to)
  const [queryParams, setQueryParams] = useState({ from: def.from, to: def.to })

  const { data, isLoading, isError } = useQuery({
    queryKey: ['audit-log', queryParams.from, queryParams.to],
    queryFn: () => listAuditLog(queryParams.from, queryParams.to),
  })

  const entries = data ?? []

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">稽核日誌</h2>

      <div className="flex items-center gap-3">
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
        <Button onClick={() => setQueryParams({ from: fromDate, to: toDate })}>
          查詢
        </Button>
      </div>

      {isLoading && <p className="text-muted-foreground">載入中...</p>}
      {isError && <p className="text-destructive">載入失敗，請重新整理頁面</p>}
      {!isLoading && !isError && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="whitespace-nowrap">時間</TableHead>
              <TableHead className="whitespace-nowrap">操作者</TableHead>
              <TableHead className="whitespace-nowrap">動作</TableHead>
              <TableHead className="whitespace-nowrap">訂閱名稱</TableHead>
              <TableHead>變更詳情</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {entries.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="py-8 text-center text-muted-foreground">
                  此區間內沒有操作記錄
                </TableCell>
              </TableRow>
            )}
            {entries.map((entry) => (
              <TableRow key={entry.id}>
                <TableCell className="whitespace-nowrap text-sm">
                  {formatDateTime(entry.created_at)}
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {entry.user_email ?? '—'}
                </TableCell>
                <TableCell className="text-sm">
                  {ACTION_LABELS[entry.action] ?? entry.action}
                </TableCell>
                <TableCell className="text-sm">{entry.service_name ?? '—'}</TableCell>
                <TableCell>
                  <ChangesCell entry={entry} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  )
}
