import { api } from './client'
import type { ApiResponse, User } from '@/types/api'

export async function login(email: string, password: string): Promise<User> {
  const { data } = await api.post<ApiResponse<User>>('/api/v1/auth/login', { email, password })
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

export async function logout(): Promise<void> {
  await api.post('/api/v1/auth/logout')
}

export async function getMe(): Promise<User> {
  const { data } = await api.get<ApiResponse<User>>('/api/v1/auth/me')
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

export async function forgotPassword(email: string): Promise<void> {
  await api.post('/api/v1/auth/forgot-password', { email })
}

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
