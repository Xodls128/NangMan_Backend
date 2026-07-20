import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from apps.rooms.models import RoomMembership

from .models import ChatMessage
from .serializers import ChatMessageSerializer


class RoomChatConsumer(AsyncJsonWebsocketConsumer):
    """
    ws://host/ws/rooms/<room_id>/?token=<access>

    클라이언트 → 서버:
      {"type": "chat.message", "content": "안녕"}

    서버 → 클라이언트:
      {"type": "chat.message", "message": {...}}
      {"type": "room.deleted", "room_id": <int>}
      {"type": "error", "detail": "..."}
    """

    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.group_name = f'chat_room_{self.room_id}'
        user = self.scope.get('user')

        if user is None or user.is_anonymous:
            await self.close(code=4401)
            return

        if not await self._is_approved_member(user.id, self.room_id):
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        msg_type = content.get('type')
        if msg_type != 'chat.message':
            await self.send_json({'type': 'error', 'detail': '지원하지 않는 type 입니다.'})
            return

        raw = content.get('content', '')
        message_data, error = await self._create_message(
            room_id=self.room_id,
            user_id=self.scope['user'].id,
            content=raw,
        )
        if error:
            await self.send_json({'type': 'error', 'detail': error})
            return

        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'chat.message',
                'message': message_data,
            },
        )

    async def chat_message(self, event):
        await self.send_json({
            'type': 'chat.message',
            'message': event['message'],
        })

    async def room_deleted(self, event):
        await self.send_json({
            'type': 'room.deleted',
            'room_id': event['room_id'],
        })

    @database_sync_to_async
    def _is_approved_member(self, user_id, room_id) -> bool:
        return RoomMembership.objects.filter(
            room_id=room_id,
            user_id=user_id,
            status=RoomMembership.Status.APPROVED,
        ).exists()

    @database_sync_to_async
    def _create_message(self, room_id, user_id, content):
        text = (content or '').strip()
        if not text:
            return None, '메시지 내용을 입력하세요.'
        if len(text) > ChatMessage.MAX_CONTENT_LENGTH:
            return None, f'메시지는 {ChatMessage.MAX_CONTENT_LENGTH}자까지 가능합니다.'

        # 연결 이후 멤버십이 바뀌었을 수 있어 재확인
        if not RoomMembership.objects.filter(
            room_id=room_id,
            user_id=user_id,
            status=RoomMembership.Status.APPROVED,
        ).exists():
            return None, '승인된 방 멤버만 채팅할 수 있습니다.'

        message = ChatMessage.objects.create(
            room_id=room_id,
            sender_id=user_id,
            content=text,
        )
        message = ChatMessage.objects.select_related('sender').get(pk=message.pk)
        data = ChatMessageSerializer(message).data
        # JSON 직렬화 가능한 형태로 (datetime 등)
        return json.loads(json.dumps(data, default=str)), None
