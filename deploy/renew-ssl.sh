#!/usr/bin/env bash
# cron 예: 0 3 * * * cd /home/ubuntu/NangMan && bash deploy/renew-ssl.sh >> /var/log/nangman-ssl.log 2>&1
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

docker compose run --rm --entrypoint certbot certbot renew --webroot -w /var/www/certbot
docker compose exec -T nginx nginx -s reload
echo "cert renew done: $(date -Is)"
