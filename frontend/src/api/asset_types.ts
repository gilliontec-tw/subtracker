/**
 * api/asset_types.ts — 項目類型管理 API
 *
 * 項目類型（AssetType）是訂閱的分類標籤，例如「軟體授權」、「雲端服務」等。
 * 由管理員在系統設定頁面維護；訂閱表單與 Dashboard 的篩選下拉選單皆使用此清單。
 *
 * 刪除限制：後端會檢查是否有訂閱正在使用該類型，若有則拒絕刪除並回傳錯誤訊息。
 */
import { api } from './client'
import type { ApiResponse, AssetType } from '@/types/api'

/** 取得所有項目類型清單，依建立時間排序 */
export async function listAssetTypes(): Promise<AssetType[]> {
  const { data } = await api.get<ApiResponse<AssetType[]>>('/api/v1/asset-types')
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

/** 建立新的項目類型，名稱不可重複（後端會拒絕並回傳 409 衝突錯誤） */
export async function createAssetType(name: string): Promise<AssetType> {
  const { data } = await api.post<ApiResponse<AssetType>>('/api/v1/asset-types', { name })
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

/** 更新項目類型的名稱 */
export async function updateAssetType(id: number, name: string): Promise<AssetType> {
  const { data } = await api.patch<ApiResponse<AssetType>>(`/api/v1/asset-types/${id}`, { name })
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

/**
 * 刪除項目類型。
 * 若有訂閱正在使用此類型，後端會回傳 409 錯誤，需先將訂閱改為其他類型再刪除。
 */
export async function deleteAssetType(id: number): Promise<void> {
  await api.delete(`/api/v1/asset-types/${id}`)
}
