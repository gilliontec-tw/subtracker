/**
 * api/subscriptions.ts — 訂閱項目相關 API
 *
 * 包含訂閱的 CRUD 與批次續訂操作。
 * listSubscriptions 一次拉取最多 500 筆，搜尋與篩選在前端完成（client-side filtering），
 * 不走後端分頁，適合目前數量規模（< 500 筆）。
 */
import { api } from './client'
import type { ApiResponse, ListResponse, Subscription } from '@/types/api'

/**
 * 取得所有訂閱清單。
 * @param showSuspended true 時同時回傳已停用的訂閱，預設只回傳啟用中的項目
 */
export async function listSubscriptions(
  showSuspended = false,
): Promise<{ items: Subscription[]; total: number }> {
  const { data } = await api.get<ListResponse<Subscription>>('/api/v1/subscriptions', {
    params: { limit: 500, offset: 0, show_suspended: showSuspended },
  })
  return { items: data.data, total: data.meta.total }
}

/** 取得單筆訂閱的完整資訊（用於編輯頁面） */
export async function getSubscription(id: number): Promise<Subscription> {
  const { data } = await api.get<ApiResponse<Subscription>>(`/api/v1/subscriptions/${id}`)
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

/** 新增訂閱項目，payload 格式由 SubscriptionForm 的 buildPayload 組裝 */
export async function createSubscription(payload: Record<string, unknown>): Promise<Subscription> {
  const { data } = await api.post<ApiResponse<Subscription>>('/api/v1/subscriptions', payload)
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

/** 更新訂閱項目，payload 格式同 createSubscription */
export async function updateSubscription(
  id: number,
  payload: Record<string, unknown>,
): Promise<Subscription> {
  const { data } = await api.put<ApiResponse<Subscription>>(
    `/api/v1/subscriptions/${id}`,
    payload,
  )
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

/** 軟刪除訂閱項目（後端設定 deleted_at，不從資料庫移除） */
export async function deleteSubscription(id: number): Promise<void> {
  await api.delete(`/api/v1/subscriptions/${id}`)
}

/** 批次續訂時，被略過的項目會附上原因 */
export type BatchRenewSkipped = { id: number; reason: 'not_found' | 'not_active' | 'missing_billing_cycle' }

/** 批次續訂的回應：成功續訂的列表 + 被略過的列表 */
export type BatchRenewResult = { renewed: Subscription[]; skipped: BatchRenewSkipped[] }

/**
 * 批次續訂：後端根據各訂閱的 billing_cycle 將 expiry_date 往後推算。
 * 沒有設定 billing_cycle 的訂閱會出現在 skipped 列表。
 */
export async function batchRenewSubscriptions(ids: number[]): Promise<BatchRenewResult> {
  const { data } = await api.post<ApiResponse<BatchRenewResult>>('/api/v1/subscriptions/batch-renew', {
    subscription_ids: ids,
  })
  if (!data.success || !data.data) throw new Error('batch renew failed')
  return data.data
}
