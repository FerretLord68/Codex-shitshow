# Implementation plan

## Host findings

- Ubuntu 24.04.2 LTS, Linux 6.8, x86-64.
- 2 vCPU, 3.8 GiB RAM, 3.8 GiB swap, approximately 39 GiB free disk.
- Host address `192.168.1.112/24`; default gateway `192.168.1.1`.
- Public DNS resolves `codex-shitshow.fejlgoblin.ovh` to `185.181.220.193`, consistent with a separate reverse proxy.
- SSH is the only TCP listener. Port 80 is unused.
- No existing Nginx, Apache, Caddy, PostgreSQL, Redis, Docker, Podman, or hosted project was found.
- UFW/nftables rules require root access to inspect. Non-interactive sudo is unavailable.
- The account belongs to the `lxd` group. The Ubuntu LXD installer was triggered during inspection and installed LXD 5.21.

## Delivery stages

1. Provision an isolated Ubuntu 24.04 LXD application container.
2. Build the Django/PostgreSQL modular monolith and database migrations.
3. Implement authentication, household tenancy, recipes, planning, inventory, shopping, offers, budgets, waste, notifications, and administration.
4. Build responsive server-rendered Danish/English interfaces.
5. Add security controls, tests, accessibility checks, operational scripts, and complete documentation.
6. Deploy with Gunicorn, Nginx, PostgreSQL, and systemd services inside the container.
7. Publish only host port 80 through an LXD proxy device.
8. Verify local, proxy, public HTTPS, backup/restore, and restart behavior.

## Assumptions

- The external reverse proxy is managed separately and can reach `192.168.1.112:80`.
- The external proxy's preserved source address was verified as `192.168.0.240`; Nginx trusts forwarding headers only from that address.
- SMTP credentials are unavailable. Email is queued and safely captured to a production spool until SMTP is configured.
- No grocery-offer source URL was supplied. Live scraping is disabled; mock and validated manual JSON/CSV providers are implemented.
- Nutrition and prices are estimates and are never medical advice.
