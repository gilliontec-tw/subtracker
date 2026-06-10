import { api } from './client'
import type { ApiResponse, AssetType } from '@/types/api'

export async function listAssetTypes(): Promise<AssetType[]> {
  const { data } = await api.get<ApiResponse<AssetType[]>>('/api/v1/asset-types')
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

export async function createAssetType(name: string): Promise<AssetType> {
  const { data } = await api.post<ApiResponse<AssetType>>('/api/v1/asset-types', { name })
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

export async function updateAssetType(id: number, name: string): Promise<AssetType> {
  const { data } = await api.patch<ApiResponse<AssetType>>(`/api/v1/asset-types/${id}`, { name })
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

export async function deleteAssetType(id: number): Promise<void> {
  await api.delete(`/api/v1/asset-types/${id}`)
}
