# User Management Design

## Overview

Admin-only user management feature for SubTrack. Allows admins to invite new users, edit roles and status, and delete accounts. Uses invite-based registration (no self-signup). Roles are simplified to `user` and `admin` only.

---

## Backend API

Base path: `/api/v1`

### User endpoints (admin only)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/users` | List all users |
| POST | `/users` | Create user + generate invite token |
| PATCH | `/users/{id}` | Edit display name, role |
| PATCH | `/users/{id}/status` | Toggle is_active |
| DELETE | `/users/{id}` | Delete user |

**GET `/users` response:**
```json
[
  {
    "id": 1,
    "email": "user@corp.com",
    "display_name": "Wang Da Ming",
    "role": "user",
    "is_active": true,
    "created_at": "2026-05-01"
  }
]
```

**POST `/users` request:**
```json
{
  "email": "new@corp.com",
  "display_name": "Li Xiao Hua",
  "role": "user"
}
```

**POST `/users` response:**
```json
{
  "id": 2,
  "invite_url": "http://host/invite/abc123..."
}
```

**PATCH `/users/{id}` request:**
```json
{
  "display_name": "Updated Name",
  "role": "admin"
}
```

**PATCH `/users/{id}/status` request:**
```json
{ "is_active": false }
```

All admin endpoints return 403 if caller is not admin. DELETE returns 400 if trying to delete the only remaining admin.

### Invite endpoints (public)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/invite/{token}` | Validate token, return email |
| POST | `/invite/{token}` | Accept invite, set password |

**GET `/invite/{token}` response:**
```json
{ "email": "new@corp.com" }
```
Returns 404 if token invalid or expired.

**POST `/invite/{token}` request:**
```json
{ "password": "..." }
```
Returns 200 on success. Frontend redirects to `/login`.

---

## Invite Token

- UUID4, stored on user row as `invite_token` + `invite_token_expires_at`
- 7-day expiry from creation
- Cleared (set to NULL) after accepted
- Already exists in `User` entity and `SqlUserRepository`

---

## Frontend Pages

### `/users` (admin only)

Full-width table: display name, email, role, status badge (active/inactive), created date, actions column.

Actions per row:
- Edit icon → opens Edit Modal
- Delete icon → confirmation dialog, then DELETE call

Top-right: **新增使用者** button → opens Create Modal.

Non-admin accessing this route: redirect to 403 page (same pattern as rest of app).

### Create User Modal

Fields:
- 顯示名稱 (required)
- Email (required)
- 角色: radio — `user` / `admin`

On submit: POST `/api/v1/users`. On success, modal content switches to **邀請連結已產生** screen showing full invite URL + copy button. Link shown once only. Closing dismisses and refreshes user list.

### Edit User Modal

Pre-filled fields:
- 顯示名稱
- 角色 (user / admin)
- 狀態 toggle (啟用/停用) — calls PATCH `/users/{id}/status`

On save: PATCH `/api/v1/users/{id}`. Modal closes, table refreshes.

### `/invite/:token` (public, no auth required)

Standalone page outside main layout. Shows user's email (read-only), password input, confirm password input. On submit: POST `/api/v1/invite/{token}`, then redirect to `/login`. Token invalid/expired: error message shown inline.

---

## Architecture

**Backend layers (Clean Architecture):**
- `domain/entities/user.py` — already exists, no changes needed
- `domain/repositories/user_repository.py` — add `list_all` if not present
- `application/use_cases/` — add `CreateUserUseCase`, `UpdateUserUseCase`, `ToggleUserStatusUseCase`, `DeleteUserUseCase`, `AcceptInviteUseCase`
- `api/v1/routers/users.py` — new router for `/users` endpoints
- `api/v1/routers/invite.py` — new router for `/invite` endpoints

**Frontend:**
- `src/pages/UsersPage.tsx` — list page
- `src/components/users/CreateUserModal.tsx`
- `src/components/users/EditUserModal.tsx`
- `src/pages/InvitePage.tsx` — public page
- `src/api/users.ts` — API client functions
- Add `/users` route (ProtectedRoute, admin-only redirect)
- Add `/invite/:token` route (public)

---

## Error Handling

- Token expired/invalid → 404 → invite page shows "此邀請連結已失效或過期"
- Duplicate email on create → 409 → modal shows inline error
- Delete last admin → 400 → show inline error "無法刪除唯一的管理員"
- Disabled user logging in → existing auth guard handles (is_active check)

---

## Testing

Unit tests (pytest, MagicMock pattern matching existing tests):
- `CreateUserUseCase`: generates invite token, sets 7-day expiry, hashes nothing (no password yet)
- `AcceptInviteUseCase`: validates token not expired, sets password hash, clears token
- `DeleteUserUseCase`: blocks deletion of last admin
- `ToggleUserStatusUseCase`: flips is_active

No DB required — pure unit tests against mock repository, same pattern as existing use case tests.
