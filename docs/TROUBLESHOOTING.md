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

- SMTP is not configured; messages spool locally until credentials are supplied.
- No live grocery provider can be enabled without a source URL and permission review.
- Nutrition and prices require curated source data for complete totals.
- Public recipes are schema-ready but public publishing is disabled by default.
- Two-factor schema and feature flag architecture exist, but enrollment is disabled until a reviewed TOTP/WebAuthn flow is added.
- Travel-distance optimization and external AI recommendations are future extensions.
- The external proxy, public firewall path, and TLS certificate are managed outside this server.

