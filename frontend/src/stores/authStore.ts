import { create } from 'zustand'
import type { User } from '@/types/api'

interface AuthState {
  currentUser: User | null
  setUser: (user: User) => void
  clear: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  currentUser: null,
  setUser: (user) => set({ currentUser: user }),
  clear: () => set({ currentUser: null }),
}))
