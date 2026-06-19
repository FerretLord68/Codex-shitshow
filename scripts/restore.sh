#!/usr/bin/env bash
set -euo pipefail
umask 077

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 /path/to/backup-directory" >&2
  exit 2
fi
BACKUP="$(realpath "$1")"
ENV_FILE="${ENV_FILE:-/etc/mealhouse/mealhouse.env}"

cd "$BACKUP"
sha256sum --check SHA256SUMS
set -a
source "$ENV_FILE"
set +a

export PGPASSWORD="$POSTGRES_PASSWORD"
pg_restore --host="$POSTGRES_HOST" --port="$POSTGRES_PORT" --username="$POSTGRES_USER" \
  --dbname="$POSTGRES_DB" --clean --if-exists --no-owner --exit-on-error database.dump
unset PGPASSWORD

tar --extract --gzip --file=media.tar.gz --directory=/var/lib/mealhouse
/srv/mealhouse/.venv/bin/python /srv/mealhouse/manage.py check
echo "Restore completed and application check passed."

