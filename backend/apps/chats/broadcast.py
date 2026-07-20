from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import ChatMessage
from .serializers import ChatMessageSerializer


def serialize_message(message: ChatMessage) -> dict:
    message = ChatMessage.objects.select_related('sender').get(pk=message.pk)
    data = ChatMessageSerializer(message).data
    # datetime 등 JSON 직렬화
    import json

    return json.loads(json.dumps(data, default=str))


def broadcast_chat_message(room_id, message_data: dict) -> None:
    """REST/시스템으로 저장된 메시지도 WebSocket 구독자에게 전달."""
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    async_to_sync(channel_layer.group_send)(
        f'chat_room_{room_id}',
        {
            'type': 'chat.message',
            'message': message_data,
        },
    )


def create_system_message(*, room, content: str, related_user=None) -> ChatMessage:
    """
    시스템 안내 메시지를 저장하고 접속 중인 멤버에게 브로드캐스트합니다.
    related_user가 있으면 sender로 기록(누가 입장했는지 추적용).
    """
    message = ChatMessage.objects.create(
        room=room,
        sender=related_user,
        message_type=ChatMessage.MessageType.SYSTEM,
        content=content,
    )
    broadcast_chat_message(room.id, serialize_message(message))
    return message


def notify_member_joined(*, room, user) -> ChatMessage:
    display = (user.nickname or user.username).strip() or user.username
    return create_system_message(
        room=room,
        content=f'{display}님이 방에 입장했습니다.',
        related_user=user,
    )


def notify_member_left(*, room, user) -> ChatMessage:
    display = (user.nickname or user.username).strip() or user.username
    return create_system_message(
        room=room,
        content=f'{display}님이 방을 나갔습니다.',
        related_user=user,
    )


def broadcast_room_deleted(room_id: int) -> None:
    """방 삭제 시 채팅 WebSocket 구독자에게 알립니다."""
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    async_to_sync(channel_layer.group_send)(
        f'chat_room_{room_id}',
        {
            'type': 'room.deleted',
            'room_id': room_id,
        },
    )
