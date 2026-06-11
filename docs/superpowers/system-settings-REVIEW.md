---
phase: system-settings
reviewed: 2026-06-08T00:00:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - backend/src/application/services/settings_service.py
  - backend/src/api/v1/routers/admin_settings.py
  - backend/src/api/v1/schemas/admin_settings.py
  - backend/src/domain/exceptions.py
  - backend/src/api/exception_handlers.py
  - backend/src/infrastructure/database/repositories/system_setting_repository.py
  - backend/src/infrastructure/database/models.py
  - backend/src/api/v1/routers/auth.py
  - backend/src/infrastructure/scheduler/main.py
  - backend/alembic/versions/004_add_system_settings.py
  - frontend/src/api/admin_settings.ts
  - frontend/src/pages/SystemSettingsPage.tsx
  - frontend/src/layouts/AppLayout.tsx
findings:
  critical: 3
  warning: 5
  info: 2
  total: 10
status: issues_found
---

# System Settings: Code Review Report

**Reviewed:** 2026-06-08T00:00:00Z
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

The system settings feature wires together a DB-backed key-value store with Fernet encryption for
the SMTP password. The overall architecture is sound and follows the established clean-architecture
pattern. However, three security/correctness blockers were found:

1. The `login` endpoint does not check `user.is_active`, so disabled accounts can authenticate.
2. The `get` function in `SettingsService` silently falls back to the `.env` SMTP password in
   **plaintext** when `SETTINGS_ENCRYPTION_KEY` is not configured — no decryption is attempted,
   yet the raw env value is returned as the credential. This means an admin can write a DB password
   that can never be read back (encryption key absent) while the system silently uses the old env
   credential, creating confusion and a potential credential-exposure path.
3. The scheduler reads the notification schedule only once at startup; a DB change takes effect only
   after a container restart, which is undocumented in code (only in the UI hint) and could mislead
   operators who change the hour/minute setting and expect immediate effect.

Five warnings around input validation, error-message leakage, and concurrency are also noted.

---

## Critical Issues

### CR-01: Login endpoint does not check `user.is_active`

**File:** `backend/src/api/v1/routers/auth.py:86`

**Issue:** The `/login` handler verifies the password but never checks `user.is_active`.
A deactivated user can obtain a valid `access_token` / `refresh_token` pair and operate normally
until token expiry. The `/refresh` endpoint (line 157) does check `is_active`, but login itself
does not, so a newly deactivated account can still log in fresh.

```python
# current (line 86)
if not user or not verify_password(body.password, user.password_hash):
```

**Fix:** Add the `is_active` guard at the same point:

```python
if not user or not user.is_active or not verify_password(body.password, user.password_hash):
    await redis.incr(fail_key)
    await redis.expire(fail_key, _FAIL_TTL)
    raise NotAuthenticatedException()
```

---

### CR-02: `SettingsService.get` leaks plaintext `.env` SMTP password when encryption key is absent

**File:** `backend/src/application/services/settings_service.py:44-57`

**Issue:** When `SETTINGS_ENCRYPTION_KEY` is not set (`self._fernet is None`), the code falls
through to `_ENV_FALLBACKS` and returns `settings.smtp_password` — the **plaintext** env
credential — for the `smtp_password` key. Two problems:

1. Any code path that calls `svc.get("smtp_password")` (including `get_smtp_config()`, the
   scheduler, and `forgot_password`) receives the raw password from `.env` even though `set()`
   for that key would raise a `ValueError` if called. There is no indication to the caller that
   the value came from an unencrypted env variable.
2. If the admin previously stored an encrypted DB value and the encryption key is later **rotated
   or removed**, `decrypt()` raises `InvalidToken` (line 52) and the function returns `None`
   rather than falling back to env, silently breaking email delivery. The comment on line 53 says
   "fall through to env fallback" but the code immediately `return None` on `InvalidToken` — the
   env fallback on line 56 is never reached.

```python
# current — InvalidToken path returns None, never reaches env fallback
except InvalidToken:
    return None   # <-- falls out of the if-block; line 56 is skipped
# No fernet — cannot decrypt; fall through to env fallback
```

The indentation means the `else: return db_value` and the env fallback on line 56 are **only**
reached when `key != _SMTP_PASSWORD_KEY`. When `key == _SMTP_PASSWORD_KEY` and
`self._fernet is None`, the outer `if db_value is not None and db_value != ""` block body for
the non-password branch returns, but the password branch has no `else`, so execution does fall
to line 56. Re-reading the logic: when `_fernet is None` the inner `if self._fernet:` block is
skipped entirely, so control does fall to line 56 — meaning the no-fernet path does silently
return the env plaintext password. This is a **security design flaw**: the method contract implies
the returned value is safe to use; callers cannot distinguish "DB-decrypted value" from "raw env
credential".

**Fix:** The fallback to env SMTP password when no encryption key is set should be made explicit
and should log a warning. More importantly, `InvalidToken` should also fall back to env rather
than returning `None`:

```python
async def get(self, key: str) -> str | None:
    db_value = await self._repo.get(key)
    if db_value is not None and db_value != "":
        if key == _SMTP_PASSWORD_KEY:
            if self._fernet:
                try:
                    return self._fernet.decrypt(db_value.encode()).decode()
                except InvalidToken:
                    # Key was rotated — fall through to env fallback
                    pass
            # fernet absent or decryption failed: fall through
        else:
            return db_value
    fallback_fn = _ENV_FALLBACKS.get(key)
    return fallback_fn(self._env) if fallback_fn else None
```

---

### CR-03: `notification_cron_hour` and `notification_cron_minute` have no range validation on the server

**File:** `backend/src/api/v1/schemas/admin_settings.py:26-27`

**Issue:** `SettingsUpdateRequest` declares `notification_cron_hour: int | None = None` and
`notification_cron_minute: int | None = None` with no range constraints (no `Field(ge=0, le=23)`
etc.). An admin can store `hour=99` or `minute=-1`. The scheduler reads these values via
`int(await svc.get(...))` and uses them directly in the comparison
`now.hour == target_hour and now.minute == target_minute` — a value outside `[0,23]` / `[0,59]`
means the scheduler **never fires**, silently breaking all renewal notifications.

The frontend enforces `min`/`max` on the HTML input (lines 215/222) but there is no server-side
guard. Any direct API call bypasses this.

**Fix:** Add Pydantic constraints in the schema:

```python
from pydantic import Field

class SettingsUpdateRequest(BaseModel):
    ...
    notification_cron_hour: int | None = Field(default=None, ge=0, le=23)
    notification_cron_minute: int | None = Field(default=None, ge=0, le=59)
    smtp_port: int | None = Field(default=None, ge=1, le=65535)
```

---

## Warnings

### WR-01: `test-email` endpoint leaks raw SMTP exception messages to the client

**File:** `backend/src/api/v1/routers/admin_settings.py:101-102`

**Issue:** The exception message from `smtplib.SMTPException` or `OSError` is embedded verbatim
in the 400 response:

```python
raise BadRequestException(f"寄信失敗：{e}")
```

SMTP errors can include internal hostnames, authentication details, or server banners that expose
infrastructure information. The same pattern is used in `forgot_password` in `auth.py` indirectly
via the `SmtpEmailSender`.

**Fix:** Log the full exception server-side and return a generic client message:

```python
except (smtplib.SMTPException, OSError) as e:
    logger.warning("SMTP test failed: %s", e)
    raise BadRequestException("寄信失敗，請確認 SMTP 設定是否正確")
```

---

### WR-02: `SettingsService.get` makes multiple separate DB round-trips per request

**File:** `backend/src/api/v1/routers/admin_settings.py:25-38`

**Issue:** `get_settings` calls `await svc.get(...)` nine times sequentially, each issuing an
independent `SELECT` against the database. The repository has a `get_all()` method that fetches
all rows in one query but it is never called. This is a correctness-adjacent concern: under high
concurrency a setting may be updated between the first and last `get()` call, making the returned
`SettingsResponse` reflect a mix of old and new values in the same response.

**Fix:** Add a `get_all_with_fallbacks()` helper to `SettingsService` backed by a single
`repo.get_all()` call, and use it in `get_settings`.

---

### WR-03: Scheduler reads schedule only at startup; dynamic changes have no effect without restart

**File:** `backend/src/infrastructure/scheduler/main.py:86-98`

**Issue:** `_read_schedule()` is called once in `main()` and the resulting `target_hour` /
`target_minute` are baked into `scheduler_loop()` for the process lifetime. The UI hints at this
(SystemSettingsPage.tsx line 226) but the code contains no enforcement — if the DB values change,
the running scheduler silently ignores them. The poll loop re-checks the shutdown event every 30
seconds (POLL_INTERVAL) but never re-reads the schedule.

**Fix:** Either re-read the schedule inside `scheduler_loop` each iteration (cheap, one DB query
per 30 s), or document this limitation with a raised exception / log at the start of each day:

```python
# Inside scheduler_loop, at the top of each loop iteration:
target_hour, target_minute = await _read_schedule()
```

---

### WR-04: `updateSystemSettings` silently swallows non-HTTP errors

**File:** `frontend/src/api/admin_settings.ts:51-61`

**Issue:** The `catch` block in `updateSystemSettings` only re-throws when
`(err as AxiosError)?.response` is truthy (i.e., the server replied with an error status). If
the request never reaches the server (network timeout, DNS failure), `err.response` is
`undefined`, and the `throw err` on line 59 re-throws the raw `AxiosError` — which has no `.message`
that matches the expected `Error` interface used by the `onError` handler in the React mutation.
The same pattern exists in `testSmtpEmail`. The result is that network errors surface as
`[object Object]` in the toast.

**Fix:**

```typescript
} catch (err) {
  if ((err as AxiosError)?.response) {
    return extractMessage(err, '儲存設定失敗')
  }
  throw err instanceof Error ? err : new Error('網路錯誤，請確認連線後重試')
}
```

---

### WR-05: `SystemSettingsPage` performs no query cache invalidation after save

**File:** `frontend/src/pages/SystemSettingsPage.tsx:94-109`

**Issue:** After `doSave` succeeds, the `['system-settings']` TanStack Query cache entry is not
invalidated. If the user navigates away and returns, the stale form values are shown until the
cache TTL expires (default: `staleTime=0` with `gcTime=5min`). More importantly,
`smtp_password_set` and `encryption_key_configured` flags shown in the UI hints will not reflect
the updated state until a page reload.

**Fix:** Add `queryClient.invalidateQueries` in `onSuccess`:

```typescript
import { useQueryClient } from '@tanstack/react-query'
// ...
const queryClient = useQueryClient()
const { mutate: doSave } = useMutation({
  mutationFn: ...,
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['system-settings'] })
    toast({ title: '設定已儲存' })
  },
})
```

---

## Info

### IN-01: `smtp_port` in `SettingsUpdateRequest` has no server-side range check

**File:** `backend/src/api/v1/schemas/admin_settings.py:20`

**Issue:** `smtp_port: int | None = None` accepts any integer. Values ≤ 0 or > 65535 are
invalid TCP port numbers and would cause `SmtpEmailSender` to fail at connect time with a
confusing OS error. This is covered by the same fix as CR-03 (`Field(ge=1, le=65535)`).

---

### IN-02: `SystemSettingsPage` role check is client-side only with no loading guard

**File:** `frontend/src/pages/SystemSettingsPage.tsx:127`

**Issue:** The `<Navigate to="/dashboard" replace />` redirect on line 127 runs after hooks are
called, but before `isLoading` is resolved. If `currentUser` is `null` (not yet hydrated from
cookie/session), the page redirects non-admin users correctly, but an authenticated admin whose
Zustand store has not yet rehydrated will also be redirected away before `currentUser` is
populated. The server-side `require_admin` guard prevents actual data exposure, so this is a UX
issue rather than a security gap, but it could cause confusing redirects on hard reload.

---

_Reviewed: 2026-06-08T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
