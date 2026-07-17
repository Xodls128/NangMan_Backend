## Deploy Configuration (configured by /setup-deploy)
- Platform: AWS EC2 + Docker Compose (Nginx, Daphne, PostgreSQL, Redis)
- Production URL: https://api.gamemate.kr
- Deploy workflow: `.github/workflows/deploy.yml` (push to main → SSH redeploy)
- Deploy status command: `docker compose -f /home/ubuntu/NangMan/docker-compose.yml ps`
- Merge method: squash (recommended)
- Project type: web app / API (Django Channels ASGI)
- Post-deploy health check: https://api.gamemate.kr/health/

### Custom deploy hooks
- Pre-merge: none
- Deploy trigger: GitHub Actions on `main` (or `bash deploy/deploy.sh` on EC2)
- Deploy status: `docker compose ps`
- Health check: `curl -sf https://api.gamemate.kr/health/`
