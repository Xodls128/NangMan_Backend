#!/usr/bin/env bash
# EC2 최초 1회: Docker + Compose 설치, 저장소 clone, 방화벽
set -euo pipefail

APP_USER="${APP_USER:-ubuntu}"
APP_HOME="/home/${APP_USER}"
APP_DIR="${APP_HOME}/NangMan"
REPO_URL="${REPO_URL:-https://github.com/Xodls128/NangMan_Backend.git}"

export DEBIAN_FRONTEND=noninteractive

echo "==> 시스템 패키지"
apt-get update
apt-get install -y ca-certificates curl git ufw

echo "==> Docker 설치"
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
  usermod -aG docker "${APP_USER}"
fi

systemctl enable --now docker

echo "==> 저장소"
if [ ! -d "${APP_DIR}/.git" ]; then
  sudo -u "${APP_USER}" git clone "${REPO_URL}" "${APP_DIR}"
else
  echo "이미 clone 됨: ${APP_DIR}"
fi

echo "==> 방화벽"
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable || true

cat <<EOF

========================================
Docker 준비 완료

다음 단계 (ubuntu 유저로):
  cd ${APP_DIR}
  cp .env.example .env
  nano .env          # SECRET_KEY, DB_PASSWORD, 카카오 키 등
  # 최초 SSL 전: HTTP 부트스트랩으로 기동
  cp deploy/nginx/conf.d/00-http-bootstrap.conf.template deploy/nginx/conf.d/00-http-bootstrap.conf
  mv deploy/nginx/conf.d/api.gamemate.kr.conf deploy/nginx/conf.d/api.gamemate.kr.conf.ssl-pending
  docker compose up -d --build
  export CERTBOT_EMAIL=you@example.com
  bash deploy/init-ssl.sh

이후 재배포:
  bash deploy/deploy.sh
  # 또는 GitHub Actions (main push)

자세한 내용: deploy/README.md
========================================
EOF
