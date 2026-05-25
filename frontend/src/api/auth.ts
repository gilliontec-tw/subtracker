import type { User } from '@/types/api'

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export async function login(email: string, password: string): Promise<User> {
  throw new Error('not implemented')
}

export async function logout(): Promise<void> {
  throw new Error('not implemented')
}

export async function getMe(): Promise<User> {
  throw new Error('not implemented')
}
