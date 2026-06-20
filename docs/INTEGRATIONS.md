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

Verify stores authentication:

```bash
sudo -u www-data /srv/mealhouse/.venv/bin/python /srv/mealhouse/manage.py verify_salling
```

Add `--zip 8000` (or the configured target ZIP) to verify Anti Food Waste access and normalization too. Output contains counts and error classes only, never tokens or upstream response bodies.

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

Production uses authenticated SMTP submission to `mail.taxoz.org` on port 587
with STARTTLS. Port 465 with implicit TLS is supported by setting
`SMTP_SECURE=true`. Certificate validation is mandatory.

```env
EMAIL_BACKEND=notifications.backends.smtp.EmailBackend
SMTP_HOST=mail.taxoz.org
SMTP_PORT=587
SMTP_SECURE=false
SMTP_USERNAME=mealhouse@taxoz.org
SMTP_PASSWORD=
SMTP_FROM_ADDRESS=mealhouse@taxoz.org
SMTP_FROM_NAME=MealHouse
SMTP_CONNECTION_TIMEOUT_MS=10000
SMTP_SEND_TIMEOUT_MS=15000
SMTP_CA_FILE=/etc/mealhouse/certs/mail.taxoz.org.pem
SMTP_CERT_FINGERPRINT=
```

Email is queued and delivered by the worker in plain-text and HTML forms. Temporary failures are retried with bounded exponential backoff; permanent SMTP rejections are marked dead. Logs include template/job identity but never recipient addresses, message bodies, credentials, or tokens.

### Host-specific certificate trust

As verified on June 20, 2026, ports 25, 587, and 465 present the same
self-signed certificate:

- Subject and issuer: `CN=mail.taxoz.org, OU=mailcow, O=mailcow, L=Willich, ST=NRW, C=DE`
- Serial: `1CA60BEF3469FEDE7FC5C4F58094BFC151ED2E3B`
- Validity: February 1, 2026 through February 1, 2027
- Certificate SHA-256: `cbc123713718f2414a489a51d6f4c9197e81305ad92d38824150aff724c557c3`
- SPKI SHA-256: `3f6efd1f1c5ed449e699f2cd76bcb85d73f088063d2492eeb1b15d1a98d83777`

The SPKI matches the value supplied by the mail owner. DNSSEC validation for
`taxoz.org` succeeds, but currently proves an authenticated `NXDOMAIN` for
`_25._tcp.mail.taxoz.org`; the supplied TLSA record is not currently published.
It is therefore treated as out-of-band owner evidence rather than live DANE
evidence.

The exact certificate is installed at
`/etc/mealhouse/certs/mail.taxoz.org.pem`. The custom backend loads it into a
dedicated SSL context used only for MealHouse SMTP. Certificate signature,
validity, and hostname checks remain enabled. The backend refuses to apply this
trust file to another hostname; global HTTPS and system trust are unchanged.

Before February 1, 2027, obtain the replacement certificate or SPKI through a
trusted owner channel, compare it with every enabled SMTP port, replace the PEM
atomically, run `manage.py verify_smtp`, and restart the web and worker
services. A changed or expired certificate fails closed.

Verify without sending:

```bash
sudo -u www-data /srv/mealhouse/.venv/bin/python /srv/mealhouse/manage.py verify_smtp
```

Add `--send --recipient you@example.test` to send a test message.

The mail server requires the full mailbox address as the SMTP login. The short
name `mealhouse` is rejected even when the password is correct.
