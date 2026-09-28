# PCC Education (Frappe Education on the VPS)

Frappe v16 + ERPNext + HRMS + Education + LMS for Philippine Coding Camp, running on the
Hostinger VPS `srv1586246.hstgr.cloud` (187.127.110.227).

- **Site:** https://portal.srv1586246.hstgr.cloud
- **Desk (staff):** https://portal.srv1586246.hstgr.cloud/desk (old `/app` links redirect there)
- **LMS (online courses):** https://portal.srv1586246.hstgr.cloud/lms
- **Student/guardian portal:** https://portal.srv1586246.hstgr.cloud/edu-portal
- **Admissions page:** https://portal.srv1586246.hstgr.cloud/admissions (currently broken upstream, see [Known issues](#known-issues))
- **Deployed:** 28 Sep 2026 (image `16-build1`: Frappe 16.35.0, ERPNext 16.36.0, HRMS 16.20.0, Education 16.0.1)
- **LMS added:** 28 Sep 2026 (image `16-build2`: same apps plus Payments 0.0.1 and LMS 2.63.0, installed on the
  same site, so Education and LMS share users and logins)

## Rules for the shared VPS

The VPS also runs Jitsi (`/docker/jitsi`), WorkAdventure (`/docker/workadventure`), n8n + Traefik
(`/docker/n8n`) and Sir Jim's apps.

- Everything for Education runs as `docker compose -p education` from `/docker/education`.
- **Never touch Sir Jim's project:** `/home/jim`, the `jim` and `openvpn-ce` projects, the
  `psmbfi_kc`, `psmbfi_kc_db`, `nginx-proxy`, `nginx-demo`, `certbot_ssl`, `dnsmasq` containers, UDP 1194.
- Never restart or edit Jitsi, WorkAdventure, n8n or Traefik. No `down -v`, no `prune`, no
  deploys through hPanel's Docker Manager, no Docker/server restarts.
- Before a change, save the other containers' state; after it, compare (see [Health check](#health-check)).

## How it's built

The server never builds anything. GitHub Actions builds the image and the VPS pulls it.

| File | Purpose |
|---|---|
| [apps.json](apps.json) | Apps baked into the image (ERPNext, HRMS, Education, Payments, LMS, all `version-16`) |
| [.github/workflows/build-image.yml](.github/workflows/build-image.yml) | Builds with frappe_docker's `images/layered/Containerfile`, pushes `ghcr.io/crimsoin/pcc-education:16` and `:16-buildN` (public) |
| [deploy/docker-compose.yaml](deploy/docker-compose.yaml) | The `education` project on the VPS |
| [deploy/env.template](deploy/env.template) | Settings; `install.sh` turns it into `.env` with generated passwords |
| [deploy/install.sh](deploy/install.sh) | Creates `.env` (never overwrites it) and validates the compose file |

Repo: https://github.com/Crimsoin/pcc-education. A build runs on every push that changes
`apps.json` or the workflow, or by hand: `gh workflow run build-image.yml` (about 10 minutes).

## How it runs on the VPS

| Service | Job | Memory / CPU cap | Idle use |
|---|---|---|---|
| frontend | nginx, the only service Traefik talks to | 128 MB / 0.5 | ~5 MB |
| backend | the app (gunicorn, 2 workers × 4 threads) | 768 MB / 1.0 | ~220 MB |
| websocket | live updates | 192 MB / 0.25 | ~50 MB |
| queue | one worker for all queues (long, default, short) | 512 MB / 0.75 | ~50 MB |
| scheduler | timed tasks (enabled) | 256 MB / 0.25 | ~50 MB |
| db | MariaDB 11.8, 256 MB buffer pool | 640 MB / 1.0 | ~300 MB |
| redis-cache / redis-queue | cache / job queue | 192 + 128 MB | ~30 MB |
| configurator | writes DB/Redis settings on start, then exits | 256 MB | — |
| create-site | one-off site creation (`setup` profile, never runs on `up`) | 1.5 GB / 1.0 | — |

Total cap for the running services is about 2.75 GB; at idle they use about 0.7 GB.

- **Routing:** only `frontend` joins `n8n_default`. Traefik routes `portal.srv1586246.hstgr.cloud`
  to it (router `edu-portal`, cert resolver `mytlschallenge`, Let's Encrypt, auto-renews).
  Everything else is on the private `edu` network. No ports are published, no firewall rules needed.
- **DNS:** none needed. Hostinger's `*.srv1586246.hstgr.cloud` already points to the VPS.
- **Data:** Docker volumes `education_sites` (site config, uploaded files), `education_db-data`
  (database), `education_redis-queue-data`, `education_logs`.
- **Secrets:** `DB_PASSWORD` (MariaDB root) and `ADMIN_PASSWORD` (the site's `Administrator`)
  exist only in `/docker/education/.env` on the server (mode 600). Never commit them.

## Customization

Branding is the Frappe default (no custom logo or app name). The only customization is the login
page layout: the icon and heading are centered, and the card is centered vertically.

- Stored in **Website Settings → Head HTML** as a `<style id="login-center">` tag with
  [customization/login-center.css](customization/login-center.css). It's in the site's database, so it
  survives image updates.
- Every rule is scoped to `body[data-path="login"]`, so other pages are unaffected.
- **Undo:** clear the Head HTML field (it was empty before).

## Known issues

- **`/admissions` returns a 500 error.** It's an upstream Education v16 bug (missing list template),
  [frappe/education#440](https://github.com/frappe/education/issues/440), and unrelated to our setup.
  Applicants can still be entered in the desk under Student Applicant.

## Everyday commands (on the VPS, in `/docker/education`)

```bash
docker compose -p education ps                     # status
docker compose -p education logs -f --tail 100 backend
docker compose -p education restart backend        # restart one Education service
docker compose -p education exec backend bench --site portal.srv1586246.hstgr.cloud <command>
grep ADMIN_PASSWORD .env                           # initial Administrator password
```

## Backups

Not automated yet (open item). A manual backup of the database and files:

```bash
docker compose -p education exec backend bench --site portal.srv1586246.hstgr.cloud backup --with-files
docker compose -p education exec backend ls -lh sites/portal.srv1586246.hstgr.cloud/private/backups
```

Hostinger's weekly auto-backups cover the whole server, but restoring one rolls back **every**
app on it, including Sir Jim's, so it's a last resort.

## Updating

1. Change `apps.json` if needed and push, or run the workflow by hand. Note the new `16-buildN`.
2. Take a backup (above).
3. On the VPS: set `EDU_TAG=16-buildN` in `.env`, then:
   ```bash
   docker compose -p education pull
   docker compose -p education up -d
   docker compose -p education exec backend bench --site portal.srv1586246.hstgr.cloud migrate
   ```
4. Run the health check.

## Health check

```bash
# before a change
docker ps -a --format '{{.Names}}' | grep -v '^education-' | sort | while read n; do
  docker inspect "$n" --format '{{.Name}} {{.Id}} {{.State.StartedAt}} restarts={{.RestartCount}} {{.State.Status}}'; done > /root/containers-before.txt
# after: re-run the same loop into /root/containers-after.txt, then
diff /root/containers-before.txt /root/containers-after.txt && echo "others unchanged"
curl -s -o /dev/null -w '%{http_code}\n' https://portal.srv1586246.hstgr.cloud/api/method/ping
```

The deployment baseline is `/root/containers-before-education.txt` (22 containers, 28 Sep).

## Redeploy from scratch / new server

1. Docker + Compose v2, and a Traefik on an external network with a TLS cert resolver.
   On another server, check `n8n_default`, `mytlschallenge` and `TRAEFIK_SUBNET`.
2. Copy `deploy/*` to `/docker/education`, then `bash install.sh`.
3. `docker compose -p education pull && docker compose -p education up -d`
4. `docker compose -p education --profile setup run --rm create-site` (about 3–15 minutes)
5. `docker compose -p education exec backend bench --site <site> enable-scheduler`
6. To move existing data instead, restore a `bench backup --with-files` with `bench --site <site> restore`.

## Removal

Only removes Education; nothing else is affected.

```bash
cd /docker/education
docker compose -p education down        # stop and remove containers, keep data
docker compose -p education down -v     # also delete the database and files (irreversible)
```

## Outgoing email

Set up 28 Sep 2026 in the desk as Email Account **PCC Portal** (`pccwebnotifs@gmail.com`),
Service GMail, `smtp.gmail.com:587` with TLS, outgoing only, **Default Outgoing** on. It
authenticates with a Gmail App Password stored only in the site (not in this repo). This makes
"Forgot password?", welcome emails and notifications work.

- Queued and failed emails: `/desk/email-queue`.
- Gmail allows about 500 emails a day; use a sending service (e.g. Brevo) for bulk mail.
- If the Gmail password changes or 2-Step Verification is turned off, the App Password stops
  working: create a new one and paste it into the Email Account.

## Open items

- Configure the school (academic year, programs) and change the Administrator password.
- Automate daily backups and copy them off the server.
- Optional: a `philippinecoding.com` address (DNS **A record** → 187.127.110.227, not
  Websites → Subdomains), then `bench setup add-domain` / rename the site.
