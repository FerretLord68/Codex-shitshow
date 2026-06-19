#!/usr/bin/env bash
set -euo pipefail

cd /srv/mealhouse
PREVIOUS="$(git rev-parse HEAD)"
git fetch --prune origin
git checkout --detach "${1:-origin/main}"
.venv/bin/pip install --requirement requirements.txt
set -a
source /etc/mealhouse/mealhouse.env
set +a
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py collectstatic --noinput
systemctl restart mealhouse-web mealhouse-worker
echo "$PREVIOUS" > /var/lib/mealhouse/previous-release

