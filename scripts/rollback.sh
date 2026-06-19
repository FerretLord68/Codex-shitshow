#!/usr/bin/env bash
set -euo pipefail

cd /srv/mealhouse
TARGET="${1:-$(cat /var/lib/mealhouse/previous-release)}"
git checkout --detach "$TARGET"
.venv/bin/pip install --requirement requirements.txt
set -a
source /etc/mealhouse/mealhouse.env
set +a
.venv/bin/python manage.py collectstatic --noinput
systemctl restart mealhouse-web mealhouse-worker
echo "Rolled application code back to $TARGET. Database migrations require the documented migration-specific rollback review."

