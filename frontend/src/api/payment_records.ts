/**
 * api/payment_records.ts — 付款紀錄相關 API
 *
 * 付款紀錄是手動建立的實際付款歷史（相對於訂閱的「預估費用」）。
 * 提供兩種查詢方式：
 *  - listBySubscription：取得特定訂閱的所有付款，用於 SubscriptionForm 內嵌的付款列表
 *  - listByFilters：依日期範圍 / 服務名稱篩選，用於 Dashboard 趨勢圖與 PaymentRecordsPage
 */
import { api } from './client'
import type { ApiResponse, PaymentRecord } from '@/types/api'

/** 取得特定訂閱的所有付款紀錄（用於訂閱編輯頁面的付款列表區塊） */
export async function listBySubscription(subscriptionId: number): Promise<PaymentRecord[]> {
  const { data } = await api.get<ApiResponse<PaymentRecord[]>>('/api/v1/payments', {
    params: { subscription_id: subscriptionId },
  })
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

/**
 * 依條件篩選付款紀錄，所有參數皆為選填。
 * @param fromDate 起始日期（YYYY-MM-DD），不傳則不限起始
 * @param toDate 結束日期（YYYY-MM-DD），不傳則不限結束
 * @param serviceName 服務名稱關鍵字篩選
 */
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

/** 新增付款紀錄，amount 傳字串以保留精度 */
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

/** 更新付款紀錄的部分欄位，只傳需要修改的欄位即可 */
export async function updatePayment(
  id: number,
  body: Partial<{ payment_date: string; amount: string; currency: string; notes: string | null }>,
): Promise<PaymentRecord> {
  const { data } = await api.put<ApiResponse<PaymentRecord>>(`/api/v1/payments/${id}`, body)
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

/** 刪除付款紀錄（不可復原） */
export async function deletePayment(id: number): Promise<void> {
  const { data } = await api.delete<ApiResponse<null>>(`/api/v1/payments/${id}`)
  if (!data.success) throw new Error(data.message)
}
