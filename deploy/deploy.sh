#!/usr/bin/env bash
# EC2에서 코드 pull 후 Docker Compose 재배포
set -euo pipefail

APP_DIR="${APP_DIR:-/home/ubuntu/NangMan}"
cd "$APP_DIR"

echo "==> git pull"
git pull --ff-only

echo "==> docker compose build & up"
docker compose up -d --build --remove-orphans

echo "==> 상태"
docker compose ps

echo "==> health (container)"
sleep 3
docker compose exec -T web curl -sf http://127.0.0.1:8000/health/ && echo

echo "배포 완료"
