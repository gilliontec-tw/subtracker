/**
 * stores/authStore.ts — 全域登入狀態管理（Zustand）
 *
 * 儲存目前登入使用者的資訊，作為前端的唯一真相來源（single source of truth）。
 * 僅存在記憶體中，頁面重新整理後會清空（ProtectedRoute 會重新呼叫 /auth/me 補回來）。
 *
 * 使用方式：
 *  const { currentUser } = useAuthStore()          // 元件中讀取
 *  useAuthStore.getState().clear()                  // 攔截器等非元件環境中操作
 */
import { create } from 'zustand'
import type { User } from '@/types/api'

interface AuthState {
  /** 目前登入的使用者，null 表示未登入或尚未確認登入狀態 */
  currentUser: User | null
  /** 登入成功後呼叫，寫入使用者資料 */
  setUser: (user: User) => void
  /** 登出或 token 失效時呼叫，清除使用者資料，ProtectedRoute 會導向登入頁 */
  clear: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  currentUser: null,
  setUser: (user) => set({ currentUser: user }),
  clear: () => set({ currentUser: null }),
}))
