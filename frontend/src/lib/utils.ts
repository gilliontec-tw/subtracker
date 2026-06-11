/**
 * lib/utils.ts — 全域共用工具函式
 *
 * cn：合併 Tailwind CSS class 的標準寫法（shadcn/ui 慣例）
 * fmtDate：日期字串格式化，統一顯示風格
 */
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

/**
 * 合併多個 CSS class 字串，自動處理 Tailwind 衝突（例如 p-2 與 p-4 同時存在時保留後者）。
 * shadcn/ui 所有元件都使用此函式。
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * 將 ISO 日期字串格式化為 YYYY/MM/DD 顯示。
 * 只取前 10 字元避免時區問題（後端回傳 "2024-05-01" 形式，不含時間）。
 * 空值或 undefined 回傳破折號 "—"。
 */
export function fmtDate(s: string | null | undefined): string {
  if (!s) return '—'
  return s.slice(0, 10).replace(/-/g, '/')
}
