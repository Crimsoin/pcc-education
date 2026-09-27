# PCC Education (Frappe Education on the VPS)

Frappe v16 + ERPNext + HRMS + Education for Philippine Coding Camp, running on the
Hostinger VPS `srv1586246.hstgr.cloud` at **https://portal.srv1586246.hstgr.cloud**.

> Status: image build set up. Server deployment not done yet. This README will be
> completed after deployment.

## How the image is built

The server never builds anything. GitHub Actions builds the image and the VPS pulls it.

- [apps.json](apps.json) lists the apps baked into the image (all on `version-16`).
- [.github/workflows/build-image.yml](.github/workflows/build-image.yml) builds it with
  frappe_docker's `images/layered/Containerfile` and pushes it to
  `ghcr.io/crimsoin/pcc-education`, tagged `16` (latest) and `16-buildN` (each build).
- It runs on every push that changes `apps.json` or the workflow, or by hand:
  GitHub → Actions → Build image → Run workflow, or `gh workflow run build-image.yml`.

## Rules for the shared VPS

- Everything runs as `docker compose -p education` from `/docker/education`.
- Never touch Sir Jim's project (`/home/jim`, the `jim` and `openvpn-ce` projects, the
  `psmbfi_kc*`, `nginx-proxy` and `nginx-demo` containers, UDP 1194).
- Never restart or edit Jitsi, WorkAdventure, n8n or Traefik. No `down -v`, no `prune`,
  no deploys through hPanel's Docker Manager.
