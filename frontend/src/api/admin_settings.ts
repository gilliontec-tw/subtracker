/**
 * api/admin_settings.ts — 系統設定相關 API（僅管理員）
 *
 * 管理 SMTP 郵件設定、App URL、通知排程時間等全域設定。
 * 設定儲存在後端資料庫的 system_settings 表，優先權高於 .env 設定。
 *
 * 注意：smtp_password 欄位特殊處理：
 *  - GET 回傳 smtp_password_set（boolean），不回傳實際密碼
 *  - PUT 傳空字串或不傳 = 保留現有密碼；傳有值才更新
 *  - encryption_key_configured 為 false 時表示後端未設定加密金鑰，密碼無法透過 UI 修改
 */
import type { AxiosError } from 'axios'
import { api } from './client'
import type { ApiResponse } from '@/types/api'

/** 後端回傳的系統設定結構，smtp_password 只有已設定/未設定狀態，不回傳明文 */
export interface SystemSettings {
  smtp_host: string
  smtp_port: number
  smtp_user: string
  smtp_password_set: boolean
  smtp_from: string
  smtp_sender_name: string
  app_url: string
  notification_cron_hour: number
  notification_cron_minute: number
  encryption_key_configured: boolean
}

/** 更新設定的 payload，所有欄位皆為選填，只傳需要更新的欄位 */
export interface SettingsUpdatePayload {
  smtp_host?: string
  smtp_port?: number
  smtp_user?: string
  smtp_password?: string
  smtp_from?: string
  smtp_sender_name?: string
  app_url?: string
  notification_cron_hour?: number
  notification_cron_minute?: number
}

/** 測試寄信用的 SMTP 設定，使用表單目前填入的值（不需要先儲存） */
export interface TestEmailPayload {
  smtp_host: string
  smtp_port: number
  smtp_user: string
  smtp_password?: string
  smtp_from: string
  smtp_sender_name: string
}

/**
 * 從 Axios 錯誤回應中提取後端的錯誤訊息。
 * 後端可能回傳 detail（FastAPI 格式）或 message（ApiResponse 格式），優先取 detail。
 */
function extractMessage(err: unknown, fallback: string): never {
  const detail = (err as AxiosError<{ detail?: string }>)?.response?.data?.detail
  const message = detail ?? (err as AxiosError<ApiResponse<null>>)?.response?.data?.message ?? fallback
  throw new Error(message)
}

/** 取得目前的系統設定 */
export async function getSystemSettings(): Promise<SystemSettings> {
  const { data } = await api.get<ApiResponse<SystemSettings>>('/api/v1/admin/settings')
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

/**
 * 儲存系統設定。
 * smtp_password 傳 undefined 表示不變更密碼；傳空字串也視為不變更。
 */
export async function updateSystemSettings(payload: SettingsUpdatePayload): Promise<void> {
  try {
    const { data } = await api.put<ApiResponse<null>>('/api/v1/admin/settings', payload)
    if (!data.success) throw new Error(data.message)
  } catch (err) {
    if ((err as AxiosError)?.response) {
      return extractMessage(err, '儲存設定失敗')
    }
    throw err instanceof Error ? err : new Error('網路錯誤，請確認連線後重試')
  }
}

/**
 * 使用表單填入的 SMTP 設定發送測試信到 smtp_from 信箱。
 * 不需要先儲存設定，方便在儲存前先確認 SMTP 是否正常。
 * 成功時後端回傳成功訊息字串。
 */
export async function testSmtpEmail(payload: TestEmailPayload): Promise<string> {
  try {
    const { data } = await api.post<ApiResponse<null>>('/api/v1/admin/settings/test-email', payload)
    if (!data.success) throw new Error(data.message)
    return data.message
  } catch (err) {
    if ((err as AxiosError)?.response) {
      return extractMessage(err, '測試寄信失敗')
    }
    throw err instanceof Error ? err : new Error('網路錯誤，請確認連線後重試')
  }
}
