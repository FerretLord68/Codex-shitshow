# Privacy and data processing

MealHouse applies data minimization and privacy-friendly defaults. It has no advertising trackers or third-party analytics.

## Data purposes

- Account data: authentication, security notices, and preferences.
- Household data: shared planning, recipes, inventory, shopping, budgets, and waste reduction.
- Optional dietary and nutrition data: user-requested estimates and filtering.
- Security metadata: abuse prevention, auditability, and session management.

## Rights procedures

Users can download a structured account export from account settings. A deletion request revokes sessions, removes access, and anonymizes the user identity. The final household owner must transfer ownership or delete the household first.

Household deletion must be confirmed by an owner, exported when requested, transactionally cascade private aggregates, and retain only minimized audit evidence needed for integrity or legal obligations.

## Retention

Security tokens expire quickly and are retained only as hashes. Sessions are revoked on password reset/deletion. Offer price history is retained for comparisons and auditability. Audit events are minimized and may outlive account anonymization. Backups expire according to the documented retention schedule.

The operator must add controller identity, contact details, legal basis, processor list, transfer information, and jurisdiction-specific retention periods before production user onboarding.

