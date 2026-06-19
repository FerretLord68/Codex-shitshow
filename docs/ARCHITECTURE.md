# Architecture

## Decision

MealHouse uses a modular monolith:

- Python 3.12 and Django 5.2 LTS.
- PostgreSQL 16.
- Gunicorn application server behind Nginx.
- Django Tasks with a database backend for queued jobs and a dedicated worker.
- Django management commands and a systemd timer for scheduled work.
- Server-rendered Django templates, HTMX-style partial updates where useful, and small ES modules.
- Pico-inspired custom CSS with no third-party browser trackers or runtime CDN dependencies.
- Pytest, Django test tools, Playwright, and axe-core for automated verification.

## Rationale

The host has modest resources. A server-rendered modular monolith minimizes memory use and operational complexity while preserving clear module boundaries. PostgreSQL provides transactions, constraints, indexing, full-text search, and optional row-level security. LXD isolates application services from the host and publishes only port 80.

## Trust boundaries

```text
Internet
  |
  | HTTPS
  v
External reverse proxy (TLS, public rate limits)
  |
  | HTTP to 192.168.1.112:80
  v
LXD proxy device
  |
  v
Nginx :80 (container)
  |
  +--> Gunicorn on Unix socket
  |      |
  |      +--> PostgreSQL on loopback
  |      +--> private upload storage
  |
  +--> static files

Systemd worker/timer --> PostgreSQL task queue --> application services
```

Forwarded headers are accepted only when the direct peer belongs to `TRUSTED_PROXY_CIDRS`. Security-sensitive absolute URLs are always generated from `APP_URL`, never from request host headers.

## Module boundaries

- `accounts`: identity, sessions, verification, reset, exports, deletion.
- `households`: households, membership, permissions, invitations, support access.
- `catalog`: ingredients, aliases, units, nutrition, stores, products.
- `recipes`: recipes, ingredients, instructions, images, import/export.
- `planning`: meal plans, participants, templates, deterministic recommendation engine.
- `inventory`: locations, stock, transactions, deductions, waste.
- `shopping`: lists, generated requirements, optimistic concurrency, purchases.
- `offers`: provider interface, mock/manual providers, matching and synchronization.
- `budgets`: budgets, price records, cost summaries.
- `notifications`: in-app notifications, preferences, queued email.
- `audit`: append-only security and business audit events.
- `operations`: health, readiness, jobs, feature flags, application settings.

Every household-owned aggregate carries an explicit household foreign key. Service-layer authorization checks membership and permission before query execution, and tests cover cross-household identifiers.

