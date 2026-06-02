import type { Subscription, PaymentRecord } from '@/types/api'

export interface ExpiringItem {
  id: number
  service_name: string
  expiry_date: string
  daysLeft: number
}

export interface DashboardStats {
  activeCount: number
  expiringCount: number
  thisMonthCost: number
  nextMonthCost: number
  historicalTotal: number
  expiringSubscriptions: ExpiringItem[]
}

function toCostTWD(sub: Subscription): number {
  if (sub.cost === null) return 0
  const cost = parseFloat(sub.cost)
  if (isNaN(cost)) return 0
  if (sub.currency === 'TWD' || sub.exchange_rate === null) return cost
  const rate = parseFloat(sub.exchange_rate)
  return isNaN(rate) ? cost : cost * rate
}

function daysFromToday(dateStr: string): number {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const target = new Date(dateStr)
  target.setHours(0, 0, 0, 0)
  return Math.ceil((target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
}

function isInYearMonth(dateStr: string, year: number, month: number): boolean {
  const d = new Date(dateStr)
  return d.getFullYear() === year && d.getMonth() === month
}

export function computeStats(
  subscriptions: Subscription[],
  payments: PaymentRecord[],
): DashboardStats {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const thisYear = today.getFullYear()
  const thisMonth = today.getMonth()
  const nextMonthYear = thisMonth === 11 ? thisYear + 1 : thisYear
  const nextMonth = thisMonth === 11 ? 0 : thisMonth + 1

  const active = subscriptions.filter((s) => s.status === 'active')

  const expiringSubscriptions: ExpiringItem[] = active
    .map((s) => ({ ...s, daysLeft: daysFromToday(s.expiry_date) }))
    .filter((s) => s.daysLeft >= 0 && s.daysLeft <= 30)
    .map((s) => ({
      id: s.id,
      service_name: s.service_name,
      expiry_date: s.expiry_date,
      daysLeft: s.daysLeft,
    }))
    .sort((a, b) => a.daysLeft - b.daysLeft)

  const thisMonthCost = active
    .filter((s) => s.next_billing_date !== null && isInYearMonth(s.next_billing_date, thisYear, thisMonth))
    .reduce((sum, s) => sum + toCostTWD(s), 0)

  const nextMonthCost = active
    .filter((s) => s.next_billing_date !== null && isInYearMonth(s.next_billing_date, nextMonthYear, nextMonth))
    .reduce((sum, s) => sum + toCostTWD(s), 0)

  const historicalTotal = payments
    .filter((p) => p.currency === 'TWD')
    .reduce((sum, p) => sum + parseFloat(p.amount), 0)

  return {
    activeCount: active.length,
    expiringCount: expiringSubscriptions.length,
    thisMonthCost,
    nextMonthCost,
    historicalTotal,
    expiringSubscriptions,
  }
}
