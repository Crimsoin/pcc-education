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

The VPS is shared. Education owns only the `education-*` containers, the `education_*` volumes
and `/docker/education`. **Everything else on the server is off-limits.**

- Everything for Education runs as `docker compose -p education` from `/docker/education`.
- **Never touch Sir Jim's project:** `/home/jim` and every container started from it (compose
  project `jim`, and anything whose working directory is under `/home/jim`). Its containers
  change over time, so check by working directory, not by name.
- Never stop, restart, edit or remove another project's containers, networks or folders. No
  `down -v`, no `prune`, no deploys through hPanel's Docker Manager, no Docker/server restarts.
- Before a change, save the other containers' state; after it, compare (see [Health check](#health-check)).

Other projects on the server (checked 18 Oct 2026), none of them part of Education:

| Compose project | Folder | Note |
|---|---|---|
| `n8n` | `/docker/n8n` | n8n, plus the **Traefik** that routes Education's HTTPS. Never restart it. |
| `jitsi` | `/docker/jitsi` | Video classes |
| `workadventure` | `/docker/workadventure` | Virtual campus |
| `virtual-campus` | `/docker/virtual-campus` | Added in October 2026 |
| `webcompiler` | `/docker/webcompiler` | |
| `jim`, `docker` (inscore-*) | `/home/jim/...` | **Sir Jim's.** Most were stopped by their owner in October 2026; leave them as they are. |

To see who owns a container: `docker inspect <name> --format '{{index .Config.Labels "com.docker.compose.project.working_dir"}}'`.

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
- **Reboots:** every service has `restart: unless-stopped`, so Education comes back on its own
  after a server reboot (confirmed after the reboot on 17 Oct 2026).

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
2. Check that no class is running on Jitsi. Take a **Hostinger snapshot** (hPanel → VPS →
   Snapshots & Backups → New snapshot; it replaces the previous one and expires after about a day)
   and a site backup (above). Taking a snapshot doesn't stop anything; **never use Restore**,
   because it rolls back every project on the server, including Sir Jim's.
3. On the VPS: save the [health check](#health-check) baseline, keep the current settings
   (`cp .env .env.bak-buildN`), set `EDU_TAG=16-buildN` in `.env`, then:
   ```bash
   docker compose -p education pull
   docker compose -p education up -d      # recreates only the education-* app containers
   docker compose -p education --profile setup run --rm create-site \
     "bench --site portal.srv1586246.hstgr.cloud migrate && bench --site portal.srv1586246.hstgr.cloud clear-cache"
   ```
   Run heavy bench commands (`migrate`, `install-app`) through the one-off `create-site`
   container like this. It has its own 1.5 GB / 1 CPU cap, so the live backend (768 MB) isn't starved.
4. Run the health check.

### Adding another Frappe app

This is how LMS was added on 28 Sep 2026 (image `16-build2`):

1. Add the app to `apps.json` on its `version-16` branch, together with any app it requires (its
   `hooks.py` lists them as `required_apps`; LMS needs `payments`). Add it to the version check
   at the end of the workflow too. Pushing builds the new `16-buildN`.
2. Update the server as above (steps 2–3), and before the migrate command install the app:
   ```bash
   docker compose -p education --profile setup run --rm create-site \
     "bench --site portal.srv1586246.hstgr.cloud install-app <app>"
   ```
3. Add `--install-app <app>` to the `create-site` service in
   [deploy/docker-compose.yaml](deploy/docker-compose.yaml), so a fresh redeploy includes it, and
   copy the file to `/docker/education` on the server.
4. Existing users don't get the new app's roles automatically. Give them to the admins again (see
   [Users and roles](#users-and-roles)).

## Health check

```bash
# before a change
docker ps -a --format '{{.Names}}' | grep -v '^education-' | sort | while read n; do
  docker inspect "$n" --format '{{.Name}} {{.Id}} {{.State.StartedAt}} restarts={{.RestartCount}} {{.State.Status}}'; done > /root/containers-before.txt
# after: re-run the same loop into /root/containers-after.txt, then
diff /root/containers-before.txt /root/containers-after.txt && echo "others unchanged"
curl -s -o /dev/null -w '%{http_code}\n' https://portal.srv1586246.hstgr.cloud/api/method/ping
```

Always take a fresh baseline right before a change, because the other projects on the server change
over time. Earlier baselines are kept as `/root/containers-*.txt` (Education install and LMS
install, both 28 Sep 2026).

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

## Users and roles

- **System Manager** is the admin role: users, roles, settings. Each app's records also need that
  app's own roles. For a full admin, open the user → **Roles & Permissions** → **Select All**,
  then **untick Student and Guardian**.
- **Student and Guardian send people to the student portal** (`/edu-portal`) after login instead
  of the desk. Never give them to staff or admins.
- **New apps add roles that existing users don't get.** After installing an app, repeat Select All
  for admins. For example, the LMS desk icon ("Frappe Learning") only shows for users with an LMS role.
- **Only System Managers can change roles.** To stop a staff account from managing roles, leave
  System Manager off it; Education Manager is enough to run the school.
- **The built-in `Administrator`** bypasses all permission checks. Keep it for emergencies, with a
  strong password.
- **New users:** leave "Send Welcome Email" ticked so they choose their own password. Students get
  a login automatically when their Student record has an email address.

| Who | Roles |
|---|---|
| Full admin | Select All, minus Student and Guardian |
| School office | Education Manager, Academics User |
| Teacher | Instructor, Academics User (plus Course Creator to write LMS courses) |
| LMS admin | Moderator |
| LMS course author / grader | Course Creator / Batch Evaluator |

**Education and LMS are separate apps on one site.** They share logins, users, email and backups,
but not records. Education's Students, Programs/Courses, Student Groups, Instructors, grades and
fees aren't linked to LMS's courses, batches, instructors, scores or payments. A teacher who works in
both needs an Education **Instructor** record (linked to an Employee) and, in LMS, the
**Course Creator** role plus a place on the course. Linking the two would need a small custom app
(or Server Scripts / n8n); nothing like that exists yet.

## Handover

This repo is the recipe, not the whole system. A new owner also needs:

| What | Where it is now | How to hand it over |
|---|---|---|
| This repo | GitHub, account `Crimsoin` | Settings → Transfer ownership, or add them as a collaborator |
| The built image | `ghcr.io/crimsoin/pcc-education` (account `Crimsoin`) | **Doesn't move with the repo.** Change `IMAGE` in the workflow and `image:` in `deploy/docker-compose.yaml` to the new owner's name, rebuild, and copy the compose file to the server. Keep the old image until the server uses the new one. |
| The server | Hostinger VPS `srv1586246` (root SSH) | See the warning below |
| Database and initial `Administrator` passwords | `/docker/education/.env` on the server only | Comes with server access |
| The site's data: users, students, courses, settings, files | The server only (`education_*` volumes) | Comes with the server, or move it with a site backup (see [Backups](#backups)) |
| A site admin login | The site | Create them their own System Manager account; don't share accounts |
| Sending email | Google account `pccwebnotifs@gmail.com` (App Password) | Hand over the Google account, or set up a new one and replace the password in the Email Account |
| Address | `portal.srv1586246.hstgr.cloud`, Hostinger's default name | Nothing to transfer while it stays on this server |

**The server is shared.** Anyone who can run Docker on it controls every project there, not
just Education, including Sir Jim's; Education-only access isn't possible. Either the new owner is
trusted with the whole server (agree it with the server's owner and Sir Jim), or move Education to its
own server first: take a site backup with files, follow
[Redeploy from scratch](#redeploy-from-scratch--new-server), and restore the backup there.

The setup was done with Claude Code. Its notes and conversations stay on the original owner's
PC, so everything a new owner needs belongs in this README.

## Open items

- Configure the school (academic year, programs) and change the Administrator password.
- Automate daily backups and copy them off the server.
- Optional: a `philippinecoding.com` address (DNS **A record** → 187.127.110.227, not
  Websites → Subdomains), then `bench setup add-domain` / rename the site.
