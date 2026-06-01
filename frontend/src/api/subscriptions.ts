import { api } from './client'
import type { ApiResponse, ListResponse, Subscription } from '@/types/api'

export async function listSubscriptions(
  showCancelled = false,
): Promise<{ items: Subscription[]; total: number }> {
  const { data } = await api.get<ListResponse<Subscription>>('/api/v1/subscriptions', {
    params: { limit: 500, offset: 0, show_cancelled: showCancelled },
  })
  return { items: data.data, total: data.meta.total }
}

export async function getSubscription(id: number): Promise<Subscription> {
  const { data } = await api.get<ApiResponse<Subscription>>(`/api/v1/subscriptions/${id}`)
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

export async function createSubscription(payload: Record<string, unknown>): Promise<Subscription> {
  const { data } = await api.post<ApiResponse<Subscription>>('/api/v1/subscriptions', payload)
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

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

export async function deleteSubscription(id: number): Promise<void> {
  await api.delete(`/api/v1/subscriptions/${id}`)
}

export type BatchRenewSkipped = { id: number; reason: 'not_found' | 'not_active' | 'missing_billing_cycle' }
export type BatchRenewResult = { renewed: Subscription[]; skipped: BatchRenewSkipped[] }

export async function batchRenewSubscriptions(ids: number[]): Promise<BatchRenewResult> {
  const { data } = await api.post<ApiResponse<BatchRenewResult>>('/api/v1/subscriptions/batch-renew', {
    subscription_ids: ids,
  })
  if (!data.success || !data.data) throw new Error('batch renew failed')
  return data.data
}
