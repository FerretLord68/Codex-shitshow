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

- Continuation from commit `6538b07`:
  - Confirmed the completed owner environment was on the host while the
    container still had the prior environment.
  - Restricted `/etc/mealhouse/mealhouse.env` from `0644` to `0600` and saved a
    root-only backup before normalization.
  - Corrected sender values entered as Markdown links and added the exact
    timeout/TLS variable names read by Django.
  - Inspected SMTP ports 25/587/465. All are reachable and present the same
    self-signed certificate and RSA-4096 key. Ports 587 and 465 advertise
    authenticated submission after TLS; port 25 does not advertise AUTH.
  - Verified certificate SHA-256
    `cbc123713718f2414a489a51d6f4c9197e81305ad92d38824150aff724c557c3`
    and SPKI SHA-256
    `3f6efd1f1c5ed449e699f2cd76bcb85d73f088063d2492eeb1b15d1a98d83777`.
  - Verified the SPKI matches the value supplied by the SMTP owner.
  - Verified DNSSEC for `taxoz.org`; validating resolvers return signed,
    authenticated `NXDOMAIN` for `_25._tcp.mail.taxoz.org`, so the supplied
    TLSA is not currently published.
  - Installed the validated leaf certificate on the host at
    `/etc/mealhouse/certs/mail.taxoz.org.pem`.
  - Added a connection-local SMTP backend that trusts the exact certificate
    only for `mail.taxoz.org`; hostname and expiry validation remain enabled.

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
- Final current suite passes: 43 tests.
- Live Playwright/axe checks pass on landing, login, registration, password reset, and privacy pages: 5 passed.
- Created production backup `/var/lib/mealhouse/backups/20260620T175215Z`.
- Created LXD rollback snapshot `mealhouse-prod/pre-91ac425-20260620`.
- Deployed commit `91ac425`, applied both new migrations, seeded the disabled Salling provider, collected 129 static files, and verified public HTTP/HTTPS plus readiness.
- Hardened web/worker systemd services from exposure scores 6.2/6.3 (medium) to 2.8 (OK).
- Enabled persistent host UFW with SSH, proxy HTTP, LXD DNS/DHCP, and LXD outbound rules.
- Applied all available standard Ubuntu updates on host and container, including the phased fwupd upgrade; no packages remain pending.
- Validated the fresh backup checksums plus PostgreSQL and media archive readability.
- Pushed commits `91ac425`, `0197902`, and `8b809d4` to `origin/codex/production-mealhouse`.
- Synchronized the clean production checkout to exact commit `8b809d4821f67a202663bea0270e91af6539fbce`.
- First reboot audit found and corrected two persistence defects: DHCP broadcast was not covered by the original UFW destination-specific rule, and `br_netfilter` was not loaded before LXD. The container recovered with its reserved IP, public HTTP/HTTPS returned 200, readiness passed, and DNS/HTTPS/SMTP egress passed.
- Second controlled reboot verified the fixes persist from boot: zero failed units on host/container; UFW active; `br_netfilter` and bridge sysctls loaded; container received `10.241.159.210`; Nginx, PostgreSQL, web, worker, scheduler, and backup timer active/enabled; readiness healthy; host/public HTTP 200; Salling DNS/HTTPS reachable; SMTP 587 reachable.
- Added sanitized `verify_salling` command for stores authentication and optional Anti Food Waste verification.

## Current work in progress

- Deploying the SMTP trust backend and completed environment, then verifying
  SMTP delivery, Salling, and administrator creation.

## Remaining work

- Deploy the protected environment and SMTP certificate to the container.
- Verify SMTP authentication, test delivery, and password-reset delivery.
- Verify Salling for postal code 9000 and provider synchronization.
- Create or promote the first administrator and verify role preservation.
- Run the complete final validation matrix.
- Push the working branch, merge to `main`, verify, and push `main`.

## Owner questions

- None currently. The sender, SMTP credentials, Salling token and target postal
  code are configured, and administrator creation is authorized.

## Assumptions made

- Canonical production URL remains `https://codex-shitshow.fejlgoblin.ovh`.
- External proxy source remains `192.168.0.240` unless live verification shows otherwise.
- SMTP uses a dedicated exact-certificate trust context restricted to
  `mail.taxoz.org`; global TLS validation remains unchanged.
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
- Ruff: passed.
- Pytest: 43 passed.
- Playwright/axe live accessibility suite: 5 passed.
- Python dependency audit: no known vulnerabilities.
- Node dependency audit: no vulnerabilities.
- Backup checksum/archive validation: passed.

## Tests still required

- SMTP authentication and optional delivery.
- Salling API live authentication and production integration.

## Deployment state

- Production is live and returns HTTP 200 through the host LAN address.
- Container services Nginx, PostgreSQL, `mealhouse-web`, `mealhouse-worker`, scheduler timer, and backup timer are active.
- Production source under `/srv/mealhouse` is a clean Git checkout at `6ffefd1`.

## System files changed

- Host UFW configuration under `/etc/ufw`; backup at `/var/backups/mealhouse-firewall/20260620T1757Z`.
- Host module/sysctl configuration: `/etc/modules-load.d/mealhouse-lxd.conf` and `/etc/sysctl.d/99-mealhouse-lxd-bridge.conf`.
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
- `0197902 chore: harden production services and firewall docs`
- `8b809d4 fix: improve provider reliability and record audit`
- `89776f9 docs: record pre-reboot production state`
- `6ffefd1 fix: persist LXD networking across reboot`

## Last known good state

- Commit `6ffefd1` on `codex/production-mealhouse` is deployed and verified across reboot.
- Production HTTP responds successfully.
- Application, worker, database, Nginx, scheduler, and backup timer active.
- Backup `20260620T175215Z` and snapshot `pre-91ac425-20260620` are verified.

## Exact next steps

1. Commit and deploy the SMTP trust backend.
2. Synchronize the protected environment and certificate to the container.
3. Verify SMTP, Salling, database, migrations, and administrator workflows.
4. Run final checks, push the branch, merge to `main`, and verify remote `main`.
