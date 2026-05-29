import { api } from './client'
import type { ApiResponse, AuditLogEntry } from '@/types/api'

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
