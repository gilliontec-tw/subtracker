/**
 * types/api.ts — 前後端共用的 TypeScript 型別定義
 *
 * 所有型別對應後端 Pydantic schema，欄位名稱與後端保持一致（snake_case）。
 * 後端 API 回應統一包裝在 ApiResponse<T> 結構中。
 *
 * 篩選器 sentinel 值說明：
 *  - '__all__'  = 全部類型（Select 選項不可為空字串，以此字串替代）
 *  - '__none__' = 未分類（asset_type_id 為 null 的訂閱）
 */

/** 計費週期 */
export type BillingCycle = 'monthly' | 'quarterly' | 'semi_annual' | 'annual' | 'biennial'

/** 支援的幣別 */
export type Currency = 'TWD' | 'USD' | 'EUR' | 'JPY' | 'GBP' | 'CNY'

/** 訂閱狀態（cancelled / renewed 由後端批次更新，前端只允許設定 active / suspended） */
export type SubscriptionStatus = 'active' | 'suspended'

/** 項目類型（管理員在系統設定中維護） */
export interface AssetType {
  id: number
  name: string
  created_at: string | null
}

/** 目前登入使用者的基本資訊與權限旗標 */
export interface User {
  id: number
  email: string
  display_name: string
  role: 'admin' | 'user'
  can_create: boolean
  can_update: boolean
  can_delete: boolean
}

/** 訂閱項目的完整欄位定義 */
export interface Subscription {
  id: number
  service_name: string
  login_account: string | null
  expiry_date: string
  notification_emails: string[]
  notification_days: number
  cost: string | null           // 數值以字串儲存，避免浮點精度問題
  currency: Currency
  exchange_rate: string | null  // 非 TWD 時用於換算月均費用，null 表示未設定
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
  asset_type_name: string | null // 後端 JOIN 查詢填入，前端直接顯示用
  created_at: string
  updated_at: string
}

/** 所有 API 的標準回應包裝格式 */
export interface ApiResponse<T> {
  success: boolean
  data: T | null
  message: string
  meta: Record<string, unknown> | null
}

/** 分頁相關的 meta 資訊 */
export interface ListMeta {
  total: number
  limit: number
  offset: number
}

/** 分頁列表回應格式 */
export interface ListResponse<T> {
  success: boolean
  data: T[]
  meta: ListMeta
}

/** 使用者管理頁面顯示用的使用者資訊（比 User 多了 is_active 與 created_at） */
export interface UserDetail {
  id: number
  email: string
  display_name: string
  role: 'admin' | 'user'
  is_active: boolean
  created_at: string | null
}

/** 稽核日誌中記錄的單一欄位變更 */
export interface AuditLogChange {
  field: string
  before: string
  after: string
}

/** 稽核日誌條目，記錄誰在何時對哪筆訂閱做了什麼操作 */
export interface AuditLogEntry {
  id: number
  action: 'create' | 'update' | 'delete'
  resource_id: number
  user_email: string | null
  service_name: string | null
  changes: AuditLogChange[] | null  // 只有 update 操作才有 changes
  created_at: string
}

/** 付款紀錄，記錄實際付款時間與金額（相對於訂閱上設定的「預估費用」） */
export interface PaymentRecord {
  id: number
  subscription_id: number
  service_name: string | null    // 非正規化欄位，方便顯示用
  department: string | null      // 非正規化欄位，方便顯示用
  login_account: string | null   // 非正規化欄位，方便顯示用
  payment_date: string
  amount: string
  currency: string
  notes: string | null
  source: string                 // 來源：'manual'（手動新增）或 'auto'（系統產生）
  created_at: string
}
