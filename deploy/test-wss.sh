#!/usr/bin/env bash
# 프로덕션 WSS 스모크 테스트 (EC2에서 실행)
# 사용: bash deploy/test-wss.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

API_BASE="${API_BASE:-https://api.gamemate.kr}"
ORIGIN="${ORIGIN:-https://gamemate.kr}"
WS_HOST="${WS_HOST:-api.gamemate.kr}"

echo "==> 테스트용 Game / User / Room 준비"
SETUP_OUT="$(docker compose exec -T web python manage.py shell <<'PY'
import json
from django.contrib.auth import get_user_model
from apps.rooms.models import Game, Room

User = get_user_model()
game, _ = Game.objects.get_or_create(
    slug='wss-test',
    defaults={
        'name': 'WSS Test Game',
        'name_ko': 'WSS테스트',
        'short_name': 'WSS',
        'color': '#3366ff',
        'is_active': True,
        'sort_order': 999,
    },
)
user, created = User.objects.get_or_create(
    username='wss_tester',
    defaults={
        'provider': User.Provider.LOCAL,
        'provider_uid': 'local_wss_tester',
        'nickname': 'wss',
    },
)
user.set_password('wss_test_pass_123')
if not user.nickname:
    user.nickname = 'wss'
if user.provider_uid != 'local_wss_tester':
    user.provider = User.Provider.LOCAL
    user.provider_uid = 'local_wss_tester'
user.save()

room = Room.objects.filter(owner=user, title='WSS Probe').first()
if room is None:
    room = Room.create_with_owner(
        owner=user,
        title='WSS Probe',
        description='websocket smoke test',
        game=game,
        max_members=5,
    )

print('SETUP_JSON:' + json.dumps({'user_id': user.id, 'room_id': room.id, 'created_user': created}))
PY
)"

echo "$SETUP_OUT"
SETUP_JSON="$(printf '%s\n' "$SETUP_OUT" | sed -n 's/^SETUP_JSON://p' | tail -1)"
if [ -z "$SETUP_JSON" ]; then
  echo "setup JSON parse failed"
  exit 1
fi
ROOM_ID="$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['room_id'])" "$SETUP_JSON")"

echo "==> JWT 발급"
TOKEN_JSON="$(curl -sf -X POST "${API_BASE}/api/auth/token/" \
  -H 'Content-Type: application/json' \
  -d '{"username":"wss_tester","password":"wss_test_pass_123"}')"
ACCESS="$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['access'])" "$TOKEN_JSON")"
echo "access token length: ${#ACCESS}"

echo "==> websockets 클라이언트 준비"
python3 -m pip install --user -q websockets >/dev/null

echo "==> WSS 연결 + 메시지 라운드트립"
WS_URL="wss://${WS_HOST}/ws/rooms/${ROOM_ID}/?token=${ACCESS}"
python3 - "$WS_URL" "$ORIGIN" <<'PY'
import asyncio, json, sys
import websockets

url, origin = sys.argv[1], sys.argv[2]

async def main():
    async with websockets.connect(url, origin=origin, open_timeout=15) as ws:
        print("CONNECTED")
        payload = {"type": "chat.message", "content": "wss smoke hello"}
        await ws.send(json.dumps(payload))
        raw = await asyncio.wait_for(ws.recv(), timeout=10)
        data = json.loads(raw)
        print("RECV:", json.dumps(data, ensure_ascii=False))
        if data.get("type") != "chat.message":
            raise SystemExit(f"unexpected type: {data}")
        if data.get("message", {}).get("content") != "wss smoke hello":
            raise SystemExit(f"content mismatch: {data}")
        print("WSS_OK")

asyncio.run(main())
PY

echo "==> 완료: WSS 정상"
