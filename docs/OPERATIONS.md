# Operations and recovery

## Health

- Public, non-sensitive: `http://127.0.0.1/ops/health/`
- Detailed readiness: `/ops/readiness/`, deliberately available only from loopback
- Administrative job status: `/ops/jobs/`

Readiness checks PostgreSQL and the recent worker heartbeat. Provider synchronization status is visible in administration.

## Backup

Manual:

```bash
lxc exec mealhouse-prod -- /srv/mealhouse/scripts/backup.sh
```

Nightly backups are created by `mealhouse-backup.timer` under `/var/lib/mealhouse/backups`. They contain a compressed PostgreSQL dump, private uploads, the private recovery environment, and checksums. Copy backups to encrypted off-host storage with access logging. A reasonable baseline is 14 daily, 8 weekly, and 12 monthly copies.

## Restore

Restore into an empty non-production instance first:

```bash
lxc exec mealhouse-prod -- systemctl stop mealhouse-web mealhouse-worker
lxc exec mealhouse-prod -- /srv/mealhouse/scripts/restore.sh /var/lib/mealhouse/backups/TIMESTAMP
lxc exec mealhouse-prod -- systemctl start mealhouse-worker mealhouse-web
```

Verify checksums, `manage.py check`, migration status, row counts, a login, an image, and a generated shopping list. The restore script uses `pg_restore --exit-on-error` and verifies archive checksums before changing data.

## Update

1. Create an LXD snapshot and database backup.
2. Review dependency and migration changes.
3. Run the full tests on the target revision.
4. Run `scripts/update.sh origin/main`.
5. Verify health, worker heartbeat, login, and logs.

## Rollback

`scripts/rollback.sh COMMIT` restores application code and dependencies. Database rollback is not automatic because reverse migrations can destroy data. Restore the pre-update backup when a schema change cannot be safely reversed.

## Logging

Application logs are structured JSON in the system journal. Tokens, passwords, request bodies, and sensitive dietary information are excluded. Use request IDs to correlate Nginx and application events.

## Host firewall

The host uses persistent UFW rules with default deny for incoming and routed traffic and default allow for host outbound traffic:

- TCP 22 from IPv4/IPv6 for SSH.
- TCP 80 from the external proxy `192.168.0.240`.
- Routed TCP 80 from that proxy to the LXD container `10.241.159.210`.
- LXD bridge DNS (TCP/UDP 53) and DHCP (UDP 67).
- Routed outbound traffic from `10.241.159.0/24` through `ens18`; established return traffic is statefully allowed.

Verify:

```bash
sudo ufw status verbose
ss -tnlp
curl -I https://codex-shitshow.fejlgoblin.ovh/
lxc exec mealhouse-prod -- getent ahosts api.sallinggroup.com
```

The pre-change UFW archive and firewall dumps are under `/var/backups/mealhouse-firewall/20260620T1757Z` on the host. Emergency rollback:

```bash
sudo ufw disable
sudo tar -C / -xzf /var/backups/mealhouse-firewall/20260620T1757Z/etc-ufw.tar.gz
sudo ufw --force enable
```

The final `enable` restores the previous saved UFW state, which was inactive. If remote access is uncertain, use console access or arm a timed rollback before changing rules:

```bash
sudo systemd-run --unit=mealhouse-firewall-rollback --on-active=2m \
  /usr/sbin/ufw --force disable
```
