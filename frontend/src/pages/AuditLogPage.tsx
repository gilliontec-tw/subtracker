/**
 * pages/AuditLogPage.tsx — 稽核日誌頁面
 *
 * 顯示指定日期範圍內的訂閱操作記錄（新增、編輯、刪除）。
 * 預設顯示最近 30 天。日期選擇後需點擊「查詢」才觸發 API，
 * 避免每次改日期就發送請求。
 *
 * 功能說明：
 *  - 編輯操作顯示各欄位的 before → after 變更詳情
 *  - 未刪除的訂閱名稱可點擊跳轉到編輯頁
 *  - 刪除的訂閱只顯示名稱，不可點擊（資料已不存在）
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
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

function pad(n: number) {
  return String(n).padStart(2, '0')
}

function formatDateTime(iso: string): string {
  const d = new Date(iso)
  return `${d.getFullYear()}/${pad(d.getMonth() + 1)}/${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function localDateStr(d: Date): string {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function defaultRange(): { from: string; to: string } {
  const to = new Date()
  const from = new Date()
  from.setDate(from.getDate() - 30)
  return { from: localDateStr(from), to: localDateStr(to) }
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
  const navigate = useNavigate()
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
        <Button onClick={() => setQueryParams({ from: fromDate, to: toDate })}>
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
              <TableHead className="whitespace-nowrap">時間</TableHead>
              <TableHead className="whitespace-nowrap">操作者</TableHead>
              <TableHead className="whitespace-nowrap">動作</TableHead>
              <TableHead className="whitespace-nowrap">訂閱</TableHead>
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
                <TableCell className="text-sm">
                  {entry.action !== 'delete' && entry.resource_id ? (
                    <button
                      className="text-left underline-offset-2 hover:underline"
                      onClick={() => navigate(`/subscriptions/${entry.resource_id}/edit`)}
                    >
                      {entry.service_name ?? '—'}
                    </button>
                  ) : (
                    <span className="text-muted-foreground">{entry.service_name ?? '—'}</span>
                  )}
                </TableCell>
                <TableCell>
                  <ChangesCell entry={entry} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        </div>
      )}
    </div>
  )
}
