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
{ "nickname": "게이머닉", "password": "...", "profile_avatar": "05" }
```

| 필드 | 설명 |
|------|------|
| `nickname`, `password` | 필수 |
| `profile_avatar` | 선택 (`01`~`10`). **신규 가입 시에만** 저장. 기존 닉네임 로그인 시 **무시** (프로필 변경 불가) |

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

**응답 200:** `User` 객체 (`profile_avatar` 포함, `01`~`10`)

프로필 이미지는 API가 URL을 주지 않고 **아바타 ID(`01`~`10`)만** 반환합니다. 실제 이미지 표시는 클라이언트가 ID로 매핑합니다.

---

### `PATCH /api/auth/me/` 🔒

내 프로필 수정. **닉네임은 변경 불가**, `profile_avatar`만 수정합니다.

**요청**
```json
{ "profile_avatar": "05" }
```

| `profile_avatar` | 아바타 ID (`01` ~ `10`) |

**응답 200:** 갱신된 `User`

---

## 2. 게임 (games)

### `GET /api/games/` 🔓

활성 게임 카탈로그 (정렬순). 기본 시드 6종 + **`etc`(기타)**.

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
| discord_invite_url | | 선택. `https://discord.gg/...` 또는 `https://discord.com/invite/...` |

**응답 201:** `Room`

`discord_invite_url`은 **방장** 또는 **approved 멤버**에게만 응답에 포함됩니다. 그 외는 `null`.

---

### `PATCH /api/rooms/{id}/` 🔒 (방장)

방장만 호출. 현재 **디스코드 초대 링크**만 수정 가능.

**요청**
```json
{ "discord_invite_url": "https://discord.gg/example" }
```

| 값 | 의미 |
|----|------|
| 유효한 https 디스코드 초대 URL | 저장 |
| `""` / `null` | 링크 삭제 |
| 필드 생략 | 변경 없음 |

**응답 200:** `Room`

**403:** 방장 아님

---

방 목록·상세 응답에는 선택값 `play_time_slot`과 표시 문구
`play_time_label`(예: `저녁 (18:00~24:00)`)이 함께 포함됩니다.
기존 방은 두 값이 `null`일 수 있습니다.

---

### `GET /api/rooms/mine/` 🔒

내가 **approved**인 방 목록.

각 방에 `unread_count`(내가 안 읽은 **타인 유저 메시지** 수)가 포함됩니다.
`0`이면 뱃지를 숨기면 됩니다. 본인 메시지·시스템 메시지는 카운트하지 않습니다.
전체 방 목록(`GET /api/rooms/`)의 `unread_count`는 항상 `0`이므로, 뱃지는 **이 API만** 사용하세요.

**권장 흐름:** 목록 화면 → `mine`으로 뱃지 표시 → 채팅방 입장 시 `GET .../messages/`(자동 읽음) → 다시 `mine`이면 해당 방 `0`.

---

### `POST /api/rooms/{id}/read/` 🔒

해당 방의 읽음 커서를 **명시적으로** 갱신합니다. **approved 멤버만** 가능.

| 구분 | 역할 |
|------|------|
| `GET .../messages/` | 채팅방 입장(메시지 조회) 시 **자동** 읽음 — 기본 경로 |
| `POST .../read/` | 메시지 목록을 조회하지 **않고** 커서만 갱신 — 보조 |

**쓰면 좋은 경우:** WS만 수신 중일 때, 포그라운드 전환 시 동기화, focus 시 뱃지 제거, 특정 ID까지 읽음 맞춤.

**요청** (body 선택)
```json
{ "last_read_message_id": 123 }
```

| 필드 | 필수 | 설명 |
|------|------|------|
| last_read_message_id | | 생략 시 방의 최신 메시지 ID. 현재 커서보다 작으면 무시(단조 증가) |

**응답 200**
```json
{ "room_id": 1, "last_read_message_id": 123, "unread_count": 0 }
```

**403:** 승인된 멤버 아님

일반 채팅방 입장에서는 `messages`만으로 충분합니다. `read`와 함께 써도 안전합니다.

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

조회 성공 시 해당 유저의 읽음 커서가 방의 **최신 메시지 ID**로 자동 갱신됩니다.
채팅방 입장의 기본 읽음 경로이며, 별도 `POST .../read/`는 필요 없습니다.
`after_id` 폴링이어도 커서는 방 전체 최신 기준으로 전진합니다.

**응답 200:** `ChatMessage[]`  
각 메시지의 `sender`에 `profile_avatar`(`01`~`10`)가 포함됩니다. 메시지에 아바타 필드를 따로 두지 않고, 보낸 사람 요약에 넣습니다.

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
    "sender": {
      "id": 1,
      "username": "...",
      "nickname": "...",
      "profile_avatar": "05"
    },
    "message_type": "user",
    "content": "안녕",
    "created_at": "2026-07-18T04:19:00+09:00"
  }
}
```

`message_type`: `user` | `system` (입장 안내 등)  
`sender.profile_avatar`: 아바타 ID (`01`~`10`). 이미지 URL이 아니라 ID만 전달하며, 표시는 클라이언트가 매핑합니다.

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
| profile_avatar | string (`01`~`10`) | 프로필 아바타 ID (이미지 URL 아님) |
| created_at | datetime | |

### PublicUser (Owner / sender / membership.user)
| 필드 | 타입 | 설명 |
|------|------|------|
| id | int | |
| username | string | |
| nickname | string | 표시 이름 |
| profile_avatar | string (`01`~`10`) | 프로필 아바타 ID |

채팅·방·멤버십 등 공개 유저 요약에 공통으로 쓰입니다. REST 메시지 목록/생성과 WebSocket `chat.message`의 `sender`가 이 형태입니다.

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
| owner | PublicUser |
| max_members | 2~12 |
| status | `open` \| `closed` |
| discord_invite_url | 방장·approved 멤버에게만 URL, 그 외 `null` |
| approved_member_count | |
| my_membership_status | `pending`/`approved`/`rejected`/null |
| unread_count | 미읽음 타인 유저 메시지 수 (`GET /rooms/mine/`에서 의미 있음, 그 외 0) |
| created_at, updated_at | |

### RoomMembership
| 필드 | 설명 |
|------|------|
| id, room_id | |
| user | PublicUser |
| status | `pending` \| `approved` \| `rejected` |
| created_at, updated_at | |

### ChatMessage
| 필드 | 설명 |
|------|------|
| id, room | |
| sender | PublicUser \| null (시스템) |
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
