# Offer providers and recipe imports

## Salling Group grocery offers

MealHouse uses the official Salling Group back-end APIs with a server-side bearer token:

- `GET https://api.sallinggroup.com/v1/food-waste/` with `zip`, or `geo` and `radius`.
- `GET https://api.sallinggroup.com/v1/food-waste/{store-id}` for one store.
- `GET https://api.sallinggroup.com/v2/stores` and documented `Link` pagination.

The API reference currently requires portal sign-in for endpoint detail. The implementation was checked against the official portal and its archived May 24, 2025 endpoint reference. The documented API base remains `https://api.sallinggroup.com`, bearer authentication remains accepted, and unauthenticated live requests return `401`.

Configure:

```env
SALLING_GROUP_API_TOKEN=
SALLING_GROUP_API_BASE_URL=https://api.sallinggroup.com
SALLING_GROUP_REQUEST_TIMEOUT_MS=10000
SALLING_GROUP_CACHE_TTL_SECONDS=300
SALLING_GROUP_MAX_RETRIES=2
SALLING_GROUP_IMAGE_HOSTS=dam.dsg.dk
```

The token never reaches the browser. Responses are schema-checked and normalized before persistence. Stores retain source IDs, address, city, postal code, coordinates, and opening hours. Offers retain source IDs, product IDs, prices, discount, stock indicator, validity, image URL, and upstream timestamps. Missing optional values use empty strings or `NULL` consistently.

Successful calls are cached for five minutes by default. A stale cache copy is retained for one hour by default for graceful degradation. Identical in-process requests are coalesced. Authentication and permission failures are never cached. Safe transient failures use bounded retries; `Retry-After` is honored. The documented anti-food-waste quota was 10,000 requests/day, but the portal controls the effective project quota.

Offer images are fetched through an authenticated MealHouse endpoint with an HTTPS hostname allowlist, response-size limit, content-type validation, no redirects, and private caching. Add image hosts only after confirming them in official API responses.

Synchronization runs through the database-backed worker and records a sync run. The Salling provider is seeded disabled with ZIP `8000`; an administrator must change the target area and enable it after installing a token. Historical prices are retained. Automatic name matching stores confidence; low-confidence matches require review.

For local tests, mocked HTTP transports cover success, empty data, pagination, invalid data, missing optional fields, authorization failures, rate limiting, timeout/network/5xx errors, cache behavior, concurrency, normalization, and stale-cache degradation. Tests never call the live API.

Other supported providers:

- Mock provider: synthetic development/test data, disabled in production.
- Manual provider: administrator-reviewed JSON records.

## Recipe import

JSON and Schema.org Recipe imports are previewed before saving. URL import:

- permits only HTTP(S) and standard web ports;
- rejects credentials, loopback, private, link-local, multicast, and metadata addresses;
- revalidates every redirect;
- checks robots.txt;
- uses a descriptive user agent, timeout, response-size limit, and HTML content check;
- imports only JSON-LD Recipe data and preserves source attribution.

It does not bypass login, paywalls, CAPTCHAs, or anti-bot systems.

## SMTP

Production uses authenticated SMTP submission to `mail.taxoz.org`. Preferred configuration is port 587 with STARTTLS; port 465 with implicit TLS is supported by setting `SMTP_SECURE=true`. Certificate validation is mandatory.

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
SMTP_HOST=mail.taxoz.org
SMTP_PORT=587
SMTP_SECURE=false
SMTP_USERNAME=mealhouse
SMTP_PASSWORD=
SMTP_FROM_ADDRESS=mealhouse@taxoz.org
SMTP_FROM_NAME=MealHouse
SMTP_CONNECTION_TIMEOUT_MS=10000
SMTP_SEND_TIMEOUT_MS=15000
```

Email is queued and delivered by the worker in plain-text and HTML forms. Temporary failures are retried with bounded exponential backoff; permanent SMTP rejections are marked dead. Logs include template/job identity but never recipient addresses, message bodies, credentials, or tokens.

Verify without sending:

```bash
sudo -u www-data /srv/mealhouse/.venv/bin/python /srv/mealhouse/manage.py verify_smtp
```

Add `--send --recipient you@example.test` to send a test message. As of June 20, 2026, ports 587 and 465 were reachable but the server presented a self-signed certificate. Correct the mail-server certificate before enabling SMTP; do not disable verification.
