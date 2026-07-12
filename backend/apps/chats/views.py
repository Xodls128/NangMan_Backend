from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response

from apps.rooms.models import Room

from .models import ChatMessage
from .permissions import IsApprovedRoomMemberFromURL
from .serializers import ChatMessageCreateSerializer, ChatMessageSerializer


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
        output = ChatMessageSerializer(message, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)
