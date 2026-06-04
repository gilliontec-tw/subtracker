#!/bin/bash
# Daily backup script — run by host crontab: 0 2 * * * /opt/subtrack/scripts/backup.sh
set -euo pipefail

BACKUP_DIR="/opt/subtrack/backups"
COMPOSE_CMD="docker compose -f /opt/subtrack/docker-compose.yml -f /opt/subtrack/docker-compose.prod.yml"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/subtrack_${TIMESTAMP}.sql.gz"
RETAIN_DAYS=30

mkdir -p "${BACKUP_DIR}"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting backup..."

${COMPOSE_CMD} exec -T db pg_dump -U subtrack --no-owner --no-acl subtrack \
    | gzip > "${BACKUP_FILE}"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup saved: ${BACKUP_FILE} ($(du -sh "${BACKUP_FILE}" | cut -f1))"

find "${BACKUP_DIR}" -name "subtrack_*.sql.gz" -mtime +${RETAIN_DAYS} -delete
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cleaned up backups older than ${RETAIN_DAYS} days"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Done."
