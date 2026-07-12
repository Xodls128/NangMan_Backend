from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.response import Response

from apps.rooms.models import Room

from .broadcast import broadcast_chat_message
from .models import ChatMessage
from .permissions import IsApprovedRoomMemberFromURL
from .serializers import ChatMessageCreateSerializer, ChatMessageSerializer


@extend_schema_view(
    get=extend_schema(
        tags=['chats'],
        summary='채팅 메시지 목록',
        description=(
            '방의 채팅 메시지를 시간순으로 조회합니다.\n\n'
            '- **승인(approved) 멤버만** 접근 가능\n'
            '- `after_id`를 주면 해당 ID보다 큰 메시지만 반환 (폴링/증분 조회용)\n'
            '- 실시간 수신은 WebSocket `ws://.../ws/rooms/{room_id}/?token=...` 사용'
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

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.save()
        message = ChatMessage.objects.select_related('sender').get(pk=message.pk)
        output = ChatMessageSerializer(message, context=self.get_serializer_context())
        broadcast_chat_message(message.room_id, output.data)
        return Response(output.data, status=status.HTTP_201_CREATED)
