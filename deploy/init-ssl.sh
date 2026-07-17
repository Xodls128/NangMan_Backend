#!/usr/bin/env bash
# Let's Encrypt 인증서 최초 발급 (Docker Compose)
# 전제: DNS A레코드 api.gamemate.kr → EC2, 80 포트 개방, compose로 web/nginx 기동 중
set -euo pipefail

DOMAIN="${DOMAIN:-api.gamemate.kr}"
EMAIL="${CERTBOT_EMAIL:?CERTBOT_EMAIL 환경변수를 설정하세요 (예: export CERTBOT_EMAIL=you@example.com)}"
COMPOSE="docker compose"
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

CONF_DIR="$ROOT_DIR/deploy/nginx/conf.d"
PROD_CONF="$CONF_DIR/api.gamemate.kr.conf"
BOOT_CONF="$CONF_DIR/00-http-bootstrap.conf"
BOOT_TMPL="$CONF_DIR/00-http-bootstrap.conf.template"

echo "==> HTTP 부트스트랩 모드로 전환"
if [ -f "$PROD_CONF" ]; then
  mv "$PROD_CONF" "${PROD_CONF}.ssl-pending"
fi
cp "$BOOT_TMPL" "$BOOT_CONF"

# SSL redirect 끄고 잠시 HTTP로 동작 (앱이 https 강제하면 challenge 외 테스트만 영향)
$COMPOSE up -d nginx web
$COMPOSE exec -T nginx nginx -s reload || $COMPOSE restart nginx

echo "==> certbot 발급"
$COMPOSE run --rm --entrypoint certbot certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  --email "$EMAIL" \
  --agree-tos \
  --no-eff-email \
  -d "$DOMAIN"

echo "==> HTTPS 설정 복구"
rm -f "$BOOT_CONF"
if [ -f "${PROD_CONF}.ssl-pending" ]; then
  mv "${PROD_CONF}.ssl-pending" "$PROD_CONF"
fi

$COMPOSE up -d nginx
$COMPOSE exec -T nginx nginx -s reload

echo "==> 완료: https://${DOMAIN}/health/"
curl -sf "https://${DOMAIN}/health/" && echo
