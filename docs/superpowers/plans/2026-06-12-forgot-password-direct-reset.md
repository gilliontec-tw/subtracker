# Forgot Password (Direct Reset) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在登入頁新增「忘記密碼」Modal，讓使用者不透過 Email 直接輸入帳號和新密碼即可重設。

**Architecture:** 新增 `DirectPasswordResetUseCase` 處理業務邏輯，配一個公開的 POST 端點 `/api/v1/auth/reset-password-direct`；前端新增 `ForgotPasswordDialog` 元件，由 `LoginPage` 控制開關。

**Tech Stack:** FastAPI, bcrypt, SQLAlchemy async (backend); React 19, TanStack Query v5, react-hook-form + zod, shadcn/ui Dialog (frontend)

---

## File Map

| 動作 | 路徑 |
|------|------|
| 新增 | `backend/src/application/use_cases/direct_password_reset.py` |
| 新增 | `backend/tests/unit/test_direct_password_reset_use_case.py` |
| 修改 | `backend/src/api/v1/schemas/auth.py` |
| 修改 | `backend/src/api/v1/routers/auth.py` |
| 修改 | `frontend/src/api/auth.ts` |
| 新增 | `frontend/src/components/auth/ForgotPasswordDialog.tsx` |
| 修改 | `frontend/src/pages/LoginPage.tsx` |

---

## Task 1: Backend — DirectPasswordResetUseCase（含測試）

**Files:**
- Create: `backend/src/application/use_cases/direct_password_reset.py`
- Create: `backend/tests/unit/test_direct_password_reset_use_case.py`

- [ ] **Step 1: 先寫失敗測試**

在 `backend/tests/unit/test_direct_password_reset_use_case.py` 建立以下內容：

```python
from unittest.mock import AsyncMock, MagicMock

import pytest
from application.use_cases.direct_password_reset import DirectPasswordResetUseCase
from domain.exceptions import BadRequestException

from tests.unit.helpers import make_user


@pytest.fixture
def repo():
    return MagicMock()


@pytest.fixture
def use_case(repo):
    return DirectPasswordResetUseCase(repo)


@pytest.mark.asyncio
async def test_raises_when_user_not_found(use_case, repo):
    repo.get_by_email = AsyncMock(return_value=None)

    with pytest.raises(BadRequestException) as exc_info:
        await use_case.execute("nobody@corp.com", "newpass123")

    assert "此帳號不存在" in exc_info.value.message


@pytest.mark.asyncio
async def test_raises_when_user_inactive(use_case, repo):
    repo.get_by_email = AsyncMock(return_value=make_user(is_active=False))

    with pytest.raises(BadRequestException) as exc_info:
        await use_case.execute("u@corp.com", "newpass123")

    assert "此帳號不存在" in exc_info.value.message


@pytest.mark.asyncio
async def test_updates_password_hash(use_case, repo):
    user = make_user(password_hash="old_hash")
    repo.get_by_email = AsyncMock(return_value=user)
    repo.save = AsyncMock(side_effect=lambda u: u)

    await use_case.execute("u@corp.com", "newpass123")

    saved = repo.save.call_args[0][0]
    assert saved.password_hash != "old_hash"
    assert saved.password_hash != ""


@pytest.mark.asyncio
async def test_does_not_change_other_fields(use_case, repo):
    user = make_user(display_name="Alice", role="admin")
    repo.get_by_email = AsyncMock(return_value=user)
    repo.save = AsyncMock(side_effect=lambda u: u)

    await use_case.execute("u@corp.com", "newpass123")

    saved = repo.save.call_args[0][0]
    assert saved.display_name == "Alice"
    assert saved.role == "admin"
```

- [ ] **Step 2: 確認測試失敗**

```bash
cd backend && . .venv/bin/activate && pytest tests/unit/test_direct_password_reset_use_case.py -v
```

預期：`ImportError: cannot import name 'DirectPasswordResetUseCase'`

- [ ] **Step 3: 實作 use case**

建立 `backend/src/application/use_cases/direct_password_reset.py`：

```python
from domain.exceptions import BadRequestException
from domain.repositories.user_repository import UserRepository
from infrastructure.auth.password import hash_password


class DirectPasswordResetUseCase:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def execute(self, email: str, new_password: str) -> None:
        user = await self._repo.get_by_email(email)
        if user is None or not user.is_active:
            raise BadRequestException("此帳號不存在")

        user.password_hash = hash_password(new_password)
        await self._repo.save(user)
```

- [ ] **Step 4: 確認測試全過**

```bash
pytest tests/unit/test_direct_password_reset_use_case.py -v
```

預期：4 tests PASSED

- [ ] **Step 5: 全套 pytest 確認無回歸**

```bash
pytest
```

預期：全部 PASSED（原有 146 tests + 4 新 tests）

- [ ] **Step 6: Commit**

```bash
git add backend/src/application/use_cases/direct_password_reset.py \
        backend/tests/unit/test_direct_password_reset_use_case.py
git commit -m "feat: add DirectPasswordResetUseCase"
```

---

## Task 2: Backend — 新增 schema + endpoint

**Files:**
- Modify: `backend/src/api/v1/schemas/auth.py`
- Modify: `backend/src/api/v1/routers/auth.py`

- [ ] **Step 1: 新增 Pydantic schema**

開啟 `backend/src/api/v1/schemas/auth.py`，在 `ChangePasswordRequest` 下方加入：

```python
class DirectPasswordResetRequest(BaseModel):
    email: str
    new_password: str = Field(min_length=8)
```

（`Field` 已在 `ChangePasswordRequest` 使用，不需再 import）

- [ ] **Step 2: 新增 endpoint**

開啟 `backend/src/api/v1/routers/auth.py`：

1. 在 import 區塊加入新的 use case 和 schema：

```python
from application.use_cases.direct_password_reset import DirectPasswordResetUseCase
```

```python
from api.v1.schemas.auth import (
    ChangePasswordRequest,
    DirectPasswordResetRequest,   # 新增這行
    ForgotPasswordRequest,
    LoginRequest,
    UserResponse,
)
```

2. 在 `forgot_password` endpoint 下方新增：

```python
@router.post("/reset-password-direct")
async def reset_password_direct(
    body: DirectPasswordResetRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[None]:
    repo = SqlUserRepository(db)
    use_case = DirectPasswordResetUseCase(repo)
    await use_case.execute(email=body.email, new_password=body.new_password)
    return ApiResponse.ok(message="密碼已重設")
```

- [ ] **Step 3: 確認 backend 啟動正常**

```bash
cd backend && . .venv/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

預期：看到 `Application startup complete.`，無 import error。Ctrl+C 停止。

- [ ] **Step 4: 執行全套測試確認無回歸**

```bash
pytest
```

預期：全部 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/src/api/v1/schemas/auth.py \
        backend/src/api/v1/routers/auth.py
git commit -m "feat: add POST /api/v1/auth/reset-password-direct endpoint"
```

---

## Task 3: Frontend — API 函式

**Files:**
- Modify: `frontend/src/api/auth.ts`

- [ ] **Step 1: 新增 API 函式**

開啟 `frontend/src/api/auth.ts`，在 `changePassword` 函式下方新增：

```typescript
/** 直接重設密碼（不需 Email 驗證）。帳號不存在時後端回 400，axios 會 throw */
export async function resetPasswordDirect(
  email: string,
  newPassword: string,
): Promise<void> {
  const { data } = await api.post<ApiResponse<null>>(
    '/api/v1/auth/reset-password-direct',
    { email, new_password: newPassword },
  )
  if (!data.success) throw new Error(data.message)
}
```

- [ ] **Step 2: TypeScript 型別檢查**

```bash
cd frontend && npx tsc --noEmit
```

預期：無 error

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/auth.ts
git commit -m "feat: add resetPasswordDirect API function"
```

---

## Task 4: Frontend — ForgotPasswordDialog 元件

**Files:**
- Create: `frontend/src/components/auth/ForgotPasswordDialog.tsx`

- [ ] **Step 1: 建立元件**

建立 `frontend/src/components/auth/ForgotPasswordDialog.tsx`：

```typescript
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation } from '@tanstack/react-query'
import { resetPasswordDirect } from '@/api/auth'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { useToast } from '@/hooks/use-toast'

const schema = z
  .object({
    email: z.string().min(1, '請輸入 Email'),
    new_password: z.string().min(8, '密碼至少 8 個字元'),
    confirm_password: z.string().min(1, '請確認密碼'),
  })
  .refine((v) => v.new_password === v.confirm_password, {
    message: '密碼不一致',
    path: ['confirm_password'],
  })

type FormValues = z.infer<typeof schema>

function Field({
  label,
  error,
  children,
}: {
  label: string
  error?: string
  children: React.ReactNode
}) {
  return (
    <div className="space-y-1">
      <label className="text-sm font-medium">{label}</label>
      {children}
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  )
}

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export default function ForgotPasswordDialog({ open, onOpenChange }: Props) {
  const { toast } = useToast()
  const [apiError, setApiError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  const { mutate, isPending } = useMutation({
    mutationFn: (values: FormValues) =>
      resetPasswordDirect(values.email, values.new_password),
    onSuccess: () => {
      toast({ title: '密碼已重設，請使用新密碼登入' })
      reset()
      setApiError(null)
      onOpenChange(false)
    },
    onError: (err) => {
      const axiosErr = err as { response?: { data?: { message?: string } } }
      const msg =
        axiosErr.response?.data?.message ??
        (err as Error).message ??
        '重設失敗，請稍後再試'
      setApiError(msg)
    },
  })

  function handleOpenChange(val: boolean) {
    if (!val) {
      reset()
      setApiError(null)
    }
    onOpenChange(val)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>重設密碼</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit((v) => mutate(v))} className="space-y-4">
          <Field label="帳號 (Email)" error={errors.email?.message}>
            <Input
              type="email"
              autoComplete="email"
              placeholder="user@example.com"
              {...register('email')}
            />
          </Field>
          <Field label="新密碼" error={errors.new_password?.message}>
            <Input
              type="password"
              autoComplete="new-password"
              {...register('new_password')}
            />
          </Field>
          <Field label="確認新密碼" error={errors.confirm_password?.message}>
            <Input
              type="password"
              autoComplete="new-password"
              {...register('confirm_password')}
            />
          </Field>
          {apiError && <p className="text-sm text-destructive">{apiError}</p>}
          <Button type="submit" className="w-full" disabled={isPending}>
            {isPending ? '重設中...' : '確認重設'}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  )
}
```

- [ ] **Step 2: TypeScript 型別檢查**

```bash
cd frontend && npx tsc --noEmit
```

預期：無 error

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/auth/ForgotPasswordDialog.tsx
git commit -m "feat: add ForgotPasswordDialog component"
```

---

## Task 5: Frontend — LoginPage 整合

**Files:**
- Modify: `frontend/src/pages/LoginPage.tsx`

- [ ] **Step 1: 修改 LoginPage**

開啟 `frontend/src/pages/LoginPage.tsx`，進行以下修改：

1. 在 import 區加入：

```typescript
import { useState } from 'react'
import ForgotPasswordDialog from '@/components/auth/ForgotPasswordDialog'
```

2. 在 `export default function LoginPage()` 的函式本體最上方，`navigate` 等 hook 之後，加入：

```typescript
const [forgotOpen, setForgotOpen] = useState(false)
```

3. 在 `<Button type="submit" ...>` 下方（`</form>` 之前）加入忘記密碼按鈕：

```typescript
<div className="text-right">
  <button
    type="button"
    className="text-xs text-muted-foreground underline-offset-2 hover:underline"
    onClick={() => setForgotOpen(true)}
  >
    忘記密碼？
  </button>
</div>
```

4. 在 `</AuthLayout>` 之前（`</Card>` 之後）加入 Dialog：

```typescript
<ForgotPasswordDialog open={forgotOpen} onOpenChange={setForgotOpen} />
```

完整修改後的 `LoginPage.tsx` 結構：

```typescript
import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation } from '@tanstack/react-query'
import { login } from '@/api/auth'
import { useAuthStore } from '@/stores/authStore'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useToast } from '@/hooks/use-toast'
import AuthLayout from '@/layouts/AuthLayout'
import ForgotPasswordDialog from '@/components/auth/ForgotPasswordDialog'

const schema = z.object({
  email: z.string().min(1, '請輸入 Email'),
  password: z.string().min(1, '請輸入密碼'),
})

type FormValues = z.infer<typeof schema>

export default function LoginPage() {
  const navigate = useNavigate()
  const { currentUser, setUser } = useAuthStore()
  const { toast } = useToast()
  const [forgotOpen, setForgotOpen] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  const { mutate, isPending } = useMutation({
    mutationFn: ({ email, password }: FormValues) => login(email, password),
    onSuccess: (user) => {
      setUser(user)
      navigate('/dashboard', { replace: true })
    },
    onError: () => {
      toast({ title: '登入失敗', description: '帳號或密碼錯誤', variant: 'destructive' })
    },
  })

  if (currentUser) return <Navigate to="/subscriptions" replace />

  return (
    <AuthLayout>
      <Card>
        <CardHeader>
          <CardTitle className="text-center text-xl">SubTrack 登入</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit((data) => mutate(data))} className="space-y-4">
            <div className="space-y-1">
              <label htmlFor="email" className="text-sm font-medium">
                Email
              </label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="user@example.com"
                {...register('email')}
              />
              {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
            </div>
            <div className="space-y-1">
              <label htmlFor="password" className="text-sm font-medium">
                密碼
              </label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                {...register('password')}
              />
              {errors.password && (
                <p className="text-xs text-destructive">{errors.password.message}</p>
              )}
            </div>
            <Button type="submit" className="w-full" disabled={isPending}>
              {isPending ? '登入中...' : '登入'}
            </Button>
            <div className="text-right">
              <button
                type="button"
                className="text-xs text-muted-foreground underline-offset-2 hover:underline"
                onClick={() => setForgotOpen(true)}
              >
                忘記密碼？
              </button>
            </div>
          </form>
        </CardContent>
      </Card>
      <ForgotPasswordDialog open={forgotOpen} onOpenChange={setForgotOpen} />
    </AuthLayout>
  )
}
```

- [ ] **Step 2: TypeScript 型別檢查**

```bash
cd frontend && npx tsc --noEmit
```

預期：無 error

- [ ] **Step 3: 手動確認功能**

啟動後端與前端：
```bash
# Terminal 1
cd backend && . .venv/bin/activate && uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2
cd frontend && npm run dev
```

測試流程：
1. 前往 `http://localhost:5173/login`
2. 確認「忘記密碼？」連結出現在登入按鈕下方
3. 點擊 → Modal 開啟，含 Email、新密碼、確認新密碼三欄
4. 輸入不存在的 Email → 點確認重設 → 顯示「此帳號不存在」錯誤
5. 輸入存在的 Email + 新密碼（≥8字）→ 密碼不一致時顯示 zod 錯誤
6. 正確填寫 → 成功 toast「密碼已重設，請使用新密碼登入」，Modal 關閉
7. 用新密碼登入 → 成功

- [ ] **Step 4: 全套測試**

```bash
cd backend && pytest
```

預期：全部 PASSED

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/LoginPage.tsx
git commit -m "feat: integrate ForgotPasswordDialog into LoginPage"
```
