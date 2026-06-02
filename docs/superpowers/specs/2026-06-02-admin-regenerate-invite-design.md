# Admin Regenerate Invite Link — Design Spec

**Date:** 2026-06-02

## Context

Users who forget their password cannot log in to use the in-app "change password" feature. This is a dead end. The solution for an internal tool: admin regenerates an invite link for the affected user and sends it via Slack/Line. The user visits the existing `/invite/:token` page to set a new password — no new pages, no email required.

## Feature

Admin-only button on the Users management page to regenerate an invite token for any active user, producing a copyable link to share out-of-band.

---

## Backend

### New endpoint
`POST /api/v1/users/{id}/invite` — requires `require_admin`

**Logic:**
1. Fetch user by ID; return 404 if not found
2. Return 400 if `user.is_active` is False
3. Generate new `uuid.uuid4()` token
4. Set `user.invite_token = token`, `user.invite_token_expires_at = now + 7 days`
5. `await repo.save(user)`
6. Return `ApiResponse[RegenerateInviteResponse]` with `{ invite_token: str }`

### New use case
`backend/src/application/use_cases/regenerate_invite.py` — `RegenerateInviteUseCase`
- Same pattern as `CreateUserUseCase`
- Raises `NotFoundException` if user not found, `ForbiddenException` if inactive

### Schema
`backend/src/api/v1/schemas/users.py` — add `RegenerateInviteResponse(BaseModel): invite_token: str`

### File to modify
- `backend/src/api/v1/routers/users.py` — add new endpoint
- `backend/src/api/v1/schemas/users.py` — add response schema

---

## Frontend

### API function
`frontend/src/api/users.ts` — add `regenerateInvite(id: number): Promise<{ invite_token: string }>`

### UsersPage
`frontend/src/pages/UsersPage.tsx`

- Add state: `resetToken: string | null`
- Add mutation calling `regenerateInvite(user.id)` → `setResetToken(data.invite_token)`
- Per-row button: `<Button variant="ghost" size="sm">重設連結</Button>` — only rendered when `user.is_active === true`
- Dialog (reuse CreateUserModal's invite link UI pattern):
  - Title: "重設密碼連結"
  - Note: "請將以下連結傳送給使用者，連結有效期為 7 天。"
  - Read-only Input showing `${window.location.origin}/invite/${resetToken}`
  - "複製" button → `navigator.clipboard.writeText(url)`
  - "關閉" button → clears `resetToken`

---

## What Doesn't Change

- `/invite/:token` page — unchanged
- Invite validation/accept logic — unchanged
- CreateUserModal invite display — unchanged

---

## Verification

1. Admin visits `/users`
2. Click "重設連結" on an active user → Dialog appears with copyable link
3. Copy link, open in new tab → existing invite page loads, user sets new password
4. Verify "重設連結" button is absent for disabled users
5. Verify expired token (manually set `invite_token_expires_at` to past) shows "連結已失效" on invite page
