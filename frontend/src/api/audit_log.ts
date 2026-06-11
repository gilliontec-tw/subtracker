/**
 * api/audit_log.ts — 稽核日誌相關 API
 *
 * 稽核日誌由後端自動記錄訂閱的新增、修改、刪除操作，前端只有查詢功能。
 * 必須傳入日期範圍，避免一次拉取全部資料。
 */
import { api } from './client'
import type { ApiResponse, AuditLogEntry } from '@/types/api'

/**
 * 取得指定日期範圍內的稽核日誌。
 * @param fromDate 起始日期（YYYY-MM-DD）
 * @param toDate 結束日期（YYYY-MM-DD）
 */
export async function listAuditLog(
  fromDate: string,
  toDate: string,
): Promise<AuditLogEntry[]> {
  const { data } = await api.get<ApiResponse<AuditLogEntry[]>>('/api/v1/audit-log', {
    params: { from_date: fromDate, to_date: toDate },
  })
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}
