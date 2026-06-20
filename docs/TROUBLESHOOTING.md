# Troubleshooting and known limitations

## Common checks

```bash
lxc list
lxc exec mealhouse-prod -- systemctl --failed
lxc exec mealhouse-prod -- systemctl status nginx postgresql mealhouse-web mealhouse-worker
lxc exec mealhouse-prod -- journalctl -u mealhouse-web -n 100 --no-pager
curl -i http://127.0.0.1/ops/health/
```

If public links use the wrong host, verify `APP_URL`. If client IPs or HTTPS detection are wrong, verify the proxy source address and `TRUSTED_PROXY_CIDRS`; never broaden it to the internet.

## Known limitations

- SMTP cannot be enabled until the mail server presents a certificate trusted by the system CA store and a rotated password/sender are installed.
- The Salling Group provider remains disabled until a protected API token is installed and its target ZIP/geolocation is confirmed.
- Nutrition and prices require curated source data for complete totals.
- Public recipes are schema-ready but public publishing is disabled by default.
- Two-factor schema and feature flag architecture exist, but enrollment is disabled until a reviewed TOTP/WebAuthn flow is added.
- Travel-distance optimization and external AI recommendations are future extensions.
- The external proxy, public firewall path, and TLS certificate are managed outside this server.

## Integration diagnostics

```bash
sudo -u www-data /srv/mealhouse/.venv/bin/python manage.py verify_smtp
sudo -u www-data /srv/mealhouse/.venv/bin/python manage.py shell -c \
  'from offers.salling import SallingClient; print(len(SallingClient().stores(country="dk").items))'
```

`SSLCertVerificationError` from SMTP means the server certificate chain must be fixed. Do not set an unverified SSL context. `SallingAuthenticationError` means the token is absent, invalid, not propagated yet, or lacks the selected API.
