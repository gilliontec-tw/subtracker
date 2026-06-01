import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function fmtDate(s: string | null | undefined): string {
  if (!s) return '—'
  return s.slice(0, 10).replace(/-/g, '/')
}
