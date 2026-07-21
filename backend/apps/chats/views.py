from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.response import Response

from apps.rooms.models import Room

from .broadcast import broadcast_chat_message, serialize_message
from .models import ChatMessage
from .permissions import IsApprovedRoomMemberFromURL
from .serializers import ChatMessageCreateSerializer, ChatMessageSerializer
from .unread import advance_last_read


@extend_schema_view(
    get=extend_schema(
        tags=['chats'],
        summary='채팅 메시지 목록',
        description=(
            '방의 채팅 메시지를 시간순으로 조회합니다.\n\n'
            '- **승인(approved) 멤버만** 접근 가능\n'
            '- `after_id`를 주면 해당 ID보다 큰 메시지만 반환 (폴링/증분 조회용)\n'
            '- 실시간 수신은 WebSocket `ws://.../ws/rooms/{room_id}/?token=...` 사용\n\n'
            '## 읽음 처리 (자동)\n\n'
            '조회가 **성공하면** 호출한 유저의 읽음 커서가 해당 방의 '
            '**최신 메시지 ID**로 자동 갱신됩니다.\n\n'
            '채팅방을 열어서 메시지를 본다 = 읽었다는 카카오톡식 UX입니다. '
            '별도로 `POST /api/rooms/{id}/read/`를 호출할 필요가 **없습니다**.\n\n'
            '## 권장 사용\n\n'
            '| 상황 | 호출 |\n'
            '|------|------|\n'
            '| 채팅방 입장(기본) | 이 API (`GET .../messages/`)만 호출 → 뱃지 자동 소멸 |\n'
            '| 방 목록 뱃지 표시 | `GET /api/rooms/mine/`의 `unread_count` |\n'
            '| 메시지 조회 없이 읽음만 | `POST /api/rooms/{id}/read/` |\n\n'
            '`after_id`로 증분 조회해도 커서는 방 **전체 최신** 기준으로 앞으로 갑니다. '
            '(방에 들어와 메시지를 보고 있는 상태로 간주)\n\n'
            '이 API와 `POST .../read/`를 함께 써도 커서는 단조 증가라 중복 호출이 안전합니다.'
        ),
        parameters=[
            OpenApiParameter(
                name='after_id',
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description='이 ID보다 큰 메시지만 조회',
            ),
        ],
        responses={
            200: ChatMessageSerializer(many=True),
            403: OpenApiResponse(description='승인된 방 멤버가 아님'),
        },
    ),
    post=extend_schema(
        tags=['chats'],
        summary='채팅 메시지 전송 (REST)',
        description=(
            'REST로 메시지를 저장합니다. 연결된 WebSocket 구독자에게도 브로드캐스트됩니다.\n\n'
            '- **승인 멤버만** 가능\n'
            '- content는 공백 불가, 최대 1000자\n'
            '- 일반적인 실시간 전송은 WebSocket을 권장합니다.'
        ),
        request=ChatMessageCreateSerializer,
        responses={
            201: ChatMessageSerializer,
            400: OpenApiResponse(description='내용 검증 실패'),
            403: OpenApiResponse(description='승인된 방 멤버가 아님'),
        },
    ),
)
class RoomMessageListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/rooms/{room_id}/messages/
    POST /api/rooms/{room_id}/messages/
    승인된 멤버만 접근. ?after_id= 로 이후 메시지만 조회 가능.
    """

    permission_classes = [IsApprovedRoomMemberFromURL]

    def get_room(self):
        return get_object_or_404(Room, pk=self.kwargs['room_id'])

    def get_queryset(self):
        qs = (
            ChatMessage.objects.filter(room_id=self.kwargs['room_id'])
            .select_related('sender')
            .order_by('created_at', 'id')
        )
        after_id = self.request.query_params.get('after_id')
        if after_id is not None:
            qs = qs.filter(id__gt=after_id)
        return qs

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ChatMessageCreateSerializer
        return ChatMessageSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['room'] = self.get_room()
        return context

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        advance_last_read(room_id=self.kwargs['room_id'], user=request.user)
        return response

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.save()
        payload = serialize_message(message)
        broadcast_chat_message(message.room_id, payload)
        return Response(payload, status=status.HTTP_201_CREATED)
