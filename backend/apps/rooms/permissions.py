from rest_framework.permissions import BasePermission


class IsRoomOwner(BasePermission):
    """방장만 허용. obj가 Room이거나 room FK를 가진 객체."""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        room = getattr(obj, 'room', obj)
        return room.owner_id == request.user.id


class IsApprovedRoomMember(BasePermission):
    """해당 방의 승인된 멤버만 허용. (채팅 등에서 사용 예정)"""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        from .models import RoomMembership

        room = getattr(obj, 'room', obj)
        return RoomMembership.objects.filter(
            room=room,
            user=request.user,
            status=RoomMembership.Status.APPROVED,
        ).exists()
