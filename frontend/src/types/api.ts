export type BillingCycle = 'monthly' | 'quarterly' | 'semi_annual' | 'annual' | 'biennial'
export type Currency = 'TWD' | 'USD' | 'EUR' | 'JPY' | 'GBP' | 'CNY'
export type SubscriptionStatus = 'active' | 'renewed' | 'cancelled' | 'suspended'

export interface User {
  id: number
  email: string
  display_name: string
  role: 'admin' | 'user'
  can_create: boolean
  can_update: boolean
  can_delete: boolean
}

export interface Subscription {
  id: number
  service_name: string
  login_account: string
  expiry_date: string
  notification_emails: string[]
  notification_days: number
  cost: string | null
  currency: Currency
  exchange_rate: string | null
  notes: string | null
  owner_name: string | null
  category: string | null
  department: string | null
  billing_cycle: BillingCycle | null
  payment_account: string | null
  auto_renew: boolean
  trial_end_date: string | null
  next_billing_date: string | null
  status: SubscriptionStatus
  created_at: string
  updated_at: string
}

export interface ApiResponse<T> {
  success: boolean
  data: T | null
  message: string
  meta: Record<string, unknown> | null
}

export interface ListMeta {
  total: number
  limit: number
  offset: number
}

export interface ListResponse<T> {
  success: boolean
  data: T[]
  meta: ListMeta
}

export interface UserDetail {
  id: number
  email: string
  display_name: string
  role: 'admin' | 'user'
  is_active: boolean
  created_at: string | null
}
