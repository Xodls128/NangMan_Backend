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
ok=0
for i in $(seq 1 24); do
  if docker compose exec -T web curl -sf -H "Host: api.gamemate.kr" http://127.0.0.1:8000/health/; then
    echo
    echo "OK (attempt $i)"
    ok=1
    break
  fi
  echo "retry $i/24..."
  sleep 5
done
if [ "$ok" -ne 1 ]; then
  echo "health check failed"
  docker compose logs web --tail 80
  exit 1
fi

echo "배포 완료"
