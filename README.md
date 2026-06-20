# MealHouse

MealHouse is a bilingual (Danish/English) household meal-planning application covering recipes, nutrition, inventory, shopping, grocery offers, budgets, and food-waste tracking.

Production URL: <https://codex-shitshow.fejlgoblin.ovh>

The implementation is a modular Django monolith backed by PostgreSQL. A background worker and scheduler use the database-backed Django Tasks framework. Nginx serves the application on port 80 inside an isolated LXD container; the external reverse proxy terminates TLS.

## Documentation

- [Architecture and technology decisions](docs/ARCHITECTURE.md)
- [Implementation plan and assumptions](docs/IMPLEMENTATION_PLAN.md)
- [Local development and testing](docs/DEVELOPMENT.md)
- [Production deployment and reverse proxy](docs/DEPLOYMENT.md)
- [Operations, backup, restore, update, and rollback](docs/OPERATIONS.md)
- [Security overview and threat model](docs/SECURITY.md)
- [Privacy and data-processing overview](docs/PRIVACY.md)
- [User and administrator guide](docs/USER_GUIDE.md)
- [Offer providers and recipe imports](docs/INTEGRATIONS.md)
- [Database and API overview](docs/REFERENCE.md)
- [Troubleshooting and known limitations](docs/TROUBLESHOOTING.md)
- [Improvement audit and prioritized backlog](docs/IMPROVEMENT_AUDIT.md)

## Quick local test

```bash
pytest --reuse-db
```

The production service exposes only HTTP port 80 to the separate TLS-terminating reverse proxy. PostgreSQL and worker services remain private.

Operational setup for SMTP, Salling Group, administrator bootstrap, firewall, backups, and deployment is documented under `docs/`. Current multi-session implementation state and exact recovery steps are tracked in `docs/CODEX_PROGRESS.md`.
