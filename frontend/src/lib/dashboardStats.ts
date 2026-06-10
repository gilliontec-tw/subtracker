import type { Subscription, PaymentRecord } from '@/types/api'

export interface ExpiringItem {
  id: number
  service_name: string
  login_account: string | null
  asset_type_name: string | null
  expiry_date: string
  daysLeft: number
  costTWD: number
  currency: string
  cost: string | null
}

export interface BreakdownEntry {
  cost: number
  subscriptions: Subscription[]
}

export type Breakdown = Record<string, BreakdownEntry>

export interface DashboardStats {
  activeCount: number
  expiringCount: number
  monthlyBurnRate: number
  historicalTotal: number
  unconvertiblePaymentCount: number
  expiringSubscriptions: ExpiringItem[]
  departmentBreakdown: Breakdown
  serviceBreakdown: Breakdown
}

const CYCLE_MONTHS: Record<string, number> = {
  monthly: 1,
  quarterly: 3,
  semi_annual: 6,
  annual: 12,
  biennial: 24,
}

function toCostTWD(sub: Subscription): number {
  if (sub.cost === null) return 0
  const cost = parseFloat(sub.cost)
  if (isNaN(cost)) return 0
  if (sub.currency === 'TWD' || sub.exchange_rate === null) return cost
  const rate = parseFloat(sub.exchange_rate)
  return isNaN(rate) ? cost : cost * rate
}

export function monthlyEquivalentTWD(sub: Subscription): number {
  const costTWD = toCostTWD(sub)
  const cycleMonths = sub.billing_cycle ? (CYCLE_MONTHS[sub.billing_cycle] ?? 1) : 1
  return costTWD / cycleMonths
}

function daysFromToday(dateStr: string): number {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const target = new Date(dateStr)
  target.setHours(0, 0, 0, 0)
  return Math.ceil((target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
}

export function computeStats(
  subscriptions: Subscription[],
  payments: PaymentRecord[],
): DashboardStats {
  const active = subscriptions.filter((s) => s.status === 'active')

  const monthlyBurnRate = active.reduce((sum, s) => sum + monthlyEquivalentTWD(s), 0)

  const expiringSubscriptions: ExpiringItem[] = active
    .map((s) => ({ ...s, daysLeft: daysFromToday(s.expiry_date) }))
    .filter((s) => s.daysLeft >= 0 && s.daysLeft <= 30)
    .map((s) => ({
      id: s.id,
      service_name: s.service_name,
      login_account: s.login_account,
      asset_type_name: s.asset_type_name,
      expiry_date: s.expiry_date,
      daysLeft: s.daysLeft,
      costTWD: toCostTWD(s),
      currency: s.currency,
      cost: s.cost,
    }))
    .sort((a, b) => a.daysLeft - b.daysLeft)

  // Historical total — convert non-TWD via subscription's current exchange_rate
  const subMap = new Map(subscriptions.map((s) => [s.id, s]))
  let unconvertiblePaymentCount = 0
  const historicalTotal = payments.reduce((sum, p) => {
    const amount = parseFloat(p.amount)
    if (isNaN(amount)) return sum
    if (p.currency === 'TWD') return sum + amount
    const sub = subMap.get(p.subscription_id)
    if (!sub || !sub.exchange_rate) {
      unconvertiblePaymentCount++
      return sum
    }
    const rate = parseFloat(sub.exchange_rate)
    return isNaN(rate) ? sum : sum + amount * rate
  }, 0)

  // Breakdown by department
  const departmentBreakdown: Breakdown = {}
  for (const sub of active) {
    const key = sub.department ?? '未分類'
    if (!departmentBreakdown[key]) departmentBreakdown[key] = { cost: 0, subscriptions: [] }
    departmentBreakdown[key].cost += monthlyEquivalentTWD(sub)
    departmentBreakdown[key].subscriptions.push(sub)
  }

  // Breakdown by service name
  const serviceBreakdown: Breakdown = {}
  for (const sub of active) {
    const key = sub.service_name
    if (!serviceBreakdown[key]) serviceBreakdown[key] = { cost: 0, subscriptions: [] }
    serviceBreakdown[key].cost += monthlyEquivalentTWD(sub)
    serviceBreakdown[key].subscriptions.push(sub)
  }

  return {
    activeCount: active.length,
    expiringCount: expiringSubscriptions.length,
    monthlyBurnRate,
    historicalTotal,
    unconvertiblePaymentCount,
    expiringSubscriptions,
    departmentBreakdown,
    serviceBreakdown,
  }
}
