from rest_framework.permissions import BasePermission

from apps.rooms.models import RoomMembership


class IsApprovedRoomMemberFromURL(BasePermission):
    """URL의 room_id에 해당하는 방의 승인 멤버만 허용."""

    message = '승인된 방 멤버만 채팅할 수 있습니다.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        room_id = view.kwargs.get('room_id')
        if room_id is None:
            return False
        return RoomMembership.objects.filter(
            room_id=room_id,
            user=request.user,
            status=RoomMembership.Status.APPROVED,
        ).exists()
