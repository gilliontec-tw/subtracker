/**
 * lib/dashboardStats.ts — Dashboard 統計資料計算邏輯
 *
 * 純函式，不依賴 React 或外部狀態，方便單元測試。
 * 接收訂閱清單與付款紀錄，計算出 Dashboard 頁面所需的所有統計數字。
 *
 * 費用換算策略：
 *  - 非 TWD 訂閱以訂閱上設定的 exchange_rate 即時換算（非歷史匯率）
 *  - 找不到匯率的付款記錄計入 unconvertiblePaymentCount，Dashboard 顯示提示
 */
import type { Subscription, PaymentRecord } from '@/types/api'

/** Dashboard 到期預警表格的單筆資料 */
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

/** 費用分析圓餅圖的單一分組（部門或服務名稱） */
export interface BreakdownEntry {
  cost: number
  subscriptions: Subscription[]
}

/** 費用分析圓餅圖的完整資料，key 為部門名稱或服務名稱 */
export type Breakdown = Record<string, BreakdownEntry>

/** Dashboard 計算完成後的統一資料結構 */
export interface DashboardStats {
  activeCount: number
  expiringCount: number
  monthlyBurnRate: number           // 所有啟用訂閱的月均費用總和（TWD）
  historicalTotal: number           // 實際付款紀錄的歷史總金額（TWD）
  unconvertiblePaymentCount: number // 無法換算為 TWD 的付款筆數
  expiringSubscriptions: ExpiringItem[]
  departmentBreakdown: Breakdown
  serviceBreakdown: Breakdown
}

/** 各計費週期對應的月數，用於計算月均攤銷費用 */
const CYCLE_MONTHS: Record<string, number> = {
  monthly: 1,
  quarterly: 3,
  semi_annual: 6,
  annual: 12,
  biennial: 24,
}

/** 將訂閱費用換算為 TWD，找不到匯率時直接返回原始金額（不含幣別換算） */
function toCostTWD(sub: Subscription): number {
  if (sub.cost === null) return 0
  const cost = parseFloat(sub.cost)
  if (isNaN(cost)) return 0
  if (sub.currency === 'TWD' || sub.exchange_rate === null) return cost
  const rate = parseFloat(sub.exchange_rate)
  return isNaN(rate) ? cost : cost * rate
}

/**
 * 計算訂閱的月均費用（TWD）。
 * 年繳 1200 元 → 月均 100 元；月繳 100 元 → 月均 100 元。
 * 未設定計費週期時預設當作月繳。
 */
export function monthlyEquivalentTWD(sub: Subscription): number {
  const costTWD = toCostTWD(sub)
  const cycleMonths = sub.billing_cycle ? (CYCLE_MONTHS[sub.billing_cycle] ?? 1) : 1
  return costTWD / cycleMonths
}

/**
 * 計算指定日期字串距今的天數（正數表示未來，負數表示已過期）。
 * 時間部分歸零避免跨日計算誤差。
 */
function daysFromToday(dateStr: string): number {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const target = new Date(dateStr)
  target.setHours(0, 0, 0, 0)
  return Math.ceil((target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
}

/**
 * 根據訂閱清單與付款紀錄計算 Dashboard 所有統計數字。
 * @param subscriptions 所有訂閱（含停用）
 * @param payments 所有付款紀錄
 */
export function computeStats(
  subscriptions: Subscription[],
  payments: PaymentRecord[],
): DashboardStats {
  const active = subscriptions.filter((s) => s.status === 'active')

  const monthlyBurnRate = active.reduce((sum, s) => sum + monthlyEquivalentTWD(s), 0)

  // 只顯示 30 天內到期的訂閱，依剩餘天數從少到多排序
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

  // 歷史付款總計：以各訂閱「目前」設定的匯率換算，非歷史匯率
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

  // 部門費用分析
  const departmentBreakdown: Breakdown = {}
  for (const sub of active) {
    const key = sub.department ?? '未分類'
    if (!departmentBreakdown[key]) departmentBreakdown[key] = { cost: 0, subscriptions: [] }
    departmentBreakdown[key].cost += monthlyEquivalentTWD(sub)
    departmentBreakdown[key].subscriptions.push(sub)
  }

  // 服務名稱費用分析
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
