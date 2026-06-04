# SubTrack 部署操作手冊

部署目標：Ubuntu VM `192.168.1.7`，使用 Docker Compose 運行全部服務。

---

## 5-1. VM 環境準備

```bash
# 更新套件清單
apt update && apt upgrade -y

# 安裝 Docker Engine（Ubuntu 官方源）
apt install -y ca-certificates curl
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" \
  | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 驗證
docker compose version
```

> **注意**：Ubuntu 26.04 的 codename 若 Docker 還未支援，改用 `noble`（24.04）的 codename：
> `$(. /etc/os-release && echo "noble")`

---

## 5-2. 專案部署

### 方式 A：Git clone（推薦）

```bash
mkdir -p /opt/subtrack
cd /opt/subtrack
git clone <your-repo-url> .
```

### 方式 B：本機打包上傳

```powershell
# 在 Windows 執行
scp -r C:\Users\Gillion-ADM-015\Desktop\Claude\projects\saas-tracker root@192.168.1.7:/opt/subtrack
```

---

## 5-3. 環境變數配置

```bash
cd /opt/subtrack

# 從範例建立 .env
cp .env.production.example .env

# 生成密碼和 JWT secret
openssl rand -hex 16   # 用於 POSTGRES_PASSWORD
openssl rand -hex 32   # 用於 JWT_ACCESS_SECRET_KEY
openssl rand -hex 32   # 用於 JWT_REFRESH_SECRET_KEY

# 填入 .env
nano .env
```

**必填欄位**：
- `POSTGRES_PASSWORD` — 自行生成的隨機密碼
- `DATABASE_URL` — 須與 `POSTGRES_PASSWORD` 一致
- `JWT_ACCESS_SECRET_KEY` / `JWT_REFRESH_SECRET_KEY` — 各自獨立生成
- `SMTP_PASSWORD` — SMTP 帳號的密碼

---

## 5-4. 數據遷移（Windows → VM）

### Step 1：Windows 本機匯出

```powershell
# PostgreSQL 在 Docker 容器中
docker exec saas-tracker-db-1 pg_dump -U test --no-owner --no-acl test > C:\Users\Gillion-ADM-015\Desktop\subtrack_dump.sql
```

### Step 2：傳輸到 VM

```powershell
scp C:\Users\Gillion-ADM-015\Desktop\subtrack_dump.sql root@192.168.1.7:/tmp/
```

### Step 3：先啟動 DB 容器

```bash
cd /opt/subtrack
docker compose -f docker-compose.yml up -d db
docker compose exec db pg_isready -U subtrack
```

### Step 4：匯入數據

```bash
cat /tmp/subtrack_dump.sql | docker compose exec -T db psql -U subtrack subtrack

# 驗證
docker compose exec db psql -U subtrack subtrack -c "SELECT count(*) FROM users;"
docker compose exec db psql -U subtrack subtrack -c "SELECT count(*) FROM saas_subscriptions;"
docker compose exec db psql -U subtrack subtrack -c "SELECT * FROM alembic_version;"
```

### Step 5：清理

```bash
rm /tmp/subtrack_dump.sql
```

---

## 5-5. Build & 啟動

```bash
cd /opt/subtrack
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

---

## 5-6. 初始化驗證

```bash
# 所有服務狀態
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps

# 健康檢查
curl -s http://192.168.1.7/health
# 預期：{"status":"ok"}

# 前端可存取
curl -s -o /dev/null -w "%{http_code}" http://192.168.1.7/
# 預期：200

# API 反代正常（401 代表通了）
curl -s http://192.168.1.7/api/v1/auth/me

# Scheduler 有啟動
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs scheduler --tail=10
```

---

## 5-7. 設定自動備份 crontab

```bash
# 建立備份目錄並設定執行權限
mkdir -p /opt/subtrack/backups
chmod +x /opt/subtrack/scripts/backup.sh

# 設定 crontab（每天凌晨 2:00）
crontab -e
# 加入以下行：
# 0 2 * * * /opt/subtrack/scripts/backup.sh >> /var/log/subtrack-backup.log 2>&1

# 手動測試備份
/opt/subtrack/scripts/backup.sh
```

---

## 日常維運指令速查

| 操作 | 指令 |
|------|------|
| 查看所有服務狀態 | `docker compose -f docker-compose.yml -f docker-compose.prod.yml ps` |
| 即時 logs | `docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f api` |
| 重啟 API | `docker compose -f docker-compose.yml -f docker-compose.prod.yml restart api` |
| 更新部署 | `git pull && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build` |
| 手動備份 | `/opt/subtrack/scripts/backup.sh` |
| 還原備份 | `gunzip < backups/xxx.sql.gz \| docker compose exec -T db psql -U subtrack subtrack` |
| 進 DB shell | `docker compose exec db psql -U subtrack subtrack` |
| 磁碟清理 | `docker system prune -af` |
| 查看備份清單 | `ls -lh /opt/subtrack/backups/` |
