# MealHouse Codex progress

Last updated: 2026-06-20 UTC

## Current objective

Finish and production-harden MealHouse, including SMTP, Salling Group, administrator bootstrap, security, deployment, tests, documentation, Git commits, and GitHub push.

## Architecture discovered

- Django 5.2 modular monolith with server-rendered templates.
- PostgreSQL 16 in the `mealhouse-prod` unprivileged LXD container.
- Gunicorn on container loopback port 8000 behind Nginx on container port 80.
- Host LXD proxy/NAT publishes `192.168.1.112:80` to `10.241.159.210:80`.
- External reverse proxy at the documented `192.168.0.240` terminates TLS.
- Database-backed worker, scheduler timer, and nightly backup timer managed by systemd.

## Completed work

- Confirmed repository path, clean worktree, branch, remote, and history.
- Confirmed no repository-scoped `AGENTS.md` exists.
- Fetched and pruned the Git remote.
- Inspected core settings, accounts, offers, tests, documentation, deployment files, services, logs, ports, firewall, migrations, backups, and production database counts.
- Confirmed production migrations are current and `manage.py check --deploy` passes with three documented silenced checks.
- Confirmed one production user and no production administrator.
- Confirmed SMTP ports 25, 465, and 587 are reachable.
- Confirmed SMTP TLS currently uses a self-signed certificate, which fails normal certificate verification.
- Confirmed two recent local backups exist with mode `0600`.
- Installed host test prerequisites and the locked Python dependencies.
- Baseline Ruff, Python dependency audit, and Node dependency audit pass.
- Created the existing disposable `mealhouse_test` database with the application role as owner, without granting `CREATEDB`.
- Baseline suite passes: 25 tests.
- Added strict typed runtime configuration for SMTP and Salling Group.
- Added reusable multipart SMTP delivery, sanitized transient/permanent error handling, and `verify_smtp`.
- Added password-change and password-reset-completion security notifications.
- Added a dedicated Salling Group client with bearer authentication, timeouts, bounded retries, `Retry-After`, pagination, response validation, normalized data, caching, request coalescing, and stale-cache degradation.
- Added normalized Salling store/offer fields and migrations.
- Added an allowlisted, size-limited, content-validated offer image proxy.
- Added offer search, chain filtering, pagination, improved cards, and empty state.
- Added interactive `create_admin` command with the requested default email and safe existing-user upgrade.
- Fixed active sessions so suspended users immediately lose access.
- Expanded integration and deployment documentation.
- Current feature/security suite passes: 40 tests.
- Final current suite passes: 42 tests.
- Live Playwright/axe checks pass on landing, login, registration, password reset, and privacy pages: 5 passed.
- Created production backup `/var/lib/mealhouse/backups/20260620T175215Z`.
- Created LXD rollback snapshot `mealhouse-prod/pre-91ac425-20260620`.
- Deployed commit `91ac425`, applied both new migrations, seeded the disabled Salling provider, collected 129 static files, and verified public HTTP/HTTPS plus readiness.
- Hardened web/worker systemd services from exposure scores 6.2/6.3 (medium) to 2.8 (OK).
- Enabled persistent host UFW with SSH, proxy HTTP, LXD DNS/DHCP, and LXD outbound rules.

## Current work in progress

- Reviewing the first implementation checkpoint before commit.
- Applying operating-system updates, completing final documentation/checks, and preparing reboot verification.

## Remaining work

- Obtain SMTP password securely and configure production.
- Confirm final sender address.
- Obtain Salling Group API token securely and verify production.
- Create/upgrade the first administrator interactively.
- Complete security, performance, UX, accessibility, dependency, and secret-history audits.
- Add migrations/indexes where required, after a fresh backup.
- Synchronize production checkout safely.
- Validate/harden Nginx and systemd.
- Configure and verify persistent host firewall without breaking SSH/LXD port 80.
- Run full tests, build/checks, deployment verification, commit, push, and remote verification.
- Perform controlled reboot verification if safe and useful.

## Owner questions

- What authorized `taxoz.org` sender address should MealHouse use? Reversible default recommendation: `mealhouse@taxoz.org`.
- SMTP password is absent from protected runtime configuration and must be entered securely on the server; the previously shared value requires rotation.
- Salling Group API token is absent from protected runtime configuration and must be entered securely on the server.

## Assumptions made

- Canonical production URL remains `https://codex-shitshow.fejlgoblin.ovh`.
- External proxy source remains `192.168.0.240` unless live verification shows otherwise.
- SMTP must retain strict certificate verification in production; the mail server certificate should be corrected rather than disabling verification.
- The current production user and data must be preserved.

## Tests already run

- `git fetch --all --prune`: passed.
- Production `manage.py check --deploy`: passed with three intentional silenced checks.
- Production `manage.py showmigrations`: all migrations applied.
- Production `manage.py migrate --plan`: no pending operations.
- Nginx configuration test: passed.
- HTTP request to `192.168.1.112` with canonical host: `200 OK`.
- SMTP TCP connectivity: ports 25, 465, and 587 reachable.
- SMTP STARTTLS/implicit TLS: negotiation succeeds, certificate verification fails because the presented certificate is self-signed.

## Tests still required

- Ruff, pytest unit/integration suite, Playwright/axe accessibility suite.
- Django checks, migration consistency, production build/static collection.
- Python and Node dependency audits.
- SMTP authentication and optional delivery.
- Salling API live authentication and production integration.
- Post-deployment health/readiness and logs.
- Firewall persistence/connectivity and post-reboot recovery.

## Deployment state

- Production is live and returns HTTP 200 through the host LAN address.
- Container services Nginx, PostgreSQL, `mealhouse-web`, `mealhouse-worker`, scheduler timer, and backup timer are active.
- Production source under `/srv/mealhouse` contains deployed files not represented in its local Git index; deployment synchronization must preserve data and be corrected carefully.

## System files changed

- Host UFW configuration under `/etc/ufw`; backup at `/var/backups/mealhouse-firewall/20260620T1757Z`.
- Container systemd units: `/etc/systemd/system/mealhouse-{web,worker,scheduler}.service`.
- Container Nginx site: `/etc/nginx/sites-available/mealhouse`.
- Container configuration backup: `/var/lib/mealhouse/config-backups/20260620T1802Z`.

## Service changes

- Web and worker restarted successfully after deployment and hardening.
- Nginx reloaded after validated timeout configuration.
- Scheduler and backup timers remain enabled.

## Firewall state

- Host UFW active and enabled.
- Container UFW inactive.
- LXD-managed nftables rules continue to provide forwarding/NAT for the container and host port 80.
- SSH listens on host TCP 22 over IPv4 and IPv6.

## Database migrations

- Existing initial migrations are fully applied.
- Added and applied `catalog.0002_store_location_fields` and `offers.0002_salling_offer_fields` successfully in production.

## Git commits created

- `91ac425 feat: add secure mail and Salling integrations`

## Last known good state

- Commit `06c01b5` on `codex/production-mealhouse`.
- Production HTTP responds successfully.
- Application, worker, database, Nginx, scheduler, and backup timer active.
- Backup `20260620T022409Z` exists under `/var/lib/mealhouse/backups` in the container.

## Exact next steps

1. Commit systemd, Nginx, firewall documentation, and updated progress.
2. Apply available host/container operating-system updates.
3. Run full final checks and push the branch.
4. Reboot and verify UFW, LXD, Nginx, PostgreSQL, web, worker, timers, HTTP, DNS, and outbound connectivity.
5. Obtain protected owner credentials, verify SMTP/Salling, and bootstrap the administrator.
