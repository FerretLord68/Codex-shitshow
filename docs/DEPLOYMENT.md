# Production deployment

## Topology

The application runs in the `mealhouse-prod` LXD container. Nginx listens on container port 80 and LXD publishes host port 80. Gunicorn uses a Unix socket. PostgreSQL binds only inside the container. The worker has no network listener.

Public URL: <https://codex-shitshow.fejlgoblin.ovh>

The external proxy terminates TLS and forwards HTTP to `192.168.1.112:80`. It must set `Host`, `X-Forwarded-Proto`, `X-Forwarded-For`, `X-Forwarded-Host`, and `X-Real-IP`. See `deploy/external-proxy-nginx.example.conf`.

## Trusted proxy requirement

Nginx accepts external forwarding headers only from the observed reverse-proxy source `192.168.0.240/32`, replaces the public host with the canonical production host, and sends sanitized headers to Gunicorn. Django trusts only local Nginx at `127.0.0.1/32`. Update the exact proxy address if the proxy is moved; do not use an internet-wide range.

`APP_URL` is authoritative for verification, reset, invitation, redirect, canonical, and future OAuth URLs. Request headers are never used to construct security-sensitive links.

## Installation inside the container

1. Install Python 3.12, PostgreSQL 16, Nginx, gettext, `libpq-dev`, and image libraries.
2. Place source at `/srv/mealhouse`; keep it root-owned and not writable by `www-data`.
3. Create `/srv/mealhouse/.venv` and install locked dependencies.
4. Store secrets in `/etc/mealhouse/mealhouse.env`, mode `0640`, owner `root:www-data`.
5. Create PostgreSQL role/database with SCRAM authentication and no public listener.
6. Apply migrations and run `seed_reference_data`.
7. Collect static files.
8. Install the systemd units from `deploy/`.
9. Install `deploy/nginx-mealhouse.conf` as the only enabled Nginx site.
10. Add an LXD proxy device:

```bash
lxc config device add mealhouse-prod http proxy listen=tcp:0.0.0.0:80 connect=tcp:127.0.0.1:80
```

No local TLS certificate, Certbot, or port 443 listener is used.

## Service commands

```bash
lxc exec mealhouse-prod -- systemctl status mealhouse-web mealhouse-worker nginx postgresql
lxc exec mealhouse-prod -- systemctl restart mealhouse-web mealhouse-worker
lxc exec mealhouse-prod -- journalctl -u mealhouse-web -u mealhouse-worker
```

## First administrator

Run interactively:

```bash
lxc exec mealhouse-prod -- sudo -u www-data /srv/mealhouse/.venv/bin/python /srv/mealhouse/manage.py create_admin
```

The default address is `frederikjuulolsen@gmail.com`. The command validates and normalizes the address, hides and confirms the password, applies the Django password policy and Argon2id, and uses a transaction. If the account already exists, it requires explicit confirmation before upgrading it. It refuses to run after an administrator exists and writes a sanitized audit event.

## Protected integration values

Edit `/etc/mealhouse/mealhouse.env` as root. Never place real values in the repository:

```bash
sudoedit /etc/mealhouse/mealhouse.env
chown root:www-data /etc/mealhouse/mealhouse.env
chmod 0640 /etc/mealhouse/mealhouse.env
```

Set SMTP and Salling variables documented in `docs/INTEGRATIONS.md`, validate with `manage.py check --deploy`, then restart the web and worker services. Keep the Salling provider disabled until the API token is verified.

## Firewall

Only SSH and port 80 are required on the host. Restrict port 80 to the exact proxy IP when known. Do not modify SSH rules during application deployment. LXD, PostgreSQL, Gunicorn, and worker ports are not published.
