---
status: partial
phase: 02-feature-fixes
source: [02-VERIFICATION.md]
started: 2026-05-11T00:00:00Z
updated: 2026-05-11T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. 通知設定頁 — 停用時 email 保留驗證
expected: 關閉通知後點儲存，資料庫中該訂閱的 notification_emails 欄位不被清空
result: [pending]

### 2. Email 發送失敗 banner — create_user 路徑
expected: SMTP 設定錯誤時新增使用者，頁面顯示紅色錯誤 banner 而非成功 banner
result: [pending]

### 3. 重置密碼完整流程
expected: 點擊重置密碼按鈕 → 收到重設信件連結 → 連結可開啟設定密碼頁
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
