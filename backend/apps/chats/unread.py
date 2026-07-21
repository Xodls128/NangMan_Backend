"""방별 미읽음 메시지 커서/카운트 헬퍼."""

from django.db.models import Count, F, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce

from apps.rooms.models import RoomMembership

from .models import ChatMessage


def latest_message_id(room_id: int) -> int | None:
    return (
        ChatMessage.objects.filter(room_id=room_id)
        .order_by('-id')
        .values_list('id', flat=True)
        .first()
    )


def unread_count_for_membership(*, room_id: int, user_id: int, last_read_message_id: int | None) -> int:
    cursor = last_read_message_id or 0
    return (
        ChatMessage.objects.filter(
            room_id=room_id,
            message_type=ChatMessage.MessageType.USER,
            id__gt=cursor,
        )
        .exclude(sender_id=user_id)
        .count()
    )


def annotate_unread_counts(queryset, user):
    """Room queryset에 `_unread_count` annotate (N+1 방지)."""
    last_read = Coalesce(
        Subquery(
            RoomMembership.objects.filter(
                room_id=OuterRef('pk'),
                user_id=user.id,
                status=RoomMembership.Status.APPROVED,
            ).values('last_read_message_id')[:1]
        ),
        Value(0),
    )
    return queryset.annotate(_last_read_id=last_read).annotate(
        _unread_count=Count(
            'chat_messages',
            filter=Q(
                chat_messages__message_type=ChatMessage.MessageType.USER,
                chat_messages__id__gt=F('_last_read_id'),
            )
            & ~Q(chat_messages__sender_id=user.id),
            distinct=True,
        ),
    )


def advance_last_read(*, room_id: int, user, message_id: int | None = None) -> RoomMembership | None:
    """
    approved 멤버십의 last_read_message_id를 단조 증가로 갱신.
    message_id가 None이면 방의 최신 메시지 id 사용.
    """
    membership = RoomMembership.objects.filter(
        room_id=room_id,
        user=user,
        status=RoomMembership.Status.APPROVED,
    ).first()
    if membership is None:
        return None

    target = message_id if message_id is not None else latest_message_id(room_id)
    if target is None:
        return membership

    current = membership.last_read_message_id or 0
    if target > current:
        membership.last_read_message_id = target
        membership.save(update_fields=['last_read_message_id', 'updated_at'])
    return membership


def init_last_read_on_join(membership: RoomMembership) -> None:
    """가입/승인 시 과거 메시지는 미읽음에 잡히지 않도록 커서를 최신으로 맞춤."""
    latest = latest_message_id(membership.room_id)
    if latest is None:
        return
    membership.last_read_message_id = latest
    membership.save(update_fields=['last_read_message_id', 'updated_at'])
