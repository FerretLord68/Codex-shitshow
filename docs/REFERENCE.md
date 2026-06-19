# Technical reference

## Database

PostgreSQL stores normalized users, sessions, security tokens, households, memberships, profiles, attendance, ingredients, aliases, units, nutrition, stores, products, recipes, meal plans, participants, inventory, transactions, waste, shopping lists/events, providers, offers, matches, prices, budgets, notifications, jobs, feature flags, settings, support access, and audit events.

Household aggregates carry a required household foreign key. Foreign keys, uniqueness, checks, indexes, explicit deletion rules, transactions, and service authorization reinforce tenant isolation.

## Internal HTTP API

The current internal API is session-authenticated and CSRF protected:

- `GET /ops/health/` — public non-sensitive liveness.
- `GET /ops/readiness/` — loopback-only detailed readiness.
- `POST /shopping/items/{id}/toggle/` — optimistic-concurrency item update; returns `409` on stale version.
- standard HTML form endpoints return validation errors without implementation details.

Pagination defaults to 100–300 records on administrative/list views. Search queries use bounded database filters. Expensive generation, synchronization, import, and export operations are rate-limited or queued.

## Environment variables

See `.env.example`. Production requires `ENVIRONMENT=production`, `DEBUG=false`, `SECRET_KEY`, `APP_URL`, allowed hosts, exact trusted proxies, and PostgreSQL credentials. SMTP and live offer settings are optional and disabled safely by default.

