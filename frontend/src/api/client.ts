import axios from 'axios'
import { useAuthStore } from '@/stores/authStore'

function getCsrfToken(): string {
  const match = document.cookie.match(/csrf_token=([^;]+)/)
  if (!match) {
    console.warn('[api] csrf_token cookie not found — request may be rejected with 403')
    return ''
  }
  return decodeURIComponent(match[1])
}

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000',
  withCredentials: true,
})

api.interceptors.request.use((config) => {
  const method = config.method?.toUpperCase()
  if (method && ['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)) {
    config.headers['x-csrf-token'] = getCsrfToken()
  }
  return config
})

let isRefreshing = false
let refreshQueue: Array<(ok: boolean) => void> = []

function notifyQueue(ok: boolean) {
  refreshQueue.forEach((cb) => cb(ok))
  refreshQueue = []
}

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
