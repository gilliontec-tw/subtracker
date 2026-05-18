# SubTrack 全站重設計規格

**日期：** 2026-05-18
**狀態：** 待實作

---

## 目標

1. 將前後端完全分離：FastAPI 純 REST API + React SPA
2. 資料庫從 SQL Server 遷移至 PostgreSQL
3. 部署至 Linux（Docker Compose），移除 Windows 依賴
4. 重新設計 UI/UX：乾淨、無 emoji、資訊一目了然
5. 新增付款歷史紀錄功能
6. 新增訂閱唯讀詳情頁

---

## 架構總覽

```
React SPA (Vite + React Router)
    ↓
Nginx
    ├── / → React static files (try_files $uri /index.html)
    └── /api → FastAPI

FastAPI /api/v1/
    ├── JWT Auth (httpOnly cookie, access + refresh token)
    ├── CSRF (double submit cookie)
    ├── SQLAlchemy (async) + Alembic
    └── BackgroundTasks (email sending)

PostgreSQL 15

Scheduler container (APScheduler, 每日 08:00 發送到期通知)

Docker Compose (4 services: db, api, scheduler, web)
```

---

## Docker Compose

### Services

| Service | Image | 說明 |
|---|---|---|
| `db` | postgres:15 | PostgreSQL，volume 持久化，不對外暴露 port |
| `api` | 自建 Python image | FastAPI + gunicorn + uvicorn workers |
| `scheduler` | 自建 Python image（共用 api codebase） | APScheduler，獨立 process，跑通知排程 |
| `web` | 自建 Nginx image（multi-stage，含 React build） | serve static + proxy /api |

### 重點設定

- PostgreSQL port `5432` 不對外暴露（僅 internal Docker network）
- 所有敏感資訊（DB 密碼、JWT secret）透過 `.env` 注入
- db、api 加入 `healthcheck`，web/scheduler 依賴 api healthy 後啟動
- React multi-stage build：Node build → Nginx runtime，image 不含 Node

---

## 後端 API

### 基礎設定

- Base path：`/api/v1/`
- 全部回傳 JSON，不再使用 Jinja2 / TemplateResponse
- API 文件：Swagger UI 自動產生（FastAPI 內建），正式環境可設定權限限制

### 統一 Response Format

```json
{
  "success": true,
  "data": {},
  "message": ""
}
```

錯誤時：

```json
{
  "success": false,
  "data": null,
  "message": "錯誤說明"
}
```

### Exception Handling

全域 `@app.exception_handler` 攔截以下類型，統一格式回傳，不洩漏 traceback：

- `ValidationError`（422）
- `NotAuthenticatedException`（401）
- `ForbiddenException`（403）
- `NotFoundException`（404）
- `Exception`（500，log 錯誤，回傳 generic message）

### CORS

```python
allow_origins = [設定於 .env，不使用 *]
allow_credentials = True
allow_methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
allow_headers = ["*", "X-CSRF-Token"]
```

### Pagination

所有列表 API 統一支援：

```
GET /api/v1/subscriptions?limit=50&offset=0
```

Response 包含 `total` 欄位。

---

## 認證與安全

### JWT 雙 Token 機制

| Token | 存放 | 有效期 |
|---|---|---|
| Access Token | httpOnly cookie `access_token` | 30 分鐘 |
| Refresh Token | httpOnly cookie `refresh_token` | 7 天 |

- Axios interceptor 在 401 時自動呼叫 `/api/v1/auth/refresh` 取新 access token
- Refresh token 過期 → 導回 login 頁

### Cookie 設定

```
HttpOnly: true
Secure: true（正式環境）
SameSite: Lax
Path: /
```

### CSRF 保護

Double submit cookie 模式：
- 伺服器在 login 時額外設一個非 httpOnly 的 `csrf_token` cookie
- 前端所有 POST/PUT/DELETE 請求在 header 帶 `X-CSRF-Token`
- 後端 middleware 驗證 header 值與 cookie 值一致

### 密碼雜湊

繼續使用 `passlib + bcrypt`，確認 rounds >= 12。

### Login Rate Limit

使用 `slowapi`：5 次失敗 / 分鐘 / IP，超過回 429。

### Security Headers（Nginx）

```
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Content-Security-Policy: default-src 'self'
```

---

## 資料庫

### 遷移：SQL Server → PostgreSQL

**型別對應：**

| SQL Server | PostgreSQL |
|---|---|
| `NVARCHAR` | `TEXT` |
| `DATETIME` | `TIMESTAMP WITH TIME ZONE` |
| `BIT` | `BOOLEAN` |
| `DECIMAL(10,2)` | `NUMERIC(10,2)` |
| `IDENTITY` | `SERIAL` / `gen_random_uuid()` |

**所有 datetime 欄位統一使用 UTC**（`DateTime(timezone=True)`）。前端顯示時在 client 端轉換。

### Alembic

加入 Alembic 管理所有 schema 變更：

```
alembic/
  versions/
  env.py
alembic.ini
```

每次 schema 變更必須建立 migration，支援 upgrade / downgrade。

### Connection Pool（asyncpg）

```python
pool_size=10
max_overflow=20
pool_timeout=30
pool_recycle=1800
```

### Index 規劃

- `saas_subscriptions.expiry_date`（排程查詢常用）
- `saas_subscriptions.status`
- `payment_records.subscription_id`
- `payment_records.payment_date`
- `users.email`
- `audit_log.created_at`

### Soft Delete

`saas_subscriptions` 加入 `deleted_at TIMESTAMP WITH TIME ZONE`，預設 NULL。

刪除改為設定 `deleted_at`，所有查詢預設 filter `deleted_at IS NULL`。

### 新增資料表：payment_records

```sql
CREATE TABLE payment_records (
    id            SERIAL PRIMARY KEY,
    subscription_id INTEGER NOT NULL REFERENCES saas_subscriptions(id),
    payment_date  DATE NOT NULL,
    amount        NUMERIC(10,2) NOT NULL,
    currency      VARCHAR(10) NOT NULL DEFAULT 'TWD',
    source        VARCHAR(10) NOT NULL DEFAULT 'manual',  -- 'auto' | 'manual'
    notes         TEXT,
    created_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by    INTEGER REFERENCES users(id)
);
```

`source = 'auto'`：由「續約」動作自動建立。
`source = 'manual'`：使用者手動補登。

### 資料遷移腳本

提供 `scripts/migrate_to_postgres.py`：從 SQL Server 匯出資料，轉換格式，匯入 PostgreSQL。

---

## 新功能：付款歷史紀錄

### 觸發方式

1. **自動**：點擊「續約」按鈕 → API `POST /api/v1/subscriptions/{id}/renew` → 自動建立一筆 `payment_records`（日期=今日、金額=訂閱的 cost、source='auto'）
2. **手動**：在訂閱詳情頁手動新增歷史紀錄（date、amount、currency、notes 自填）

### 重複登錄處理

紀錄顯示 `source` 標籤（系統自動 / 手動），讓使用者自行判斷是否重複並刪除。無系統強制去重。

### API

```
GET    /api/v1/subscriptions/{id}/payments        列出付款紀錄
POST   /api/v1/subscriptions/{id}/payments        新增手動紀錄
DELETE /api/v1/payments/{payment_id}              刪除紀錄
```

---

## 新功能：訂閱詳情頁（唯讀）

- 路徑：`/subscriptions/{id}`
- 顯示所有欄位（唯讀），底部有付款歷史紀錄 tab
- 有編輯權限的使用者看到「編輯」按鈕，可跳至 `/subscriptions/{id}/edit`
- 訂閱清單點擊整行 → 進入詳情頁（不再直接進編輯頁）

---

## UI/UX 重新設計

### 設計原則

- 無 emoji（全站移除）
- 色系收斂：neutral gray 基底，primary 保留一個強調色（藍或紫，選其一）
- 資訊密度：表格要讓人一眼看清楚，不需要點擊才能看到資訊
- 操作按鈕：不在每行重複展示，移至 hover 顯示或詳情頁

### 訂閱清單改版

**預設行為：**
- 隱藏 `status = 'cancelled'` 的訂閱，使用者可手動切換「顯示已取消」
- 預設排序：到期日最近的在最上方

**欄位重新設計：**

| 欄位 | 說明 |
|---|---|
| 服務名稱 | 主要識別（大字） |
| 帳號 | 次要資訊（小字） |
| 部門 / 分類 | 合併一欄 |
| 到期日 | 顯示日期 + 倒數天數（顏色警示） |
| 費用 | 統一格式（見下方） |
| 狀態 | badge |
| 操作 | hover 顯示，或點進詳情頁操作 |

**費用顯示統一格式：**

- TWD：`NT$690`（不寫 TWD）
- USD：`US$17`（不寫 USD）
- 其他：`{金額} {幣別}`

**倒數天數顏色規則（保持現有邏輯）：**
- ≤ 14 天：紅色
- 15–30 天：橘色
- > 30 天：綠色

### Dashboard 改版

- 移除 emoji（📅 等）
- KPI cards 保留，視覺更收斂
- 即將到期 timeline 保留

### 表單頁（建立 / 編輯）

- 移除 emoji 標題
- 欄位排版更整齊

---

## 前端架構（React）

### 技術選型

| 用途 | 套件 |
|---|---|
| 框架 | React 18 |
| 建置 | Vite |
| 路由 | React Router v6 |
| 狀態管理（auth） | Zustand |
| HTTP client | Axios（含 interceptor） |
| 樣式 | CSS Modules 或 Tailwind CSS（待定） |

### 環境設定

```
.env.development    → VITE_API_URL=http://localhost:8000
.env.production     → VITE_API_URL=（由 Nginx proxy，留空或 /api）
```

### Axios Interceptor

- Request：自動帶 `X-CSRF-Token` header
- Response：401 → 自動 refresh token，refresh 失敗 → redirect login

### 頁面清單

```
/login
/dashboard
/subscriptions                    訂閱清單
/subscriptions/create             新增訂閱
/subscriptions/{id}               訂閱詳情（唯讀）
/subscriptions/{id}/edit          編輯訂閱
/reports                          費用報表
/notifications/settings           通知設定
/account/password                 修改密碼
/admin/users                      使用者管理
/admin/users/create               新增使用者
/admin/users/{id}/edit            編輯使用者
/admin/audit-log                  操作紀錄
/admin/settings                   系統設定
/auth/set-password/{token}        設定密碼（邀請連結）
```

---

## Scheduler Container

- 獨立 Python container，不共用 API process
- 使用 APScheduler（`BlockingScheduler`）
- 每日 08:00 UTC+8 執行 `CheckAndNotifyUseCase`
- 直接連 PostgreSQL（共用 db service）
- Email 發送邏輯不變（SMTP）

---

## Logging

- 使用 Python `logging` 模組，格式輸出 JSON（結構化 log）
- 每個 request 加入 `X-Request-ID`（UUID），方便 trace
- 不使用 `print`

---

## 生產環境備注（不在本次開發範圍）

- HTTPS：部署時加入 Let's Encrypt / Certbot
- Backup：`pg_dump` 排程備份
- CI/CD：GitHub Actions（未來規劃）
- Docker image 安全：non-root user、slim image（可在 Dockerfile 加入）

---

## 實作順序建議

1. **Phase 1：後端 API 化 + PostgreSQL 遷移**
   - 建立 Docker Compose 基礎（db、api）
   - Alembic 初始化，遷移現有 schema 至 PostgreSQL
   - 建立 `payment_records` table
   - FastAPI 改為純 REST API（移除 Jinja2）
   - JWT auth、CSRF、exception handler、統一 response format
   - 資料遷移腳本

2. **Phase 2：React 前端**
   - Vite 專案初始化，Docker multi-stage build
   - Auth flow（login、refresh、logout）
   - 訂閱清單頁（含新 UI）
   - 訂閱詳情頁（唯讀）
   - 建立 / 編輯訂閱
   - 付款歷史紀錄功能
   - Dashboard、Reports、其餘頁面

3. **Phase 3：Scheduler + Nginx + 整合**
   - Scheduler container
   - Nginx 設定（gzip、security headers、proxy）
   - 完整 Docker Compose 四個 services
   - End-to-end 測試
