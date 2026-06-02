# Admin Regenerate Invite Link Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow admin to regenerate an invite link for any active user so they can reset a forgotten password without email.

**Architecture:** New `RegenerateInviteUseCase` overwrites `invite_token` + `invite_token_expires_at` on the user. A new admin-only endpoint `POST /api/v1/users/{id}/invite` calls it. The frontend adds a "重設連結" button per active user row in UsersPage, which calls the endpoint and shows the link in a Dialog — reusing the same invite URL and `/invite/:token` page already in place.

**Tech Stack:** FastAPI, SQLAlchemy async, pytest-asyncio (backend); React 19, TanStack Query v5, shadcn/ui (frontend)

---

### Task 1: RegenerateInviteUseCase (TDD)

**Files:**
- Create: `backend/src/application/use_cases/regenerate_invite.py`
- Create: `backend/tests/unit/test_regenerate_invite_use_case.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/unit/test_regenerate_invite_use_case.py`:

```python
from unittest.mock import AsyncMock, MagicMock

import pytest
from application.use_cases.regenerate_invite import RegenerateInviteUseCase
from domain.exceptions import ForbiddenException, NotFoundException

from tests.unit.helpers import make_user


@pytest.fixture
def repo():
    return MagicMock()


@pytest.fixture
def use_case(repo):
    return RegenerateInviteUseCase(repo)


@pytest.mark.asyncio
async def test_regenerates_token_for_active_user(use_case, repo):
    old_token = "old-token"
    user = make_user(id=5, invite_token=old_token)
    repo.get_by_id = AsyncMock(return_value=user)
    repo.save = AsyncMock(side_effect=lambda u: u)

    result = await use_case.execute(user_id=5)

    assert result.invite_token != old_token
    assert result.invite_token is not None
    assert result.invite_token_expires_at is not None
    repo.save.assert_called_once()


@pytest.mark.asyncio
async def test_raises_not_found_if_user_missing(use_case, repo):
    repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(NotFoundException):
        await use_case.execute(user_id=99)


@pytest.mark.asyncio
async def test_raises_forbidden_if_user_inactive(use_case, repo):
    user = make_user(is_active=False)
    repo.get_by_id = AsyncMock(return_value=user)

    with pytest.raises(ForbiddenException):
        await use_case.execute(user_id=1)
```

- [ ] **Step 2: Run tests to confirm they fail**

From `backend/` with venv active:
```
pytest tests/unit/test_regenerate_invite_use_case.py -v
```
Expected: `ModuleNotFoundError` or `ImportError` — use case does not exist yet.

- [ ] **Step 3: Implement the use case**

Create `backend/src/application/use_cases/regenerate_invite.py`:

```python
import uuid
from datetime import UTC, datetime, timedelta

from domain.exceptions import ForbiddenException, NotFoundException
from domain.repositories.user_repository import UserRepository


class RegenerateInviteUseCase:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def execute(self, user_id: int):
        user = await self._repo.get_by_id(user_id)
        if user is None:
            raise NotFoundException("使用者不存在")
        if not user.is_active:
            raise ForbiddenException("無法為已停用的使用者重設連結")
        user.invite_token = str(uuid.uuid4())
        user.invite_token_expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=7)
        return await self._repo.save(user)
```

- [ ] **Step 4: Run tests to confirm they pass**

```
pytest tests/unit/test_regenerate_invite_use_case.py -v
```
Expected: 3 tests PASSED.

- [ ] **Step 5: Commit**

```
git add backend/src/application/use_cases/regenerate_invite.py backend/tests/unit/test_regenerate_invite_use_case.py
git commit -m "feat(users): add RegenerateInviteUseCase with tests"
```

---

### Task 2: Schema + Router Endpoint

**Files:**
- Modify: `backend/src/api/v1/schemas/user.py`
- Modify: `backend/src/api/v1/routers/users.py`

- [ ] **Step 1: Add response schema**

In `backend/src/api/v1/schemas/user.py`, append after the last class:

```python
class RegenerateInviteResponse(BaseModel):
    invite_token: str
```

- [ ] **Step 2: Add the endpoint**

In `backend/src/api/v1/routers/users.py`, add the import and endpoint.

Add to the imports at the top:
```python
from application.use_cases.regenerate_invite import RegenerateInviteUseCase
```

Add to the schema imports:
```python
from api.v1.schemas.user import (
    CreateUserRequest,
    CreateUserResponse,
    RegenerateInviteResponse,
    UpdateUserRequest,
    UserListItemResponse,
    UserStatusRequest,
)
```

Append the new endpoint at the end of the file:

```python
@router.post("/{id}/invite", response_model=ApiResponse[RegenerateInviteResponse])
async def regenerate_invite(
    id: int,
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = SqlUserRepository(db)
    use_case = RegenerateInviteUseCase(repo)
    user = await use_case.execute(user_id=id)
    return ApiResponse.ok(data=RegenerateInviteResponse(invite_token=user.invite_token))
```

- [ ] **Step 3: Verify lint passes**

```
ruff check src/
```
Expected: no errors. Fix any import ordering issues if reported.

- [ ] **Step 4: Commit**

```
git add backend/src/api/v1/schemas/user.py backend/src/api/v1/routers/users.py
git commit -m "feat(users): add POST /{id}/invite endpoint to regenerate invite token"
```

---

### Task 3: Frontend API Function

**Files:**
- Modify: `frontend/src/api/users.ts`

- [ ] **Step 1: Add the API function**

In `frontend/src/api/users.ts`, append after `deleteUser`:

```typescript
export async function regenerateInvite(id: number): Promise<{ invite_token: string }> {
  try {
    const { data } = await api.post<ApiResponse<{ invite_token: string }>>(
      `/api/v1/users/${id}/invite`,
    )
    if (!data.success || !data.data) throw new Error(data.message)
    return data.data
  } catch (err) {
    return extractMessage(err, '重設連結失敗')
  }
}
```

- [ ] **Step 2: Type-check**

From `frontend/`:
```
npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Commit**

```
git add frontend/src/api/users.ts
git commit -m "feat(users): add regenerateInvite API function"
```

---

### Task 4: Frontend UsersPage — Button + Dialog

**Files:**
- Modify: `frontend/src/pages/UsersPage.tsx`

- [ ] **Step 1: Replace the full file content**

Replace `frontend/src/pages/UsersPage.tsx` with:

```tsx
import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { listUsers, regenerateInvite } from '@/api/users'
import CreateUserModal from '@/components/users/CreateUserModal'
import EditUserModal from '@/components/users/EditUserModal'
import DeleteUserDialog from '@/components/users/DeleteUserDialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useToast } from '@/hooks/use-toast'

export default function UsersPage() {
  const { data: users = [], isLoading } = useQuery({
    queryKey: ['users'],
    queryFn: listUsers,
  })
  const { toast } = useToast()
  const [resetToken, setResetToken] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const { mutate: doRegenerate, isPending: isRegenerating } = useMutation({
    mutationFn: (id: number) => regenerateInvite(id),
    onSuccess: (data) => {
      setResetToken(data.invite_token)
      setCopied(false)
    },
    onError: (err: Error) => {
      toast({ title: err.message || '重設連結失敗', variant: 'destructive' })
    },
  })

  const resetUrl = resetToken
    ? `${window.location.origin}/invite/${resetToken}`
    : ''

  async function copyToClipboard() {
    await navigator.clipboard.writeText(resetUrl)
    setCopied(true)
  }

  if (isLoading) {
    return <div className="text-muted-foreground">載入中...</div>
  }

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold">使用者管理</h1>
        <CreateUserModal />
      </div>
      <div className="overflow-x-auto rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>顯示名稱</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>角色</TableHead>
              <TableHead>狀態</TableHead>
              <TableHead>建立日期</TableHead>
              <TableHead className="text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {users.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="py-8 text-center text-muted-foreground">
                  沒有使用者資料
                </TableCell>
              </TableRow>
            )}
            {users.map((user) => (
              <TableRow key={user.id}>
                <TableCell className="font-medium">{user.display_name}</TableCell>
                <TableCell className="text-muted-foreground">{user.email}</TableCell>
                <TableCell>
                  {user.role === 'admin' ? (
                    <Badge className="border-transparent bg-purple-100 text-purple-800 hover:bg-purple-100">
                      管理員
                    </Badge>
                  ) : (
                    <Badge variant="secondary">一般使用者</Badge>
                  )}
                </TableCell>
                <TableCell>
                  {user.is_active ? (
                    <Badge className="border-transparent bg-green-100 text-green-800 hover:bg-green-100">
                      啟用中
                    </Badge>
                  ) : (
                    <Badge variant="secondary">已停用</Badge>
                  )}
                </TableCell>
                <TableCell>{user.created_at ?? '—'}</TableCell>
                <TableCell className="text-right">
                  <div className="flex justify-end gap-1">
                    {user.is_active && (
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={isRegenerating}
                        onClick={() => doRegenerate(user.id)}
                      >
                        重設連結
                      </Button>
                    )}
                    <EditUserModal user={user} />
                    <DeleteUserDialog userId={user.id} displayName={user.display_name} />
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <Dialog
        open={!!resetToken}
        onOpenChange={(v) => { if (!v) { setResetToken(null); setCopied(false) } }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>重設密碼連結</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              請將以下連結傳送給使用者，連結有效期為 7 天。
            </p>
            <div className="flex gap-2">
              <Input readOnly value={resetUrl} className="text-xs" />
              <Button variant="outline" onClick={copyToClipboard}>
                {copied ? '已複製' : '複製'}
              </Button>
            </div>
            <Button className="w-full" onClick={() => { setResetToken(null); setCopied(false) }}>
              關閉
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
```

- [ ] **Step 2: Type-check**

From `frontend/`:
```
npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Manual test**
  1. Start backend (`uvicorn api.main:app --reload` from `backend/`)
  2. Start frontend (`npm run dev` from `frontend/`)
  3. Log in as admin → go to 使用者管理
  4. Confirm "重設連結" button appears only next to active users
  5. Click "重設連結" → Dialog opens with a copyable link
  6. Copy the link, open in new private tab → existing invite page loads
  7. Set a new password → verify login works with new password
  8. Confirm button is absent for disabled users

- [ ] **Step 4: Commit**

```
git add frontend/src/pages/UsersPage.tsx
git commit -m "feat(users): add reset invite link button and dialog in UsersPage"
```
