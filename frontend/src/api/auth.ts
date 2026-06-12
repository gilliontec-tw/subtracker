/**
 * api/auth.ts — 身份驗證相關 API
 *
 * 包含登入、登出、取得目前使用者、修改密碼等操作。
 * Token 以 httpOnly cookie 儲存，前端不直接操作，
 * 續簽邏輯統一由 api/client.ts 的回應攔截器處理。
 */
import { api } from './client'
import type { ApiResponse, User } from '@/types/api'

/** 登入並取得使用者資訊。成功後後端寫入 access_token / refresh_token / csrf_token cookie */
export async function login(email: string, password: string): Promise<User> {
  const { data } = await api.post<ApiResponse<User>>('/api/v1/auth/login', { email, password })
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

/** 登出，後端清除 cookie。失敗不影響前端流程（client.ts 攔截器會清除 authStore） */
export async function logout(): Promise<void> {
  await api.post('/api/v1/auth/logout')
}

/**
 * 取得目前登入使用者資訊。
 * 由 ProtectedRoute 在頁面載入時呼叫，用來驗證 cookie 是否仍有效，
 * 並將使用者資料寫入 authStore。
 */
export async function getMe(): Promise<User> {
  const { data } = await api.get<ApiResponse<User>>('/api/v1/auth/me')
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

/** 寄送忘記密碼信件（目前 UI 未使用，保留備用） */
export async function forgotPassword(email: string): Promise<void> {
  await api.post('/api/v1/auth/forgot-password', { email })
}

/** 修改目前登入使用者的密碼，需提供舊密碼驗證身份 */
export async function changePassword(
  currentPassword: string,
  newPassword: string,
): Promise<void> {
  const { data } = await api.post<{ success: boolean; message: string }>(
    '/api/v1/auth/change-password',
    { current_password: currentPassword, new_password: newPassword },
  )
  if (!data.success) throw new Error(data.message)
}

/** 直接重設密碼（不需 Email 驗證）。帳號不存在時後端回 400，axios 會 throw */
export async function resetPasswordDirect(
  email: string,
  newPassword: string,
): Promise<void> {
  const { data } = await api.post<ApiResponse<null>>(
    '/api/v1/auth/reset-password-direct',
    { email, new_password: newPassword },
  )
  if (!data.success) throw new Error(data.message)
}
