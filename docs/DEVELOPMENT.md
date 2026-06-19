# Local development and testing

## Prerequisites

- Python 3.12
- PostgreSQL 16 or newer
- GNU gettext

Create a virtual environment, install `requirements.txt`, copy `.env.example` to a private `.env`, create the database, and export the variables before running Django commands.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
set -a; . ./.env; set +a
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_reference_data
.venv/bin/python manage.py runserver 127.0.0.1:8000
```

Development credentials are never seeded automatically. Use fake data only.

## Test command

```bash
.venv/bin/pytest --reuse-db
```

Additional checks:

```bash
.venv/bin/ruff check .
.venv/bin/python manage.py check --deploy
.venv/bin/pip-audit -r requirements.txt
```

The test suite uses the mock offer provider and never contacts a production grocery site.

## Project structure

Each top-level Django application owns one domain. Business operations that require transactions live in `services.py`; request handlers remain thin. Templates are in `templates/`, browser assets in `static/`, deployment units in `deploy/`, and operational tools in `scripts/`.

## Migrations

Create migrations only after reviewing model changes:

```bash
.venv/bin/python manage.py makemigrations
.venv/bin/python manage.py migrate --plan
.venv/bin/python manage.py migrate
```

Prefer additive changes. Back up production before schema changes. Reversing a migration must be reviewed for data loss; do not blindly migrate backward.

