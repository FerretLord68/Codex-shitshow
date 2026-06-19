# Offer providers and recipe imports

## Grocery offers

Provider adapters implement a small `fetch()` interface and return validated normalized records. Supported initial providers:

- Mock provider: synthetic development/test data, disabled in production.
- Manual provider: administrator-reviewed JSON/CSV-compatible records.

No live provider is enabled because `OFFER_SOURCE_URL` and permission evidence were not supplied. Before adding one, document the official API/feed, terms, robots policy, authentication, rate limits, attribution, and copyright restrictions. Do not bypass access controls.

Synchronization runs through the database-backed worker with retries and records a sync run. Historical prices are retained. Automatic name matching stores confidence; low-confidence matches require review.

## Recipe import

JSON and Schema.org Recipe imports are previewed before saving. URL import:

- permits only HTTP(S) and standard web ports;
- rejects credentials, loopback, private, link-local, multicast, and metadata addresses;
- revalidates every redirect;
- checks robots.txt;
- uses a descriptive user agent, timeout, response-size limit, and HTML content check;
- imports only JSON-LD Recipe data and preserves source attribution.

It does not bypass login, paywalls, CAPTCHAs, or anti-bot systems.

