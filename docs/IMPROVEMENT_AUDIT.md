# MealHouse improvement audit

Date: 2026-06-20

## Critical

- **Email delivery trust:** SMTP submission uses a self-signed certificate. The
  exact certificate was validated against the owner-provided SPKI and is trusted
  only by MealHouse's dedicated SMTP context. Hostname and expiry checks remain
  enabled. Authentication, a test message, and a password-reset message are
  verified using the required full mailbox login.
- **Host ingress policy:** the host previously had no active firewall. Persistent UFW now denies unsolicited input/routing and permits SSH, the known proxy-to-MealHouse HTTP path, required LXD DNS/DHCP, and container egress.
- **Administrator ownership:** the requested existing user was transactionally
  promoted without duplication. A strong random temporary password is stored
  in a root-only local file, and password-reset role preservation is tested.

## High value completed

### Product functionality and UX

- Added official Salling Group anti-food-waste and stores clients, normalized store/offer data, graceful stale-cache fallback, and disabled-by-default provider seeding.
- Added offer search, chain filtering, 48-item pagination, price/discount/expiry display, image handling, and a useful empty state.
- Added plain-text and HTML verification, reset, invitation, password-change, and reset-completion messages.

### Accessibility

- Preserved semantic headings, labels, keyboard focus, skip navigation, responsive navigation, and reduced-motion behavior.
- Live axe checks report no serious/critical WCAG 2/2.1 A/AA findings on five public account/legal journeys.

### Architecture and maintainability

- Isolated SMTP delivery and Salling communication behind dedicated services.
- Added typed environment parsing and production validation.
- Moved external Salling network waits outside database transactions; normalized persistence remains atomic.
- Added migrations for stable provider identifiers, locations, opening hours, discounts, stock indicators, and timestamps.

### Reliability and performance

- Added external request timeouts, bounded retries, `Retry-After`, safe error classes, cache keys, stale fallback, and in-process request coalescing.
- Added permanent-versus-temporary SMTP handling and sanitized background-job failures.
- Added database pagination for offers and lazy image loading.
- Added a strict offer-image proxy with HTTPS host allowlisting, no redirects, content-type/size validation, and caching.

### Security

- Suspended users now lose existing sessions immediately.
- Public registration/profile forms cannot assign roles; admin endpoints remain server-side staff protected.
- Integration credentials remain backend-only and are redacted from logs/errors.
- PostgreSQL remains loopback-only with SCRAM and a non-superuser/non-`CREATEDB` application role.
- systemd web/worker exposure scores improved from medium (6.2/6.3) to OK (2.8).
- Python and Node dependency audits report no known vulnerabilities.

### Operations and documentation

- Added recoverable deployment with a fresh database/media/config backup and LXD snapshot.
- Validated backup checksums, PostgreSQL archive readability, and media archive readability.
- Documented SMTP, Salling, administrator bootstrap, firewall policy/rollback, test database setup, and session recovery.
- Applied current Ubuntu package updates on host and container.

## Medium value remaining

- Add authenticated browser tests for household, recipe, inventory, planning, shopping, offers, and administrator workflows.
- Replace the in-process Salling cache with a shared cache if web-facing live queries or multiple workers begin using it heavily.
- Add off-host encrypted backup replication and periodic automated restore drills.
- Add metrics/alerting for readiness failures, dead jobs, email failures, provider failures, backup age, disk usage, and certificate expiry.
- Add database query profiling with production-like data and optimize ingredient matching if provider volume grows.
- Add explicit data-retention periods after the owner supplies policy decisions.

## Optional

- Reviewed TOTP/WebAuthn enrollment.
- Public recipe sharing with explicit privacy controls.
- Travel-distance shopping optimization.
- Immutable external audit-log export.
- Additional branding assets and installable PWA support.

## Owner decisions required

- Anti Food Waste permission for the Salling token; Stores access succeeds.
- Data-retention policy and legal contact wording.
- Whether SSH password authentication may be disabled after key-only access is independently tested.
