from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def broadcast_chat_message(room_id, message_data: dict) -> None:
    """REST로 저장된 메시지도 WebSocket 구독자에게 전달."""
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
