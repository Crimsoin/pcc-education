#!/usr/bin/env bash
# Prepares /docker/education on the VPS. Safe to re-run: it never overwrites an existing .env
# and never starts, stops or touches any other Compose project.
#   Usage (on the VPS):  cd /docker/education && bash install.sh
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f .env ]; then
  cp env.template .env
  for key in DB_PASSWORD ADMIN_PASSWORD; do
    sed -i "s|^${key}=.*|${key}=$(openssl rand -hex 16)|" .env
  done
  chmod 600 .env
  echo "Created .env with fresh secrets."
else
  echo ".env already exists; left unchanged."
fi

docker network inspect n8n_default >/dev/null   # Traefik's network must exist
docker compose -p education config --quiet
echo "Compose file is valid. Next: docker compose -p education pull && docker compose -p education up -d"
