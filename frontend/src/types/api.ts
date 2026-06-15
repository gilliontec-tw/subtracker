export type BillingCycle = 'monthly' | 'quarterly' | 'semi_annual' | 'annual' | 'biennial'
export type Currency = 'TWD' | 'USD' | 'EUR' | 'JPY' | 'GBP' | 'CNY'
export type SubscriptionStatus = 'active' | 'suspended'

export interface Group {
  id: number
  name: string
}

export interface AssetType {
  id: number
  name: string
  created_at: string | null
}

/** Currently logged-in user (from /auth/me) */
export interface User {
  id: number
  email: string
  display_name: string
  role: 'admin' | 'user'
}

export interface Subscription {
  id: number
  service_name: string
  login_account: string | null
  expiry_date: string
  notification_emails: string[]
  notification_days: number
  cost: string | null
  currency: Currency
  exchange_rate: string | null
  notes: string | null
  owner_name: string | null
  login_password: string | null
  department: string | null
  billing_cycle: BillingCycle | null
  payment_account: string | null
  auto_renew: boolean
  trial_end_date: string | null
  next_billing_date: string | null
  status: SubscriptionStatus
  asset_type_id: number | null
  asset_type_name: string | null
  group_id: number | null
  group_name: string | null
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

/** User in admin user list (includes group membership) */
export interface UserDetail {
  id: number
  email: string
  display_name: string
  role: 'admin' | 'user'
  is_active: boolean
  created_at: string | null
  groups: Group[]
}

export interface AuditLogChange {
  field: string
  before: string
  after: string
}

export interface AuditLogEntry {
  id: number
  action: 'create' | 'update' | 'delete'
  resource_id: number
  user_email: string | null
  service_name: string | null
  changes: AuditLogChange[] | null
  created_at: string
}

export interface PaymentRecord {
  id: number
  subscription_id: number
  service_name: string | null
  department: string | null
  login_account: string | null
  payment_date: string
  amount: string
  currency: string
  notes: string | null
  source: string
  created_at: string
}
