# NangMan Backend API 명세서

- **버전:** 0.1.0  
- **프로덕션 Base URL:** `https://api.gamemate.kr`  
- **인증:** JWT Bearer (`Authorization: Authorization: Bearer <access>`)  
- **토큰 수명:** access 약 30분 / refresh 약 7일 (rotate + blacklist)

표기:

| 기호 | 의미 |
|------|------|
| 🔓 | 비로그인 가능 |
| 🔒 | JWT 필수 |

---

## 1. 인증 (auth)

### `GET /api/auth/mode/` 🔓

서버 인증 모드 조회. 프론트는 이 값으로 로그인 UI를 전환합니다.

**응답 200**
```json
{ "mvp_test": false, "auth_mode": "kakao" }
```

| `mvp_test` | `auth_mode` | 의미 |
|------------|-------------|------|
| `false` | `kakao` | 카카오 로그인 (기본) |
| `true` | `mvp` | 닉네임·비밀번호 통합 가입/로그인 |

환경 변수 `MVP_TEST=true` 일 때 MVP 모드. 기본값은 `false`.

---

### `POST /api/auth/mvp/` 🔓

`MVP_TEST=true` 전용. 닉네임·비밀번호로 **가입 또는 로그인**을 한 번에 처리합니다.

- 닉네임이 없으면 → 회원가입 후 JWT 발급 (`201`, `created: true`)
- 닉네임이 있으면 → 비밀번호로 로그인 (`200`, `created: false`)
- 닉네임은 `username`으로 저장되며 **대소문자를 구분하지 않고 고유**해야 합니다.

**요청**
```json
{ "nickname": "게이머닉", "password": "..." }
```

**응답 201 (신규 가입)**
```json
{
  "access": "...",
  "refresh": "...",
  "user": { "id": 1, "username": "게이머닉", "nickname": "게이머닉", "provider": "local" },
  "created": true,
  "message": "회원가입이 완료되었고 로그인되었습니다."
}
```

**응답 200 (기존 로그인)**
```json
{
  "access": "...",
  "refresh": "...",
  "user": { "..." },
  "created": false,
  "message": "로그인되었습니다."
}
```

| 코드 | 의미 |
|------|------|
| 400 | 입력 검증 실패 (짧은 비밀번호 등) |
| 401 | `해당 닉네임이 이미 존재하며 비밀번호가 다릅니다.` |
| 403 | `MVP_TEST` 비활성 |

---

### `GET /api/auth/kakao/login-url/` 🔓

카카오 인가 URL 조회. `MVP_TEST=true`이면 `403`.

**응답 200**
```json
{ "authorize_url": "https://kauth.kakao.com/oauth/authorize?..." }
```

Redirect URI는 서버 `KAKAO_REDIRECT_URI` 사용.

---

### `POST /api/auth/kakao/` 🔓

카카오 인가 코드 → JWT. `MVP_TEST=true`이면 `403`.

**요청**
```json
{ "code": "<카카오 인가 코드>" }
```

**응답 200**
```json
{
  "access": "...",
  "refresh": "...",
  "user": { "id": 1, "username": "...", "nickname": "...", "provider": "kakao", "..." }
}
```

| 코드 | 의미 |
|------|------|
| 400 | 잘못된 code / 카카오 오류 |
| 403 | MVP 테스트 모드로 카카오 비활성 |
| 502 | 카카오 서버 통신 실패 |

---

### `POST /api/auth/token/` 🔓

username/password 로그인 (개발·시드용).

**요청**
```json
{ "username": "wss_tester", "password": "..." }
```

**응답 200:** `{ "access", "refresh" }`

---

### `POST /api/auth/token/refresh/` 🔓

access 갱신. rotate 시 새 refresh도 반환, 이전 refresh는 블랙리스트.

**요청**
```json
{ "refresh": "..." }
```

---

### `POST /api/auth/logout/`

refresh 블랙리스트 등록.

**요청**
```json
{ "refresh": "..." }
```

클라이언트의 access/refresh 로컬 삭제도 필요.

---

### `GET /api/auth/me/` 🔒

현재 유저 정보.

**응답 200:** `User` 객체

---

## 2. 게임 (games)

### `GET /api/games/` 🔓

활성 게임 카탈로그 (정렬순).

**응답 200:** `Game[]`

### `GET /api/games/{id}/` 🔓

게임 단건.

---

## 3. 방 (rooms)

### `GET /api/rooms/` 🔓

방 목록 (최신순).

| Query | 설명 |
|-------|------|
| `game` | 게임 슬러그 필터 (예: `lol`) |

로그인 시 각 방에 `my_membership_status` 포함.

---

### `POST /api/rooms/` 🔒

방 생성. 생성자 = 방장, 자동 `approved` 멤버 등록.

**요청**
```json
{
  "title": "같이 하실 분",
  "description": "옵션",
  "game": "lol",
  "play_time_slot": "evening",
  "max_members": 5
}
```

| 필드 | 필수 | 설명 |
|------|------|------|
| title | O | 최대 100자 |
| game | O | 게임 slug (`GET /api/games/`) |
| play_time_slot | O | `dawn`(00~06), `morning`(06~12), `afternoon`(12~18), `evening`(18~24) |
| description | | |
| max_members | | 2~12, 기본 5 |

**응답 201:** `Room`

방 목록·상세 응답에는 선택값 `play_time_slot`과 표시 문구
`play_time_label`(예: `저녁 (18:00~24:00)`)이 함께 포함됩니다.
기존 방은 두 값이 `null`일 수 있습니다.

---

### `GET /api/rooms/mine/` 🔒

내가 **approved**인 방 목록.

---

### `GET /api/rooms/{id}/` 🔒

방 상세 + `my_membership_status`.

---

### `POST /api/rooms/{id}/apply/` 🔒

가입 신청 → `pending`.

제한: 방장 본인 불가, closed/정원 초과 불가, 기존 이력 있으면 재신청 불가.

**응답 201:** `RoomMembership`  
**400:** 신청 불가

---

### `GET /api/rooms/{id}/applications/` 🔒 (방장)

pending 신청 목록.

**403:** 방장 아님

---

### `GET /api/rooms/{id}/members/` 🔒 (approved 멤버)

approved 멤버 목록.

**403:** 미승인

---

### `POST /api/memberships/{id}/approve/` 🔒 (방장)

pending → approved. 시스템 입장 메시지 + WS 푸시. 정원 도달 시 방 `closed` 가능.

| 코드 | 의미 |
|------|------|
| 400 | 대기 아님 / 정원 초과 |
| 403 | 방장 아님 |

---

### `POST /api/memberships/{id}/reject/` 🔒 (방장)

pending → rejected. 재신청 불가.

---

## 4. 채팅 REST (chats)

승인(approved) 멤버만.

### `GET /api/rooms/{room_id}/messages/` 🔒

| Query | 설명 |
|-------|------|
| `after_id` | 해당 ID보다 큰 메시지만 (증분 조회) |

**응답 200:** `ChatMessage[]`

---

### `POST /api/rooms/{room_id}/messages/` 🔒

REST 저장 + WebSocket 브로드캐스트.

**요청**
```json
{ "content": "안녕" }
```

content: 공백 불가, 최대 1000자.  
**응답 201:** `ChatMessage`

---

## 5. 채팅 WebSocket (OpenAPI 외)

프로덕션:

```text
wss://api.gamemate.kr/ws/rooms/{room_id}/?token=<access_jwt>
```

- Origin이 `ALLOWED_HOSTS`에 포함되어야 함 (예: `gamemate.kr`, 로컬 테스트 시에도 허용 호스트 필요)
- 승인 멤버만 connect (`4401` 미인증 / `4403` 미승인)

**클라이언트 → 서버**
```json
{ "type": "chat.message", "content": "안녕" }
```

**서버 → 클라이언트**
```json
{
  "type": "chat.message",
  "message": {
    "id": 1,
    "room": 2,
    "sender": { "id": 1, "username": "...", "nickname": "..." },
    "message_type": "user",
    "content": "안녕",
    "created_at": "2026-07-18T04:19:00+09:00"
  }
}
```

`message_type`: `user` | `system` (입장 안내 등)

---

## 6. 공통 스키마

### User
| 필드 | 타입 | 설명 |
|------|------|------|
| id | int | |
| username | string | |
| nickname | string | 표시 이름 |
| email | string | |
| provider | `kakao` \| `local` | |
| provider_uid | string | 카카오 id 등 |
| created_at | datetime | |

### Game
| 필드 | 설명 |
|------|------|
| id, slug, name, name_ko | |
| short_name | 아이콘 플레이스홀더 글자 |
| color | `#rrggbb` |
| icon | URL 또는 null |

### Room
| 필드 | 설명 |
|------|------|
| id, title, description | |
| game | Game 객체 |
| owner | `{ id, username, nickname }` |
| max_members | 2~12 |
| status | `open` \| `closed` |
| approved_member_count | |
| my_membership_status | `pending`/`approved`/`rejected`/null |
| created_at, updated_at | |

### RoomMembership
| 필드 | 설명 |
|------|------|
| id, room_id | |
| user | Owner |
| status | `pending` \| `approved` \| `rejected` |
| created_at, updated_at | |

### ChatMessage
| 필드 | 설명 |
|------|------|
| id, room | |
| sender | Owner \| null (시스템) |
| message_type | `user` \| `system` |
| content | max 1000 |
| created_at | |

---

## 7. 전형 플로우

```
1) GET  /api/auth/kakao/login-url/
2) 브라우저 카카오 동의 → redirect ?code=
3) POST /api/auth/kakao/  { code }
4) GET  /api/games/
5) POST /api/rooms/  { title, game }
6) (다른 유저) POST /api/rooms/{id}/apply/
7) (방장) GET applications → POST memberships/{id}/approve/
8) WSS  connect  wss://.../ws/rooms/{id}/?token=...
9) 메시지  WSS 또는 POST /messages/
```

---

## 8. 헬스체크

### `GET /health/` 🔓

```json
{ "status": "ok" }
```

Swagger UI는 프로덕션(`DEBUG=False`)에서 비활성.  
기계 판독용 원본: `key/swagger_schema/schema.yaml` (로컬 생성본, git 제외 가능).
