import type { AxiosError } from 'axios'
import { api } from './client'
import type { ApiResponse } from '@/types/api'

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

export interface TestEmailPayload {
  smtp_host: string
  smtp_port: number
  smtp_user: string
  smtp_password?: string
  smtp_from: string
  smtp_sender_name: string
}

function extractMessage(err: unknown, fallback: string): never {
  const detail = (err as AxiosError<{ detail?: string }>)?.response?.data?.detail
  const message = detail ?? (err as AxiosError<ApiResponse<null>>)?.response?.data?.message ?? fallback
  throw new Error(message)
}

export async function getSystemSettings(): Promise<SystemSettings> {
  const { data } = await api.get<ApiResponse<SystemSettings>>('/api/v1/admin/settings')
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

export async function updateSystemSettings(payload: SettingsUpdatePayload): Promise<void> {
  try {
    const { data } = await api.put<ApiResponse<null>>('/api/v1/admin/settings', payload)
    if (!data.success) throw new Error(data.message)
  } catch (err) {
    return extractMessage(err, '儲存設定失敗')
  }
}

export async function testSmtpEmail(payload: TestEmailPayload): Promise<string> {
  try {
    const { data } = await api.post<ApiResponse<null>>('/api/v1/admin/settings/test-email', payload)
    if (!data.success) throw new Error(data.message)
    return data.message
  } catch (err) {
    return extractMessage(err, '測試寄信失敗')
  }
}
