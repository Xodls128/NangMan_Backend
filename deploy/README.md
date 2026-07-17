# NangMan 백엔드 — Docker + EC2 배포 (`api.gamemate.kr`)

Docker Compose로 `web`(Daphne) · `db` · `redis` · `nginx` · `certbot`을 올립니다.  
`main` 푸시 시 GitHub Actions가 EC2에 SSH해 자동 재배포합니다.

## 아키텍처

```
GitHub main push
    → Actions SSH → EC2: git pull + docker compose up -d --build
Internet → nginx:443 → web:8000 (Daphne ASGI + WSS)
         ├─ postgres (volume)
         └─ redis (Channel Layer)
```

## 0. AWS EC2

1. Ubuntu 22.04/24.04, t3.small 권장, 스토리지 20GB+
2. 보안 그룹: SSH 22(본인 IP), HTTP 80, HTTPS 443
3. Elastic IP 권장
4. SSH: `ssh -i your.pem ubuntu@<IP>`

## 1. 가비아 DNS

| 타입 | 호스트 | 값 | TTL |
|------|--------|-----|-----|
| A | `api` | EC2 Elastic IP | 300 |

```bash
nslookup api.gamemate.kr
```

## 2. 서버 최초 설치

```bash
sudo apt-get update && sudo apt-get install -y git
# 또는 이미 clone 했다면
git clone https://github.com/Xodls128/NangMan_Backend.git ~/NangMan
cd ~/NangMan
sudo bash deploy/setup-server.sh
# docker 그룹 적용을 위해 한 번 재로그인
exit
ssh -i your.pem ubuntu@<IP>
```

## 3. 환경 변수

```bash
cd ~/NangMan
cp .env.example .env
nano .env
```

필수: `SECRET_KEY`, `DB_PASSWORD`.  
SSL 발급 전엔 `SECURE_SSL_REDIRECT=False` 권장, 발급 후 `True`.

## 4. 최초 기동 (HTTP) → SSL → HTTPS

```bash
# HTTPS conf는 인증서 없으면 nginx가 실패하므로 잠시 비활성
cp deploy/nginx/conf.d/00-http-bootstrap.conf.template deploy/nginx/conf.d/00-http-bootstrap.conf
mv deploy/nginx/conf.d/api.gamemate.kr.conf deploy/nginx/conf.d/api.gamemate.kr.conf.ssl-pending

docker compose up -d --build
docker compose ps
curl http://127.0.0.1/health/

# DNS 전파·80 포트 확인 후
export CERTBOT_EMAIL=you@example.com
bash deploy/init-ssl.sh

# .env 의 SECURE_SSL_REDIRECT=True 로 바꾸고
docker compose up -d web
curl -sf https://api.gamemate.kr/health/
```

인증서 갱신 (cron 권장):

```bash
crontab -e
# 매일 03:00
0 3 * * * cd /home/ubuntu/NangMan && bash deploy/renew-ssl.sh >> /home/ubuntu/ssl-renew.log 2>&1
```

## 5. GitHub Actions 자동 재배포

Repository → **Settings → Secrets and variables → Actions**

### Secrets

| Name | 값 |
|------|-----|
| `EC2_HOST` | Elastic IP 또는 도메인 |
| `EC2_USER` | `ubuntu` |
| `EC2_SSH_KEY` | PEM 개인키 전체 (`-----BEGIN ...`) |
| `EC2_PORT` | (선택) 기본 22 |
| `EC2_APP_DIR` | (선택) 기본 `/home/ubuntu/NangMan` |

### Variables (선택)

| Name | 값 |
|------|-----|
| `PRODUCTION_URL` | `https://api.gamemate.kr` |

EC2에 Actions용 공개키 등록:

```bash
# 로컬에서 배포 전용 키 생성 권장
ssh-keygen -t ed25519 -f nangman-deploy -N ""
# nangman-deploy → GitHub Secret EC2_SSH_KEY
# nangman-deploy.pub → EC2 ~/.ssh/authorized_keys
```

`main`에 push하면 `.github/workflows/deploy.yml`이 실행됩니다.  
수동 실행: Actions → **Deploy to EC2** → Run workflow.

로컬/서버에서 수동 재배포:

```bash
bash ~/NangMan/deploy/deploy.sh
```

## 엔드포인트

| 용도 | URL |
|------|-----|
| Health | `https://api.gamemate.kr/health/` |
| REST | `https://api.gamemate.kr/api/...` |
| WebSocket | `wss://api.gamemate.kr/ws/rooms/{id}/?token=...` |

## 점검

```bash
docker compose ps
docker compose logs -f web
docker compose logs -f nginx
docker compose exec web python manage.py showmigrations
```

## 트러블슈팅

| 증상 | 확인 |
|------|------|
| nginx 기동 실패 | SSL conf가 인증서 없이 켜져 있음 → bootstrap 절차 |
| 502 | `docker compose logs web`, `.env` / migrate |
| Actions SSH 실패 | Secret 키·`authorized_keys`·보안그룹 |
| WS 실패 | `wss://`, Origin이 `ALLOWED_HOSTS`에 있는지 |
| DB 연결 실패 | `DB_PASSWORD`와 compose `POSTGRES_PASSWORD` 일치 |

## (레거시) systemd 직접 기동

이전 Nginx+systemd 방식 파일은 `deploy/systemd/`에 남아 있습니다.  
현재 권장 경로는 Docker Compose입니다.
