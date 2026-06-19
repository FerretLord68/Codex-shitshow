#!/usr/bin/env bash
set -euo pipefail
umask 077

BACKUP_ROOT="${BACKUP_ROOT:-/var/lib/mealhouse/backups}"
ENV_FILE="${ENV_FILE:-/etc/mealhouse/mealhouse.env}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TARGET="$BACKUP_ROOT/$STAMP"

install -d -m 0700 "$TARGET"
set -a
source "$ENV_FILE"
set +a

export PGPASSWORD="$POSTGRES_PASSWORD"
pg_dump --host="$POSTGRES_HOST" --port="$POSTGRES_PORT" --username="$POSTGRES_USER" \
  --format=custom --compress=9 --file="$TARGET/database.dump" "$POSTGRES_DB"
unset PGPASSWORD

tar --create --gzip --file="$TARGET/media.tar.gz" --directory=/var/lib/mealhouse media
install -m 0600 "$ENV_FILE" "$TARGET/mealhouse.env"
sha256sum "$TARGET/database.dump" "$TARGET/media.tar.gz" "$TARGET/mealhouse.env" > "$TARGET/SHA256SUMS"
find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -mtime "+$RETENTION_DAYS" -exec rm -rf -- {} +
echo "Backup created at $TARGET"

