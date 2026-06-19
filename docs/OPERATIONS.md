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

