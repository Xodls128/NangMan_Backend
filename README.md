# NangMan

게임 친구 매칭 서비스 — Django REST Framework 백엔드 + 테스트용 React 프론트엔드

## 프로젝트 개요

- 유저가 방을 만들고, 다른 유저의 가입 신청을 방장이 수락해 게임 친구를 매칭합니다.
- 방을 생성한 유저가 해당 방의 방장입니다.
- 승인된 멤버는 방 채팅(REST + WebSocket)을 사용할 수 있습니다.

## 기술 스택

| 구분 | 스택 |
|------|------|
| Backend | Python 3.11, Django, DRF, SimpleJWT, Channels, Daphne, drf-spectacular |
| DB | 로컬 SQLite / 프로덕션 PostgreSQL |
| Auth | JWT + 카카오 OAuth (인가 코드 → JWT) |
| Frontend | React, Vite, TypeScript (기능 검증용) |

## MVP 진행 상태

| # | 기능 | 상태 |
|---|------|------|
| 1 | 방장 · 일반 유저 (방 소속으로 구분) | 완료 |
| 2 | 방 생성 · 참여(신청/수락/거절) | 완료 |
| 3 | 방 목록 → 가입 신청 → 방장 수락 | 완료 |
| 4 | 방 내부 채팅 (REST + WebSocket) | 완료 |
| 5 | 카카오 소셜 로그인 | 완료 (로컬) |
| — | EC2 배포 · WSS · Redis Channel Layer | Docker Compose + Actions 설정 완료 · 서버 적용 진행 |

## 폴더 구조

```
NangMan/
├── backend/                 # Django 프로젝트 루트
│   ├── apps/
│   │   ├── accounts/        # 유저, JWT, 카카오 로그인
│   │   ├── rooms/           # 방, 멤버십, 시드 커맨드
│   │   └── chats/           # 채팅 REST + WebSocket
│   ├── config/
│   │   └── settings/        # base / development / production
│   ├── manage.py
│   ├── .env.example
│   └── requirements.txt
├── frontend/                # Vite React (.gitignore로 추적 제외함)
└── README.md
```

## 로컬 실행

### 1. 백엔드

```bash
cd backend
# Python 3.11 venv 권장
source env/Scripts/activate   # Git Bash (Windows)
# .\env\Scripts\Activate.ps1  # PowerShell

pip install -r requirements.txt
cp .env.example .env          # SECRET_KEY, 카카오 키 등 채우기
python manage.py migrate
python manage.py seed_mock --flush   # 선택: 테스트 목업
python manage.py runserver            # 또는 daphne (WS 포함 시 ASGI)
```

WebSocket까지 쓰기위해 ASGI로 실행합니다.

```bash
daphne -b 127.0.0.1 -p 8000 config.asgi:application
```

- 설정 기본값: `config.settings.development` (SQLite, `SEED_MOCK_DATA=True`)
- API 문서 (DEBUG만): http://127.0.0.1:8000/api/docs/

### 2. 프론트

```bash
cd frontend
npm install
npm run dev
```

- 주소: http://localhost:5173  
- `/api` → `http://127.0.0.1:8000` 프록시  
- WS: `VITE_WS_BASE=ws://127.0.0.1:8000` (필요 시 `.env`)

### 3. 환경 변수 (backend/.env)

`.env.example` 참고. 카카오 관련:

```env
KAKAO_REST_API_KEY=
KAKAO_CLIENT_SECRET=
KAKAO_REDIRECT_URI=http://localhost:5173/auth/kakao/callback
```

카카오 디벨로퍼스에서 **플랫폼 키 → REST API 키**에 Redirect URI를 등록해야 합니다.  
(제품 설정만 넣고 REST 키에 없으면 `KOE006`이 납니다.)

## 인증

### 개발·시드용 (username/password)

- `POST /api/auth/token/` → `{ access, refresh }`
- `POST /api/auth/token/refresh/`
- `POST /api/auth/logout/` (refresh 블랙리스트)
- `GET /api/auth/me/`

### 카카오 로그인

1. `GET /api/auth/kakao/login-url/` → 인가 URL  
2. 브라우저에서 카카오 동의 → Redirect:  
   `http://localhost:5173/auth/kakao/callback?code=...`  
3. `POST /api/auth/kakao/` body `{ "code": "..." }` → `{ access, refresh, user }`  
4. 이후 API·WebSocket은 기존과 같이 Bearer / `?token=` 사용  

프론트 로그인 모달: **카카오 로그인** + 테스트 계정(username) 병행.

## 방 · 멤버십 API (요약)

| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/rooms/` | 방 목록 (비로그인 가능) |
| POST | `/api/rooms/` | 방 생성 (방장 approved 자동 등록) |
| GET | `/api/rooms/mine/` | 내가 만든 방 |
| GET | `/api/rooms/{id}/` | 방 상세 |
| POST | `/api/rooms/{id}/apply/` | 가입 신청 |
| GET | `/api/rooms/{id}/applications/` | 대기 신청 (방장) |
| GET | `/api/rooms/{id}/members/` | 승인 멤버 목록 |
| POST | `/api/memberships/{id}/approve/` | 수락 (입장 시스템 메시지 + WS 푸시) |
| POST | `/api/memberships/{id}/reject/` | 거절 (재신청 불가) |

멤버십 상태: `pending` / `approved` / `rejected`

## 채팅

### REST

- `GET /api/rooms/{room_id}/messages/` (`?after_id=` 선택)
- `POST /api/rooms/{room_id}/messages/` `{ "content": "..." }`

승인 멤버만 가능. REST 전송 시에도 WebSocket으로 브로드캐스트합니다.

### WebSocket

```
ws://127.0.0.1:8000/ws/rooms/{room_id}/?token=<access_jwt>
```

- 전송: `{ "type": "chat.message", "content": "..." }`
- 수신: `{ "type": "chat.message", "message": { ... } }`  
  `message_type`: `user` | `system` (입장 안내 등)

로컬 Channel Layer는 InMemory. 배포 시 멀티 워커면 Redis로 교체해야 함.

## 프론트 IA (테스트 UI) - 깃헙에는 안올림

| 경로 | 역할 |
|------|------|
| `/` | 방 목록, 방 만들기 모달, 가입 신청 |
| `/my-rooms` | 참여 중 / 신청 대기 |
| `/me` | 계정, 내가 만든 방 |
| `/rooms/:id` | 채팅 + 우측 멤버/대기 신청(방장) |
| `/auth/kakao/callback` | 카카오 OAuth 콜백 |

하단 네비: 메인 · 나의 방 · 마이페이지

## 목업 시드

```bash
python manage.py seed_mock --flush
```

| 계정 | 비밀번호 | 용도 |
|------|----------|------|
| `ws_owner` | `testpass123` | 방장 |
| `ws_member` | `testpass123` | 승인 멤버 |
| `ws_pending` | `testpass123` | 가입 대기 |
| `ws_outsider` | `testpass123` | 미신청 |
| `ws_rejected` | `testpass123` | 거절됨 |

`SEED_MOCK_DATA=True`인 development에서만 실행됩니다.  
서버 재시작만으로는 데이터가 초기지지 않습니다. (`db.sqlite3` 유지)

## 설정 분리

- `config.settings.development` — DEBUG, SQLite, 시드 허용, CORS 완화  
- `config.settings.production` — PostgreSQL, `SEED_MOCK_DATA=False`, HTTPS 관련 설정  

`manage.py` 기본: development  
`wsgi.py` / `asgi.py` 기본: production  

## 배포 시 WebSocket 참고

- Daphne(ASGI) + Nginx `Upgrade` / `Connection` (Docker `nginx` 서비스)
- HTTPS → 클라이언트는 `wss://`
- `AllowedHostsOriginValidator` + `ALLOWED_HOSTS` (프론트 도메인 포함)
- Redis Channel Layer (`channels-redis`)
- JWT를 쿼리로 넘기는 현재 방식은 로그 노출에 주의

## 배포 (EC2 + Docker)

백엔드 도메인: `api.gamemate.kr`  
Docker Compose + GitHub Actions 자동 재배포: [deploy/README.md](deploy/README.md)

```bash
# EC2 최초
git clone https://github.com/Xodls128/NangMan_Backend.git ~/NangMan
sudo bash ~/NangMan/deploy/setup-server.sh
# → .env 작성 → docker compose up -d --build
# → 가비아 A레코드(api → EC2 IP) → bash deploy/init-ssl.sh
# → GitHub Secrets(EC2_HOST/USER/SSH_KEY) 등록 후 main push 시 자동 배포
```

## 남은 과제 (요약)

- 프로덕션 배포 실행 (EC2 인스턴스·DNS·SSL·Actions Secrets)
- JWT refresh 프론트 자동 갱신·로그아웃 연동 강화
- 방 나가기/강퇴 등 세부 정책
- 프론트를 서비스 UI 수준으로 고도화
