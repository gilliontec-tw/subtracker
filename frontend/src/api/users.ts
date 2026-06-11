/**
 * api/users.ts — 使用者管理相關 API
 *
 * 僅限管理員（admin role）呼叫，包含使用者的 CRUD 與邀請流程：
 *  - 邀請流程：建立使用者 → 取得 invite_token → 前端組成邀請連結 → 使用者透過 /invite/:token 設定密碼
 *  - 重設密碼：管理員呼叫 regenerateInvite → 取得新 token → 傳送連結給使用者
 */
import type { AxiosError } from 'axios'
import { api } from './client'
import type { ApiResponse, UserDetail } from '@/types/api'

/** 建立使用者時的請求資料 */
interface CreateUserPayload {
  email: string
  display_name: string
  role: 'admin' | 'user'
}

/** 建立使用者後的回應，包含用於產生邀請連結的一次性 token（7 天有效） */
interface CreateUserResult {
  id: number
  invite_token: string
}

/** 更新使用者時可修改的欄位 */
interface UpdateUserPayload {
  display_name: string
  role: 'admin' | 'user'
}

/**
 * 從 Axios 錯誤回應中提取後端的 message 欄位，
 * 讓 useMutation 的 onError 可以直接顯示後端的錯誤說明。
 */
function extractMessage(err: unknown, fallback: string): never {
  const message =
    (err as AxiosError<ApiResponse<null>>)?.response?.data?.message ?? fallback
  throw new Error(message)
}

/** 取得所有使用者清單（含停用帳號） */
export async function listUsers(): Promise<UserDetail[]> {
  const { data } = await api.get<ApiResponse<UserDetail[]>>('/api/v1/users')
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

/** 建立新使用者，回傳 invite_token 供產生邀請連結 */
export async function createUser(payload: CreateUserPayload): Promise<CreateUserResult> {
  try {
    const { data } = await api.post<ApiResponse<CreateUserResult>>('/api/v1/users', payload)
    if (!data.success || !data.data) throw new Error(data.message)
    return data.data
  } catch (err) {
    return extractMessage(err, '建立使用者失敗')
  }
}

/** 更新使用者的顯示名稱或角色 */
export async function updateUser(id: number, payload: UpdateUserPayload): Promise<UserDetail> {
  try {
    const { data } = await api.patch<ApiResponse<UserDetail>>(
      `/api/v1/users/${id}`,
      payload,
    )
    if (!data.success || !data.data) throw new Error(data.message)
    return data.data
  } catch (err) {
    return extractMessage(err, '更新失敗')
  }
}

/** 啟用或停用使用者帳號（is_active: false 後無法登入） */
export async function toggleUserStatus(id: number, is_active: boolean): Promise<UserDetail> {
  try {
    const { data } = await api.patch<ApiResponse<UserDetail>>(`/api/v1/users/${id}/status`, {
      is_active,
    })
    if (!data.success || !data.data) throw new Error(data.message)
    return data.data
  } catch (err) {
    return extractMessage(err, '更新狀態失敗')
  }
}

/** 永久刪除使用者（不可復原） */
export async function deleteUser(id: number): Promise<void> {
  try {
    await api.delete(`/api/v1/users/${id}`)
  } catch (err) {
    return extractMessage(err, '刪除失敗')
  }
}

/**
 * 重新產生使用者的邀請連結（舊 token 失效）。
 * 用於新使用者尚未設定密碼、或需要讓使用者重設密碼的情境。
 */
export async function regenerateInvite(id: number): Promise<{ invite_token: string }> {
  try {
    const { data } = await api.post<ApiResponse<{ invite_token: string }>>(
      `/api/v1/users/${id}/invite`,
    )
    if (!data.success || !data.data) throw new Error(data.message)
    return data.data
  } catch (err) {
    return extractMessage(err, '重設連結失敗')
  }
}

/**
 * 驗證邀請 token 是否有效，回傳對應的 email。
 * 由 InvitePage 在頁面載入時呼叫，token 無效時顯示失效訊息。
 */
export async function validateInvite(token: string): Promise<{ email: string }> {
  const { data } = await api.get<ApiResponse<{ email: string }>>(`/api/v1/invite/${token}`)
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

/** 用邀請 token 設定密碼，完成後使用者可以用 email + 新密碼登入 */
export async function acceptInvite(token: string, password: string): Promise<void> {
  try {
    await api.post(`/api/v1/invite/${token}`, { password })
  } catch (err) {
    return extractMessage(err, '設定密碼失敗')
  }
}
