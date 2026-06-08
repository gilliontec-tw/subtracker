# System Settings Design

## Goal

Allow admins to configure SMTP, App URL, sender name, and notification schedule via a web UI, without requiring SSH access to edit `.env`. Settings are stored in a `system_settings` DB table with per-key fallback to `.env` values.

## Architecture

Key-value store in PostgreSQL. Each setting is one row (`key`, `value`, `updated_at`). `SettingsService` reads each key from DB first; if absent, falls back to the corresponding `.env` value. SMTP password is encrypted with Fernet symmetric encryption using a key stored in `.env` as `SETTINGS_ENCRYPTION_KEY`.

## Decisions

| Decision | Choice |
|----------|--------|
| Storage model | Key-value table (`system_settings`) |
| Fallback | Per-key: DB → `.env` |
| GET response | Returns currently-effective value (DB or .env) |
| Save UX | Single "儲存所有設定" button, one PUT request |
| Password field on load | Empty, placeholder "留空則不變"; null payload = skip update |
| Test email | Uses form values (unsaved); recipient = current admin's email |
| Encryption key missing | Service starts normally; password field cannot be saved to DB, shows warning |
| Notification time apply | Restart required; UI shows hint |
| Sidebar placement | Bottom of sidebar, admin-only, same level as 使用者管理 |

## Setting Keys

| Key | Type | Fallback (.env) | Notes |
|-----|------|-----------------|-------|
| `smtp_host` | string | `SMTP_HOST` | |
| `smtp_port` | int | `SMTP_PORT` | |
| `smtp_user` | string | `SMTP_USER` | |
| `smtp_password` | string | `SMTP_PASSWORD` | Fernet-encrypted in DB |
| `smtp_from` | string | `SMTP_FROM` | Raw email address e.g. `noreply@corp.com` |
| `smtp_sender_name` | string | — | Display name e.g. `SubTrack`. Default: `SubTrack` |
| `app_url` | string | `APP_URL` | Used in invite and password reset links |
| `notification_cron_hour` | int | `NOTIFICATION_CRON_HOUR` | 0–23, default 8 |
| `notification_cron_minute` | int | `NOTIFICATION_CRON_MINUTE` | 0–59, default 0 |

## Backend

### New Files

**`backend/src/domain/entities/system_setting.py`**
```python
@dataclass
class SystemSetting:
    key: str
    value: str | None
    updated_at: datetime
```

**`backend/src/domain/repositories/system_setting_repository.py`**
```python
class SystemSettingRepository(ABC):
    async def get(self, key: str) -> str | None: ...
    async def set(self, key: str, value: str) -> None: ...
    async def get_all(self) -> dict[str, str]: ...
```

**`backend/src/infrastructure/database/repositories/system_setting_repository.py`**
`SqlSystemSettingRepository` implements the above using SQLAlchemy async session. `set()` uses upsert (INSERT ... ON CONFLICT DO UPDATE).

**`backend/src/application/services/settings_service.py`**

Core logic:
- `get(key)` → DB value if present, else `.env` value, else default
- `get_smtp_config()` → returns `SmtpConfig` dataclass with all five SMTP fields resolved
- `get_app_url()` → resolved `app_url` string
- `get_notification_schedule()` → `(hour: int, minute: int)`
- `update(key, value)` → encrypts if key is `smtp_password` (requires `SETTINGS_ENCRYPTION_KEY`; raises `EncryptionKeyMissingError` if absent)
- Password field: if `SETTINGS_ENCRYPTION_KEY` is absent, `get()` for `smtp_password` reads from `.env` only; `update()` raises error

**`backend/src/api/v1/routers/admin_settings.py`**

```
GET  /api/v1/admin/settings          → require_admin
PUT  /api/v1/admin/settings          → require_admin
POST /api/v1/admin/settings/test-email → require_admin
```

GET response: all keys with effective values. `smtp_password` returns `"••••••••"` if set, `null` if not set. Each key includes `"source": "db" | "env" | "default"` for transparency.

PUT request body: all keys as optional strings. `smtp_password: null | ""` = skip update. `smtp_port`, `notification_cron_hour`, `notification_cron_minute` validated as integers (stored as strings in DB).

POST test-email body: all SMTP fields + optional `smtp_password`. If `smtp_password` is null/empty, load existing password from `SettingsService`. Sends email to `current_user.email` with subject "SubTrack 郵件設定測試".

**`backend/src/api/v1/schemas/admin_settings.py`**

```python
class SettingsResponse(BaseModel):
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password_set: bool          # true if a password exists (DB or .env)
    smtp_from: str
    smtp_sender_name: str
    app_url: str
    notification_cron_hour: int
    notification_cron_minute: int
    encryption_key_configured: bool  # false = password cannot be saved to DB

class SettingsUpdateRequest(BaseModel):
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_user: str | None = None
    smtp_password: str | None = None  # None or "" = skip
    smtp_from: str | None = None
    smtp_sender_name: str | None = None
    app_url: str | None = None
    notification_cron_hour: int | None = None
    notification_cron_minute: int | None = None

class TestEmailRequest(BaseModel):
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str | None = None  # None = use existing saved password
    smtp_from: str
    smtp_sender_name: str
```

### Modified Files

**`backend/src/infrastructure/database/models.py`**
Add `SystemSettingModel`:
```python
class SystemSettingModel(Base):
    __tablename__ = "system_settings"
    key = Column(String, primary_key=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

**`backend/src/api/config.py`**
Add field:
```python
settings_encryption_key: str = ""
```

**`backend/src/api/main.py`**
Register `admin_settings` router under `/api/v1`.

**`backend/src/api/v1/routers/auth.py`**
`forgot_password` endpoint: replace direct `settings.smtp_*` access with `await settings_service.get_smtp_config()`. `SettingsService` injected via `Depends()`.

**`backend/src/infrastructure/smtp/smtp_email_sender.py`**
Accept separate `sender_name: str` parameter. Construct the `From` header as `"sender_name <from_addr>"` (or just `from_addr` if `sender_name` is empty).

**`backend/src/infrastructure/scheduler/main.py`**
At startup, read `(hour, minute)` from `SettingsService` instead of env vars. Read SMTP config from `SettingsService` when constructing `SmtpEmailSender`. Uses a one-off async DB session at startup.

**`backend/alembic/versions/xxxx_add_system_settings.py`**
```python
def upgrade():
    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(), primary_key=True),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now()),
    )
```

### `.env` Changes

Add to `backend/.env` (and `.env.production.example`):
```
SETTINGS_ENCRYPTION_KEY=   # generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Frontend

### New Files

**`frontend/src/api/admin_settings.ts`**
```typescript
export function getSettings(): Promise<SettingsResponse>
export function updateSettings(payload: SettingsUpdateRequest): Promise<void>
export function testEmail(payload: TestEmailRequest): Promise<void>
```

**`frontend/src/pages/SystemSettingsPage.tsx`**

Admin-only page (`currentUser?.role !== 'admin'` → redirect). Uses `react-hook-form` + `zodResolver`. Three `<section>` blocks:

1. **郵件伺服器**
   - SMTP Host (text)
   - SMTP Port (number)
   - 帳號 (text)
   - 密碼 (password, placeholder "留空則不變")
   - 寄件人 Email (text)
   - 寄件人顯示名稱 (text, placeholder "SubTrack")
   - 「測試寄信」button — calls `testEmail` with current form values, shows toast success/error

2. **應用程式設定**
   - App URL (text, placeholder "http://192.168.1.7")

3. **通知排程**
   - 發送時間 (two number inputs: 小時 0–23, 分鐘 0–59)
   - Info text: "修改後需重新啟動服務才會生效"

Bottom: 「儲存所有設定」button. On success: toast "設定已儲存". On error: toast with error message.

If `encryption_key_configured === false`: show inline warning near password field — "尚未設定加密金鑰（SETTINGS_ENCRYPTION_KEY），密碼無法儲存至資料庫，目前使用 .env 設定"。

### Modified Files

**`frontend/src/layouts/AppLayout.tsx`**
Add to both `desktopNavLinks` and `mobileNavLinks` inside the admin block:
```tsx
<NavLink to="/settings" className={navLinkClass}>系統設定</NavLink>
```

**`frontend/src/App.tsx`**
Add route: `<Route path="/settings" element={<SystemSettingsPage />} />`

## Error Handling

| Scenario | Behaviour |
|----------|-----------|
| DB unreachable on GET settings | Return `.env` values with `source: "env"` for all keys |
| `SETTINGS_ENCRYPTION_KEY` missing, password save attempted | 400 error "加密金鑰未設定，無法儲存密碼" |
| Test email SMTP connection fails | 400 error with SMTP error message shown in toast |
| Non-admin accesses settings page | Frontend redirect to `/dashboard`; API returns 403 |
| `notification_cron_hour` out of range 0–23 | 422 validation error |

## Testing

Unit tests (backend, no DB required):
- `SettingsService.get()`: DB hit → returns DB value; DB miss → returns .env value; DB miss + no .env → returns default
- `SettingsService.update()`: no encryption key → raises `EncryptionKeyMissingError` for password key; other keys save normally
- `SettingsService.get_smtp_config()`: mixed DB + .env values resolved correctly
- Test email endpoint: SMTP send called with form values; missing password uses existing DB value

No integration tests needed (follows project's unit-test-only pattern).
