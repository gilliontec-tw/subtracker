import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  PieChart, Pie, Cell, Tooltip, Legend,
  LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer,
} from 'recharts'
import { listSubscriptions } from '@/api/subscriptions'
import { listByFilters } from '@/api/payment_records'
import { computeStats, monthlyEquivalentTWD } from '@/lib/dashboardStats'
import type { DashboardStats, Breakdown } from '@/lib/dashboardStats'
import { Button } from '@/components/ui/button'
import type { Subscription, PaymentRecord } from '@/types/api'
import { fmtDate } from '@/lib/utils'

const PIE_COLORS = [
  '#e74c3c', '#e67e22', '#f1c40f', '#2ecc71',
  '#1abc9c', '#3498db', '#9b59b6', '#e91e63',
  '#00bcd4', '#ff5722',
]

const BRAND_BLUE = '#00a8e8'

function formatTWD(n: number): string {
  return `NT$ ${Math.round(n).toLocaleString('zh-TW')}`
}

// ── Section title ─────────────────────────────────────────────
function SectionTitle({ label, hint }: { label: string; hint?: string }) {
  return (
    <div className="mb-4 flex items-center gap-3">
      <span className="text-xs font-semibold uppercase tracking-widest text-slate-400">{label}</span>
      {hint && <span className="text-xs text-slate-500">{hint}</span>}
      <div className="h-px flex-1 bg-slate-200" />
    </div>
  )
}

// ── Stat card ─────────────────────────────────────────────────
function StatCard({ title, value, sub }: { title: string; value: string; sub?: string }) {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="h-1 w-full bg-[#00a8e8]" />
      <div className="p-5">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">{title}</p>
        <p className="mt-3 text-2xl font-bold tabular-nums text-slate-900">{value}</p>
        {sub && <p className="mt-1 text-xs text-slate-400">{sub}</p>}
      </div>
    </div>
  )
}

// ── Expiring table ────────────────────────────────────────────
function ExpiringTable({
  items,
  onRowClick,
}: {
  items: DashboardStats['expiringSubscriptions']
  onRowClick: (serviceName: string) => void
}) {
  if (items.length === 0) {
    return <p className="text-sm text-muted-foreground">目前沒有即將到期的訂閱</p>
  }

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-slate-50">
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-400">服務名稱</th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-400">帳號</th>
            <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-slate-400">費用</th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-400">到期日</th>
            <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-slate-400">剩餘天數</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const urgent = item.daysLeft < 14
            return (
              <tr
                key={item.id}
                className="cursor-pointer border-b last:border-0 hover:bg-slate-100/70"
                onClick={() => onRowClick(item.service_name)}
              >
                <td className="px-4 py-3 font-medium text-slate-900">{item.service_name}</td>
                <td className="px-4 py-3 text-slate-600">{item.login_account}</td>
                <td className="px-4 py-3 text-right tabular-nums text-slate-700">
                  {item.cost ? formatTWD(item.costTWD) : '—'}
                </td>
                <td className="px-4 py-3 text-slate-600">{fmtDate(item.expiry_date)}</td>
                <td className="px-4 py-3 text-center">
                  {urgent ? (
                    <span className="text-sm font-semibold text-red-600">{item.daysLeft} 天</span>
                  ) : (
                    <span className="text-sm text-slate-500">{item.daysLeft} 天</span>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ── Breakdown detail (pie click) ──────────────────────────────
const CYCLE_LABEL: Record<string, string> = {
  monthly: '月繳', quarterly: '季繳', semi_annual: '半年繳', annual: '年繳', biennial: '兩年繳',
}
interface BreakdownRow { groupKey: string; sub: Subscription }

function BreakdownTable({
  rows,
  variant,
}: {
  rows: BreakdownRow[]
  variant: 'department' | 'service'
}) {
  const col1 = variant === 'department'
    ? { header: '部門', get: (r: BreakdownRow) => r.groupKey }
    : { header: '服務名稱', get: (r: BreakdownRow) => r.sub.service_name }
  const col2 = variant === 'department'
    ? { header: '服務名稱', get: (r: BreakdownRow) => r.sub.service_name }
    : { header: '部門', get: (r: BreakdownRow) => r.sub.department ?? '—' }

  return (
    <div className="mt-3 overflow-hidden rounded-lg border border-slate-200">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-slate-50">
            <th className="px-4 py-2 text-left text-xs font-medium text-slate-400">{col1.header}</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-slate-400">{col2.header}</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-slate-400">帳單週期</th>
            <th className="px-4 py-2 text-right text-xs font-medium text-slate-400">月均費用</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ groupKey, sub }) => (
            <tr key={sub.id} className="border-b last:border-0 hover:bg-slate-50/60">
              <td className="px-4 py-2 text-sm text-slate-600">{col1.get({ groupKey, sub })}</td>
              <td className="px-4 py-2 text-slate-800">{col2.get({ groupKey, sub })}</td>
              <td className="px-4 py-2 text-slate-600">
                {sub.billing_cycle ? (CYCLE_LABEL[sub.billing_cycle] ?? sub.billing_cycle) : '—'}
              </td>
              <td className="px-4 py-2 text-right tabular-nums text-slate-700">{formatTWD(monthlyEquivalentTWD(sub))}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Pie breakdown ─────────────────────────────────────────────
function PieBreakdown({ title, breakdown, variant }: { title: string; breakdown: Breakdown; variant: 'department' | 'service' }) {
  const [selected, setSelected] = useState<string | null>(null)

  const data = Object.entries(breakdown)
    .map(([name, entry]) => ({ name, cost: Math.round(entry.cost) }))
    .sort((a, b) => b.cost - a.cost)

  if (data.length === 0) {
    return (
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">{title}</p>
        <p className="text-sm text-slate-400">無資料</p>
      </div>
    )
  }

  const handleClick = (entry: { name: string }) => {
    setSelected((prev) => (prev === entry.name ? null : entry.name))
  }

  const visibleGroups = selected ? [[selected, breakdown[selected]] as const] : Object.entries(breakdown)
  const rows: BreakdownRow[] = visibleGroups.flatMap(([key, entry]) =>
    entry.subscriptions.map((sub) => ({ groupKey: key, sub })),
  )

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="px-5 pt-5">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">{title}</p>
        {selected && (
          <p className="mt-1 text-xs text-slate-500">篩選：{selected}</p>
        )}
      </div>
      <div className="px-5 pb-2">
        <ResponsiveContainer width="100%" height={240}>
          <PieChart>
            <Pie
              data={data}
              dataKey="cost"
              nameKey="name"
              cx="50%"
              cy="50%"
              outerRadius={85}
              onClick={handleClick}
              className="cursor-pointer"
            >
              {data.map((entry, i) => (
                <Cell
                  key={entry.name}
                  fill={PIE_COLORS[i % PIE_COLORS.length]}
                  opacity={selected && selected !== entry.name ? 0.4 : 1}
                  stroke={selected === entry.name ? '#1e293b' : 'none'}
                  strokeWidth={selected === entry.name ? 2 : 0}
                />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: number, name: string) => [formatTWD(value), name]}
              contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e2e8f0' }}
            />
            <Legend
              formatter={(value) => <span style={{ fontSize: 12, color: '#64748b' }}>{value}</span>}
            />
          </PieChart>
        </ResponsiveContainer>
        <BreakdownTable rows={rows} variant={variant} />
      </div>
      <div className="pb-3" />
    </div>
  )
}

// ── Trend chart ───────────────────────────────────────────────
function TrendChart({
  payments,
  subs,
  fromDate,
  toDate,
}: {
  payments: PaymentRecord[]
  subs: Subscription[]
  fromDate: string
  toDate: string
}) {
  const data = computeTrend(payments, subs, fromDate, toDate)
  const hasData = data.some((d) => d.cost > 0)

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="px-5 pt-5">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">每月支出走勢</p>
        <p className="mt-0.5 text-xs text-slate-500">實際付款紀錄（最多 36 個月）</p>
      </div>
      <div className="px-5 pb-5 pt-3">
        {!hasData ? (
          <p className="py-6 text-center text-sm text-slate-400">尚無付款紀錄可計算趨勢</p>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={data} margin={{ top: 5, right: 16, left: 8, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="month" tick={{ fontSize: 12, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
              <YAxis
                tick={{ fontSize: 12, fill: '#94a3b8' }}
                tickFormatter={(v: number) => `NT$${(v / 1000).toFixed(0)}k`}
                width={60}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                formatter={(value: number) => [formatTWD(value), '實際支出']}
                contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e2e8f0' }}
              />
              <Line
                type="monotone"
                dataKey="cost"
                stroke={BRAND_BLUE}
                strokeWidth={2}
                dot={{ r: 3, fill: BRAND_BLUE, strokeWidth: 0 }}
                activeDot={{ r: 5, fill: BRAND_BLUE, strokeWidth: 0 }}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}

// ── Trend helpers ─────────────────────────────────────────────
function pad2(n: number) { return String(n).padStart(2, '0') }

function initTrendFrom(): string {
  const d = new Date()
  d.setMonth(d.getMonth() - 11)
  d.setDate(1)
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-01`
}

function initTrendTo(): string {
  const d = new Date()
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`
}

function computeTrend(
  payments: PaymentRecord[],
  subs: Subscription[],
  fromDate: string,
  toDate: string,
): { month: string; cost: number }[] {
  const subMap = new Map(subs.map((s) => [s.id, s]))
  const from = new Date(fromDate)
  const to = new Date(toDate)
  const monthlyAmounts: Record<string, number> = {}

  for (const p of payments) {
    const d = new Date(p.payment_date)
    if (d < from || d > to) continue
    const key = `${d.getFullYear()}-${pad2(d.getMonth() + 1)}`
    const amount = parseFloat(p.amount)
    if (isNaN(amount)) continue
    let amountTWD: number
    if (p.currency === 'TWD') {
      amountTWD = amount
    } else {
      const sub = subMap.get(p.subscription_id)
      if (!sub || !sub.exchange_rate) continue
      const rate = parseFloat(sub.exchange_rate)
      if (isNaN(rate)) continue
      amountTWD = amount * rate
    }
    monthlyAmounts[key] = (monthlyAmounts[key] ?? 0) + amountTWD
  }

  const result: { month: string; cost: number }[] = []
  const today = new Date()
  const cursor = new Date(from.getFullYear(), from.getMonth(), 1)
  const toMonth = new Date(to.getFullYear(), to.getMonth(), 1)

  while (cursor <= toMonth && result.length < 36) {
    const key = `${cursor.getFullYear()}-${pad2(cursor.getMonth() + 1)}`
    const yearPrefix = cursor.getFullYear() !== today.getFullYear() ? `${cursor.getFullYear()}/` : ''
    result.push({ month: `${yearPrefix}${cursor.getMonth() + 1}月`, cost: monthlyAmounts[key] ?? 0 })
    cursor.setMonth(cursor.getMonth() + 1)
  }

  return result
}

// ── Page ──────────────────────────────────────────────────────
export default function DashboardPage() {
  const navigate = useNavigate()
  const [trendFrom, setTrendFrom] = useState(initTrendFrom)
  const [trendTo, setTrendTo] = useState(initTrendTo)
  const [appliedFrom, setAppliedFrom] = useState(initTrendFrom)
  const [appliedTo, setAppliedTo] = useState(initTrendTo)
  const { data: subsData, isLoading, isError: subsError } = useQuery({
    queryKey: ['subscriptions', false],
    queryFn: () => listSubscriptions(),
  })

  const { data: payments, isError: paymentsError } = useQuery({
    queryKey: ['payments'],
    queryFn: () => listByFilters(),
  })

  const isError = subsError || paymentsError
  const stats = computeStats(subsData?.items ?? [], payments ?? [])

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-slate-900">總覽</h1>

      {isLoading && <p className="text-sm text-slate-400">載入中...</p>}
      {isError && <p className="text-sm text-destructive">載入失敗，請重新整理頁面</p>}

      {!isLoading && !isError && (
        <>
          {/* 統計卡片 */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <StatCard title="訂閱總數" value={`${stats.activeCount} 個`} />
            <StatCard title="即將到期" value={`${stats.expiringCount} 個`} sub="30 天內" />
            <StatCard
              title="每月費用"
              value={formatTWD(stats.monthlyBurnRate)}
              sub="所有訂閱折算月均總和"
            />
            <StatCard
              title="歷史付款總計"
              value={formatTWD(stats.historicalTotal)}
              sub={
                stats.unconvertiblePaymentCount > 0
                  ? `有 ${stats.unconvertiblePaymentCount} 筆外幣無法換算`
                  : '以各訂閱目前匯率換算'
              }
            />
          </div>

          {/* 費用分析 */}
          <div>
            <SectionTitle label="費用分析" hint="月均攤銷" />
            <div className="grid gap-4 lg:grid-cols-2">
              <PieBreakdown title="部門" breakdown={stats.departmentBreakdown} variant="department" />
              <PieBreakdown title="服務名稱" breakdown={stats.serviceBreakdown} variant="service" />
            </div>
          </div>

          {/* 趨勢 */}
          <div>
            <SectionTitle label="支出趨勢" />
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <input
                type="date"
                value={trendFrom}
                max={trendTo}
                onChange={(e) => setTrendFrom(e.target.value)}
                className="rounded-md border px-3 py-1.5 text-sm"
              />
              <span className="text-sm text-slate-400">至</span>
              <input
                type="date"
                value={trendTo}
                min={trendFrom}
                onChange={(e) => setTrendTo(e.target.value)}
                className="rounded-md border px-3 py-1.5 text-sm"
              />
              <Button
                size="sm"
                variant="outline"
                onClick={() => { setAppliedFrom(trendFrom); setAppliedTo(trendTo) }}
              >
                套用
              </Button>
            </div>
            <TrendChart
              payments={payments ?? []}
              subs={subsData?.items ?? []}
              fromDate={appliedFrom}
              toDate={appliedTo}
            />
          </div>

          {/* 即將到期 */}
          <div>
            <SectionTitle label="即將到期" hint="30 天內，紅字 < 14 天" />
            <ExpiringTable
              items={stats.expiringSubscriptions}
              onRowClick={(name) => navigate('/subscriptions', { state: { search: name } })}
            />
          </div>
        </>
      )}
    </div>
  )
}
