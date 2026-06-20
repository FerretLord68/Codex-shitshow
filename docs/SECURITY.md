# Security overview and threat model

## Assets

- Account credentials and active sessions.
- Household membership and authorization.
- Private meal plans, inventory, shopping lists, budgets, dietary preferences, allergies, and nutrition targets.
- Offer-provider configuration.
- Uploaded recipe images.
- Audit evidence and recovery secrets.

## Trust boundaries and attacker types

Trust boundaries exist between the public internet and external proxy, proxy and application host, Nginx and Gunicorn, application and PostgreSQL, background jobs and providers, households, administrators and support access, and uploaded/untrusted content.

Attackers include unauthenticated internet clients, credential-stuffing actors, malicious household members, compromised user accounts, malicious import sources, a compromised grocery provider, and an administrator exceeding assigned duties.

## Entry points

Authentication forms, household invitations, all object identifiers, recipe import URLs and JSON, image uploads, shopping concurrency endpoints, offer imports, administration, proxy headers, and background jobs.

## Controls

- Argon2id password hashing and Django password validation.
- Hashed, random, expiring, single-use reset, verification, and invitation tokens.
- Session rotation, revocation, Secure/HttpOnly/SameSite cookies, CSRF protection, and account backoff.
- Server-side household authorization and cross-tenant tests.
- Parameterized ORM queries, transactions, constraints, optimistic concurrency, and nonnegative inventory checks.
- Trusted-proxy CIDRs; forwarding headers from untrusted peers are removed.
- `APP_URL` for security-sensitive absolute links.
- CSP, clickjacking denial, MIME sniff prevention, restrictive referrer and permissions policies.
- Nginx and Django request limits and endpoint rate limits.
- SSRF controls requiring HTTP(S), global DNS addresses, allowed ports, redirect revalidation, robots permission, timeouts, and response limits.
- No automatic live offer scraper without documented authorization.
- Upload ownership, randomized names, size/signature checks, raster re-encoding, and private storage.
- Append-only application audit events and explicit time-limited support access records.
- Least-privilege PostgreSQL role and hardened systemd services.
- Persistent host UFW policy permitting only SSH and proxy-originated MealHouse HTTP ingress.
- Production debug guard and generic error pages.

## Remaining risks

- The external proxy and its TLS/firewall configuration are outside this host.
- SSH password authentication remains enabled because key-only access has not been independently verified; migrate to tested key-only access before disabling it.
- E-mail spool mode is operationally safe but does not deliver messages until SMTP is configured.
- Nutrition, price, and unit-conversion source quality varies.
- Python process isolation is not a substitute for host patching.
- Application-level append-only audit controls do not prevent a database superuser from altering records; export logs to immutable storage for stronger assurance.
- CSP currently permits no third-party sources; future integrations require explicit review.

## Security response

Revoke sessions, disable compromised accounts/providers, preserve minimized logs, rotate secrets, patch dependencies, and document scope. Never include raw tokens or household health data in incident tickets.
