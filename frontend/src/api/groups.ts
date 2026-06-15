import type { AxiosError } from 'axios'
import { api } from './client'
import type { ApiResponse, Group, UserDetail } from '@/types/api'

function extractMessage(err: unknown, fallback: string): never {
  const message =
    (err as AxiosError<ApiResponse<null>>)?.response?.data?.message ?? fallback
  throw new Error(message)
}

export async function listGroups(): Promise<Group[]> {
  const { data } = await api.get<ApiResponse<Group[]>>('/api/v1/groups')
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

export async function createGroup(name: string): Promise<Group> {
  try {
    const { data } = await api.post<ApiResponse<Group>>('/api/v1/groups', { name })
    if (!data.success || !data.data) throw new Error(data.message)
    return data.data
  } catch (err) {
    return extractMessage(err, '建立群組失敗')
  }
}

export async function deleteGroup(id: number): Promise<void> {
  try {
    await api.delete(`/api/v1/groups/${id}`)
  } catch (err) {
    return extractMessage(err, '刪除群組失敗')
  }
}

export async function listGroupMembers(groupId: number): Promise<UserDetail[]> {
  const { data } = await api.get<ApiResponse<UserDetail[]>>(
    `/api/v1/groups/${groupId}/members`,
  )
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

export async function addGroupMember(groupId: number, userId: number): Promise<void> {
  try {
    await api.post(`/api/v1/groups/${groupId}/members`, { user_id: userId })
  } catch (err) {
    return extractMessage(err, '新增成員失敗')
  }
}

export async function removeGroupMember(groupId: number, userId: number): Promise<void> {
  try {
    await api.delete(`/api/v1/groups/${groupId}/members/${userId}`)
  } catch (err) {
    return extractMessage(err, '移除成員失敗')
  }
}

export async function getUserGroups(userId: number): Promise<Group[]> {
  const { data } = await api.get<ApiResponse<Group[]>>(`/api/v1/users/${userId}/groups`)
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}
