#!/usr/bin/env bash
# Дамп базы VinylVault из compose-контейнера в ./backups и удаление архивов старше RETENTION_DAYS.
# Запускать из cron на сервере: 30 3 * * * /srv/VinylVault/scripts/mongo_backup.sh >> /var/log/vv-backup.log 2>&1
set -euo pipefail

cd "$(dirname "$0")/.."

read_env() {
    # Значения берём построчно, чтобы не выполнять .env как shell-скрипт
    grep -E "^$1=" .env | tail -n 1 | cut -d= -f2- | tr -d '"'
}

MONGO_ROOT_USER="${MONGO_ROOT_USER:-$(read_env MONGO_ROOT_USER)}"
MONGO_ROOT_PASSWORD="${MONGO_ROOT_PASSWORD:-$(read_env MONGO_ROOT_PASSWORD)}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"

mkdir -p "$BACKUP_DIR"
archive="$BACKUP_DIR/vinylvault-$(date +%Y%m%d-%H%M%S).archive.gz"

docker compose exec -T mongo mongodump \
    --username "$MONGO_ROOT_USER" \
    --password "$MONGO_ROOT_PASSWORD" \
    --authenticationDatabase admin \
    --db VinylVault \
    --archive --gzip > "$archive"

find "$BACKUP_DIR" -name 'vinylvault-*.archive.gz' -mtime "+$RETENTION_DAYS" -delete

echo "OK: $archive ($(du -h "$archive" | cut -f1))"
