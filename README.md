# MealHouse

MealHouse is a bilingual (Danish/English) household meal-planning application covering recipes, nutrition, inventory, shopping, grocery offers, budgets, and food-waste tracking.

Production URL: <https://codex-shitshow.fejlgoblin.ovh>

The implementation is a modular Django monolith backed by PostgreSQL. A background worker and scheduler use the database-backed Django Tasks framework. Nginx serves the application on port 80 inside an isolated LXD container; the external reverse proxy terminates TLS.

## Status

Implementation is in progress. See [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

