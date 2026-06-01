import { api } from './client'
import type { ApiResponse, PaymentRecord } from '@/types/api'

export async function listBySubscription(subscriptionId: number): Promise<PaymentRecord[]> {
  const { data } = await api.get<ApiResponse<PaymentRecord[]>>('/api/v1/payments', {
    params: { subscription_id: subscriptionId },
  })
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

export async function listByFilters(
  fromDate?: string,
  toDate?: string,
  serviceName?: string,
): Promise<PaymentRecord[]> {
  const { data } = await api.get<ApiResponse<PaymentRecord[]>>('/api/v1/payments', {
    params: {
      ...(fromDate ? { from_date: fromDate } : {}),
      ...(toDate ? { to_date: toDate } : {}),
      ...(serviceName ? { service_name: serviceName } : {}),
    },
  })
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

export async function createPayment(body: {
  subscription_id: number
  payment_date: string
  amount: string
  currency: string
  notes?: string
}): Promise<PaymentRecord> {
  const { data } = await api.post<ApiResponse<PaymentRecord>>('/api/v1/payments', body)
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

export async function updatePayment(
  id: number,
  body: Partial<{ payment_date: string; amount: string; currency: string; notes: string | null }>,
): Promise<PaymentRecord> {
  const { data } = await api.put<ApiResponse<PaymentRecord>>(`/api/v1/payments/${id}`, body)
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

export async function deletePayment(id: number): Promise<void> {
  const { data } = await api.delete<ApiResponse<null>>(`/api/v1/payments/${id}`)
  if (!data.success) throw new Error(data.message)
}
