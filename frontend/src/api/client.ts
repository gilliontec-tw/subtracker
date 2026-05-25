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

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      if (useAuthStore.getState().currentUser !== null) {
        useAuthStore.getState().clear()
      }
    }
    return Promise.reject(error)
  },
)
