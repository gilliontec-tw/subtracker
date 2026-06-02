import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { listSubscriptions } from '@/api/subscriptions'
import { listByFilters } from '@/api/payment_records'
import { computeStats } from '@/lib/dashboardStats'
import type { DashboardStats } from '@/lib/dashboardStats'
import { fmtDate } from '@/lib/utils'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

function StatCard({ title, value }: { title: string; value: string }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-xl font-bold">{value}</p>
      </CardContent>
    </Card>
  )
}

function formatTWD(n: number): string {
  return `NT$ ${Math.round(n).toLocaleString('zh-TW')}`
}

function ExpiringTable({ items }: { items: DashboardStats['expiringSubscriptions'] }) {
  const navigate = useNavigate()

  if (items.length === 0) {
    return <p className="text-sm text-muted-foreground">目前沒有即將到期的訂閱</p>
  }

  return (
    <div className="rounded-md border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/50">
            <th className="px-4 py-3 text-left font-medium">服務名稱</th>
            <th className="px-4 py-3 text-left font-medium">到期日</th>
            <th className="px-4 py-3 text-left font-medium">剩餘天數</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr
              key={item.id}
              className="cursor-pointer border-b transition-colors last:border-0 hover:bg-muted/50"
              onClick={() => navigate('/subscriptions')}
            >
              <td className="px-4 py-3">{item.service_name}</td>
              <td className="px-4 py-3">{fmtDate(item.expiry_date)}</td>
              <td className="px-4 py-3">
                <Badge variant={item.daysLeft <= 7 ? 'destructive' : 'secondary'}>
                  {item.daysLeft} 天
                </Badge>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function DashboardPage() {
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
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">總覽</h1>

      {isLoading && <p className="text-sm text-muted-foreground">載入中...</p>}
      {isError && <p className="text-sm text-destructive">載入失敗，請重新整理頁面</p>}

      {!isLoading && !isError && (
        <>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
            <StatCard title="訂閱總數" value={`${stats.activeCount} 個`} />
            <StatCard title="即將到期" value={`${stats.expiringCount} 個`} />
            <StatCard title="本月費用" value={formatTWD(stats.thisMonthCost)} />
            <StatCard title="下月費用" value={formatTWD(stats.nextMonthCost)} />
            <StatCard title="歷史付款總計" value={formatTWD(stats.historicalTotal)} />
          </div>

          <div>
            <h2 className="mb-3 text-lg font-medium">即將到期（30 天內）</h2>
            <ExpiringTable items={stats.expiringSubscriptions} />
          </div>
        </>
      )}
    </div>
  )
}
