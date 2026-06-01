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
