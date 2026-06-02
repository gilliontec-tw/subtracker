import type { AxiosError } from 'axios'
import { api } from './client'
import type { ApiResponse, UserDetail } from '@/types/api'

interface CreateUserPayload {
  email: string
  display_name: string
  role: 'admin' | 'user'
}

interface CreateUserResult {
  id: number
  invite_token: string
}

interface UpdateUserPayload {
  display_name: string
  role: 'admin' | 'user'
}

function extractMessage(err: unknown, fallback: string): never {
  const message =
    (err as AxiosError<ApiResponse<null>>)?.response?.data?.message ?? fallback
  throw new Error(message)
}

export async function listUsers(): Promise<UserDetail[]> {
  const { data } = await api.get<ApiResponse<UserDetail[]>>('/api/v1/users')
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

export async function createUser(payload: CreateUserPayload): Promise<CreateUserResult> {
  try {
    const { data } = await api.post<ApiResponse<CreateUserResult>>('/api/v1/users', payload)
    if (!data.success || !data.data) throw new Error(data.message)
    return data.data
  } catch (err) {
    return extractMessage(err, '建立使用者失敗')
  }
}

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

export async function deleteUser(id: number): Promise<void> {
  try {
    await api.delete(`/api/v1/users/${id}`)
  } catch (err) {
    return extractMessage(err, '刪除失敗')
  }
}

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

export async function validateInvite(token: string): Promise<{ email: string }> {
  const { data } = await api.get<ApiResponse<{ email: string }>>(`/api/v1/invite/${token}`)
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

export async function acceptInvite(token: string, password: string): Promise<void> {
  try {
    await api.post(`/api/v1/invite/${token}`, { password })
  } catch (err) {
    return extractMessage(err, '設定密碼失敗')
  }
}
