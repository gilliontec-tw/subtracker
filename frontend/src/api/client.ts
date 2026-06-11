/**
 * api/client.ts — Axios 全域客戶端
 *
 * 建立一個帶 baseURL 與 withCredentials 的 axios 實例，供所有 API 模組共用。
 * 包含兩層攔截器：
 *  1. 請求攔截：mutating 請求自動注入 X-CSRF-Token header
 *  2. 回應攔截：401 時嘗試用 refresh token 無感續簽，失敗則清除登入狀態
 *
 * 驗證機制：
 *  - access_token / refresh_token 以 httpOnly cookie 儲存，瀏覽器自動攜帶，前端無法讀取
 *  - csrf_token 以可讀 cookie 儲存，前端讀取後手動附加到 header（double-submit CSRF 防護）
 */
import axios from 'axios'
import { useAuthStore } from '@/stores/authStore'

/**
 * 從瀏覽器 cookie 讀取 csrf_token 值。
 * 後端在登入成功時設定此 cookie，前端每次 mutating 請求都必須帶上。
 * 找不到時只印 warning，請求仍會發出（後端會回 403）。
 */
function getCsrfToken(): string {
  const match = document.cookie.match(/csrf_token=([^;]+)/)
  if (!match) {
    console.warn('[api] csrf_token cookie not found — request may be rejected with 403')
    return ''
  }
  return decodeURIComponent(match[1])
}

/**
 * 全域 axios 實例。
 * baseURL 由環境變數 VITE_API_URL 決定（本機開發為 http://localhost:8000，
 * 連 VM 時改為 http://192.168.1.7:8000）。
 * withCredentials: true 讓瀏覽器自動攜帶 httpOnly cookie。
 */
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? '',
  withCredentials: true,
})

/**
 * 請求攔截器：只對會修改資料的 HTTP 方法注入 X-CSRF-Token header。
 * GET / HEAD 等讀取操作不需要 CSRF 保護，不注入。
 */
api.interceptors.request.use((config) => {
  const method = config.method?.toUpperCase()
  if (method && ['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)) {
    config.headers['x-csrf-token'] = getCsrfToken()
  }
  return config
})

/** 防止多個並發請求同時觸發 token refresh，確保同一時間只有一個 refresh 在執行 */
let isRefreshing = false

/** 在 refresh 進行中排隊等待的請求，refresh 完成後統一通知要重試還是失敗 */
let refreshQueue: Array<(ok: boolean) => void> = []

/** 通知所有等待中的請求 refresh 結果，並清空 queue */
function notifyQueue(ok: boolean) {
  refreshQueue.forEach((cb) => cb(ok))
  refreshQueue = []
}

/**
 * 回應攔截器：處理 401 Unauthorized 的自動續簽邏輯。
 *
 * 流程：
 *  1. 收到 401 且不是 refresh 端點本身 → 嘗試呼叫 /auth/refresh 取得新 access_token
 *  2. 若已有 refresh 進行中，把此請求排進 queue 等結果
 *  3. refresh 成功 → 重試原請求
 *  4. refresh 失敗 → 清除 authStore，ProtectedRoute 偵測到 currentUser 為 null 後導回登入頁
 *
 * `_retry` 旗標防止重試後的請求再次觸發 refresh，避免無限迴圈。
 */
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    const is401 = error.response?.status === 401
    const isRefreshEndpoint = original?.url?.includes('/auth/refresh')

    if (is401 && !original?._retry && !isRefreshEndpoint) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          refreshQueue.push((ok) => {
            if (ok) resolve(api(original))
            else reject(error)
          })
        })
      }

      original._retry = true
      isRefreshing = true

      try {
        await api.post('/api/v1/auth/refresh')
        isRefreshing = false
        notifyQueue(true)
        return api(original)
      } catch {
        isRefreshing = false
        notifyQueue(false)
        if (useAuthStore.getState().currentUser !== null) {
          useAuthStore.getState().clear()
        }
        return Promise.reject(error)
      }
    }

    if (is401 && useAuthStore.getState().currentUser !== null) {
      useAuthStore.getState().clear()
    }

    return Promise.reject(error)
  },
)
