/**
 * pages/SubscriptionsPage.tsx — 項目管理頁面
 *
 * 顯示所有訂閱列表，支援搜尋、類型篩選、顯示停用項目，以及匯出 CSV。
 *
 * 搜尋篩選在前端完成（client-side filtering），不需額外的 API 請求。
 * 搜尋欄位：服務名稱、登入帳號、部門、負責人。
 *
 * 從 Dashboard 到期預警表格點擊跳轉時，會透過 React Router location.state
 * 帶入 search 關鍵字，自動填入搜尋框並聚焦。
 *
 * CSV 匯出：在前端組裝，檔名含日期，BOM 字元確保 Excel 正確識別 UTF-8。
 */
import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { listSubscriptions } from '@/api/subscriptions'
import { listAssetTypes } from '@/api/asset_types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import SubscriptionTable from '@/components/subscriptions/SubscriptionTable'
import { Download, Plus } from 'lucide-react'
import type { Subscription } from '@/types/api'

/** CSV 標頭對應的計費週期中文名稱 */
const CYCLE_LABELS_CSV: Record<string, string> = {
  monthly: '月繳', quarterly: '季繳', semi_annual: '半年繳', annual: '年繳', biennial: '兩年繳',
}
/** CSV 標頭對應的狀態中文名稱 */
const STATUS_LABELS_CSV: Record<string, string> = {
  active: '啟用中', suspended: '停用',
}

/**
 * 將目前篩選後的訂閱清單下載為 CSV 檔。
 * 欄位值包含逗號或引號時自動跳脫。
 * 開頭加 BOM（U+FEFF）讓 Excel 自動識別 UTF-8 編碼，避免中文亂碼。
 */
function downloadCSV(items: Subscription[]) {
  const headers = ['服務名稱', '類型', '登入帳號', '部門', '負責人', '費用', '幣別', '計費週期', '到期日', '狀態']
  const rows = items.map((s) => [
    s.service_name,
    s.asset_type_name ?? '',
    s.login_account ?? '',
    s.department ?? '',
    s.owner_name ?? '',
    s.cost ?? '',
    s.currency,
    s.billing_cycle ? (CYCLE_LABELS_CSV[s.billing_cycle] ?? s.billing_cycle) : '',
    s.expiry_date,
    STATUS_LABELS_CSV[s.status] ?? s.status,
  ])
  const csv = [headers, ...rows]
    .map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(','))
    .join('\n')
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  const d = new Date()
  a.href = url
  a.download = `subscriptions-${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}.csv`
  a.style.display = 'none'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export default function SubscriptionsPage() {
  const navigate = useNavigate()
  const location = useLocation()
  // 從 Dashboard 跳轉時帶入的搜尋關鍵字，預設空字串
  const [search, setSearch] = useState<string>((location.state as { search?: string } | null)?.search ?? '')
  const [showSuspended, setShowSuspended] = useState(false)
  // __all__ 為全部類型的 sentinel 值（shadcn Select 不允許空字串作為值）
  const [selectedTypeId, setSelectedTypeId] = useState<string>('__all__')

  const { data, isLoading, isError } = useQuery({
    queryKey: ['subscriptions', showSuspended],
    queryFn: () => listSubscriptions(showSuspended),
  })

  const { data: assetTypes = [] } = useQuery({
    queryKey: ['asset-types'],
    queryFn: listAssetTypes,
  })

  const subscriptions = data?.items ?? []
  const q = search.toLowerCase()

  /** 同時套用搜尋文字與類型篩選 */
  const filtered = subscriptions.filter((s) => {
    const matchesSearch =
      s.service_name.toLowerCase().includes(q) ||
      (s.login_account ?? '').toLowerCase().includes(q) ||
      (s.department ?? '').toLowerCase().includes(q) ||
      (s.owner_name ?? '').toLowerCase().includes(q)
    const matchesType = selectedTypeId === '__all__'
      ? true
      : selectedTypeId === '__none__'
        ? s.asset_type_id == null
        : s.asset_type_id === parseInt(selectedTypeId)
    return matchesSearch && matchesType
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">項目管理</h2>
        <div className="flex items-center gap-2">
          {/* 匯出的是目前篩選後的資料，非全部 */}
          <Button variant="outline" onClick={() => downloadCSV(filtered)} disabled={filtered.length === 0}>
            <Download className="size-4" />
            匯出 CSV
          </Button>
          <Button onClick={() => navigate('/subscriptions/new')}>
            <Plus className="size-4" />
            新增項目
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-4">
        <Input
          placeholder="搜尋名稱、帳號、部門、負責人..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-sm"
        />
        <Select value={selectedTypeId} onValueChange={setSelectedTypeId}>
          <SelectTrigger className="w-36">
            <SelectValue placeholder="全部類型" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__all__">全部類型</SelectItem>
            <SelectItem value="__none__">未分類</SelectItem>
            {assetTypes.map((t) => (
              <SelectItem key={t.id} value={String(t.id)}>{t.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <label className="flex cursor-pointer items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={showSuspended}
            onChange={(e) => setShowSuspended(e.target.checked)}
            className="size-4"
          />
          顯示已停用
        </label>
        <span className="text-xs text-muted-foreground">勾選列可批次續訂</span>
      </div>

      {isLoading && <p className="text-muted-foreground">載入中...</p>}
      {isError && <p className="text-destructive">載入失敗，請重新整理頁面</p>}
      {!isLoading && !isError && <SubscriptionTable subscriptions={filtered} />}
    </div>
  )
}
