# SubTrack 部署與維運手冊

> **基本資訊**
> | 項目 | 值 |
> |------|---|
> | VM IP | `192.168.1.7` |
> | VM SSH 帳號 | `gillionsubtrack` |
> | GitHub Repo | `https://github.com/gilliontec-tw/subtracker.git` |
> | GitHub 帳號 | `Gillionservice`（密碼使用 PAT，非 GitHub 登入密碼） |

---

## 【A】本機首次設定（每台電腦只做一次）

### A-1 Clone 專案

```bash
git clone https://github.com/gilliontec-tw/subtracker.git
cd subtracker
```

Clone 完成後 `origin` 已自動指向公司 repo，無需額外設定。

---

### A-2 建立前端環境設定檔

```bash
cp frontend/.env.local.example frontend/.env.local
```

`frontend/.env.local` 內容保持預設即可：

```
VITE_API_URL=http://localhost:8000
```

> 此檔案不會 commit，每台電腦都需自行建立。

---

### A-3 建立後端環境設定檔

```bash
cp backend/.env.example backend/.env
```

開啟 `backend/.env`，填入：

```
DATABASE_URL=postgresql+asyncpg://subtrack:<DB_PASSWORD>@localhost:5432/subtrack
REDIS_URL=redis://localhost:6379/0

JWT_ACCESS_SECRET_KEY=<向管理員索取>
JWT_REFRESH_SECRET_KEY=<向管理員索取>

CORS_ORIGINS=http://localhost:5173
APP_ENV=development
APP_URL=http://localhost:5173

SMTP_HOST=pollux4.url.com.tw
SMTP_PORT=587
SMTP_USER=service@gilliontec.com.tw
SMTP_PASSWORD=<向管理員索取>
SMTP_FROM=service@gilliontec.com.tw
```

> 此檔案不會 commit，每台電腦都需自行建立。

---

### A-4 安裝依賴套件

**前端**

```bash
cd frontend
npm install
cd ..
```

**後端**（需先安裝 Python 3.11+）

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
cd ..
```

---

## 【B】本機開發（日常啟動）

開兩個終端機分別啟動：

**終端機 1 — 後端**

```bash
cd backend
.venv\Scripts\activate
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

**終端機 2 — 前端**

```bash
cd frontend
npm run dev
```

瀏覽器開 `http://localhost:5173`。

---

## 【C】推送程式碼（每次改完後執行）

```bash
git add -A
git commit -m "feat: 描述這次改了什麼"
git push
```

---

## 【D】VM 首次設定（由管理員執行一次）

### D-1 SSH 進入 VM

```bash
ssh gillionsubtrack@192.168.1.7
```

### D-2 安裝 Docker

```bash
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker

# 驗證安裝成功
docker compose version
```

### D-3 Clone 專案

```bash
mkdir -p /opt/subtrack
cd /opt/subtrack
git clone https://github.com/gilliontec-tw/subtracker.git .
# 輸入帳號：Gillionservice，密碼：PAT

# 儲存認證（之後 git pull 不再需要輸入）
git config credential.helper store
git pull
# 再輸入一次帳號/PAT，之後永久記住
```

### D-4 建立 Production .env

```bash
cd /opt/subtrack
cp .env.production.example .env
nano .env
```

填入以下內容，存檔後離開（`Ctrl+O` → `Enter` → `Ctrl+X`）：

```
POSTGRES_USER=subtrack
POSTGRES_PASSWORD=<DB_PASSWORD>
POSTGRES_DB=subtrack

DATABASE_URL=postgresql+asyncpg://subtrack:<DB_PASSWORD>@db:5432/subtrack
REDIS_URL=redis://redis:6379/0

JWT_ACCESS_SECRET_KEY=<執行 openssl rand -hex 32 產生>
JWT_REFRESH_SECRET_KEY=<執行 openssl rand -hex 32 產生>

CORS_ORIGINS=http://192.168.1.7
APP_ENV=production
APP_URL=http://192.168.1.7

SMTP_HOST=pollux4.url.com.tw
SMTP_PORT=587
SMTP_USER=service@gilliontec.com.tw
SMTP_PASSWORD=<SMTP_PASSWORD>
SMTP_FROM=service@gilliontec.com.tw

NOTIFICATION_CRON_HOUR=8
NOTIFICATION_CRON_MINUTE=0
```

> 產生 JWT 金鑰（執行兩次，各填一個）：
> ```bash
> openssl rand -hex 32
> ```

### D-5 第一次啟動服務

```bash
cd /opt/subtrack
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

> 第一次會下載 image 並編譯，需等 3–5 分鐘。

### D-6 驗證部署成功

```bash
# 所有服務狀態（api、web、scheduler、db、redis 都應為 running）
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps

# 健康檢查（預期回傳 {"status":"ok"}）
curl -s http://192.168.1.7/health

# 前端可存取（預期回傳 200）
curl -s -o /dev/null -w "%{http_code}" http://192.168.1.7/

# API 正常（預期回傳 401，代表通了）
curl -s http://192.168.1.7/api/v1/auth/me

# Scheduler 有啟動
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs scheduler --tail=10
```

---

## 【E】VM 更新部署（本機 push 後執行）

```bash
ssh gillionsubtrack@192.168.1.7
cd /opt/subtrack
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

---

## 【F】資料遷移（搬移現有資料到 VM，只做一次）

如果本機已有舊資料需要搬到 VM，依序執行：

**Step 1 — Windows 本機匯出**

```powershell
docker exec subtrack-db-1 pg_dump -U subtrack --no-owner --no-acl subtrack > C:\Users\Gillion-ADM-015\Desktop\subtrack_dump.sql
```

**Step 2 — 上傳到 VM**

```powershell
scp C:\Users\Gillion-ADM-015\Desktop\subtrack_dump.sql gillionsubtrack@192.168.1.7:/tmp/
```

**Step 3 — 先確認 DB 容器已啟動**

```bash
cd /opt/subtrack
docker compose -f docker-compose.yml up -d db
docker compose exec db pg_isready -U subtrack
```

**Step 4 — 匯入資料**

```bash
cat /tmp/subtrack_dump.sql | docker compose exec -T db psql -U subtrack subtrack

# 驗證筆數
docker compose exec db psql -U subtrack subtrack -c "SELECT count(*) FROM users;"
docker compose exec db psql -U subtrack subtrack -c "SELECT count(*) FROM saas_subscriptions;"
docker compose exec db psql -U subtrack subtrack -c "SELECT * FROM alembic_version;"
```

**Step 5 — 清理暫存檔**

```bash
rm /tmp/subtrack_dump.sql
```

---

## 【G】資料庫備份

**手動備份**

```bash
mkdir -p /opt/subtrack/backups
docker compose -f /opt/subtrack/docker-compose.yml exec -T db \
  pg_dump -U subtrack subtrack | gzip \
  > /opt/subtrack/backups/subtrack_$(date +%Y%m%d_%H%M%S).sql.gz
```

**設定每日自動備份（crontab）**

```bash
crontab -e
# 加入以下這行（每天凌晨 2:00）：
# 0 2 * * * docker compose -f /opt/subtrack/docker-compose.yml exec -T db pg_dump -U subtrack subtrack | gzip > /opt/subtrack/backups/subtrack_$(date +\%Y\%m\%d).sql.gz
```

**還原備份**

```bash
gunzip < /opt/subtrack/backups/subtrack_YYYYMMDD.sql.gz | \
  docker compose -f docker-compose.yml exec -T db psql -U subtrack subtrack
```

---

## 【H】維運速查

> 以下 `dc` = `docker compose -f docker-compose.yml -f docker-compose.prod.yml`（在 `/opt/subtrack` 目錄下執行）

| 操作 | 指令 |
| --- | --- |
| 查看所有服務狀態 | `dc ps` |
| 即時查看 log | `dc logs -f api` |
| 重啟單一服務 | `dc restart api` |
| 只重建前端 | `dc up -d --build web` |
| 只重建後端 | `dc up -d --build api` |
| 完整重建（出問題時） | `dc up -d --build --force-recreate` |
| 進 DB shell | `dc exec db psql -U subtrack subtrack` |
| 查看備份清單 | `ls -lh /opt/subtrack/backups/` |
| Docker 磁碟清理 | `docker system prune -af` |
| 離開 SSH | `exit` |
