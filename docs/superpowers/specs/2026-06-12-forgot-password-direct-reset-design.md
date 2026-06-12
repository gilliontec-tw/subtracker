# 忘記密碼（直接重設）設計文件

**日期：** 2026-06-12
**範圍：** 登入頁新增忘記密碼 Modal，允許使用者不透過 Email 直接重設密碼

---

## 需求

- 登入頁面新增「忘記密碼？」連結
- 點擊後開啟 Modal，顯示三個欄位：Email、新密碼、確認密碼
- 送出前驗證 Email 是否存在於使用者清單中；若不存在顯示「此帳號不存在」
- 若帳號存在，直接更新密碼，無需 Email 驗證
- 成功後關閉 Modal，顯示 toast「密碼已重設，請使用新密碼登入」
- 適用場景：內部系統（192.168.1.7），無需對外安全防護

---

## 架構

### Backend

**新 use case：** `DirectPasswordResetUseCase`
- 輸入：`email: str`, `new_password: str`
- 查詢 `repo.get_by_email(email)`
- 若使用者不存在或 `is_active=False` → 拋出 `NotFoundException`（或自訂錯誤）
- 若存在 → `hash_password(new_password)` 更新 `user.password_hash` → `repo.save(user)`

**新 Pydantic schema：** `DirectPasswordResetRequest`
```python
email: str
new_password: str  # min_length=8
```

**新 endpoint：** `POST /api/v1/auth/reset-password-direct`
- 公開端點，不需 `get_current_user`
- 帳號不存在 → `ApiResponse.fail("此帳號不存在")`
- 成功 → `ApiResponse.ok(message="密碼已重設")`

### Frontend

**新增 API 函式**（`frontend/src/api/auth.ts`）：
```ts
resetPasswordDirect(email: string, newPassword: string): Promise<void>
```

**新增元件** `frontend/src/components/auth/ForgotPasswordDialog.tsx`：
- Props：`open: boolean`, `onOpenChange: (open: boolean) => void`
- 使用現有 `Dialog/*` shadcn 元件
- Zod schema：email（非空）、new_password（≥8）、confirm_password（需等於 new_password）
- 提交錯誤顯示於表單內（非 toast）；成功則關閉 + toast

**修改** `frontend/src/pages/LoginPage.tsx`：
- 密碼欄位下方加「忘記密碼？」按鈕（text variant）
- 管理 `forgotOpen` state，傳給 `ForgotPasswordDialog`

---

## 不改動項目

- 資料庫 schema / migration（`password_hash` 欄位已存在）
- 現有 `forgot-password`（寄信流程）保留不動
- 現有 `change-password`（需登入）保留不動

---

## 測試考量

- 後端 unit test：`test_direct_password_reset.py`
  - 帳號不存在 → 回傳 fail
  - 帳號存在但 inactive → 回傳 fail
  - 帳號存在且 active → 密碼更新成功
