from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Game, Room, RoomMembership
from .permissions import IsRoomOwner
from .serializers import (
    GameSerializer,
    RoomCreateSerializer,
    RoomMembershipSerializer,
    RoomSerializer,
    rooms_with_counts,
)
from apps.chats.broadcast import notify_member_joined


@extend_schema_view(
    list=extend_schema(
        tags=['games'],
        summary='게임 목록 조회',
        description=(
            '활성화된 게임 카탈로그를 정렬 순서대로 조회합니다.\n\n'
            '- **비로그인 가능**\n'
            '- 방 목록 필터 바와 방 생성 게임 선택에 사용됩니다.\n'
            '- `icon`이 null이면 프론트에서 `color`+`short_name` 플레이스홀더로 표시합니다.'
        ),
        responses={200: GameSerializer(many=True)},
    ),
)
class GameViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = GameSerializer
    queryset = Game.objects.filter(is_active=True)
    pagination_class = None
    http_method_names = ['get', 'head', 'options']


@extend_schema_view(
    list=extend_schema(
        tags=['rooms'],
        summary='방 목록 조회',
        description=(
            '전체 방 목록을 최신순으로 조회합니다.\n\n'
            '- **비로그인 가능**\n'
            '- `?game=<slug>`로 특정 게임의 방만 필터링할 수 있습니다.\n'
            '- 로그인 시 각 방에 `my_membership_status`가 포함됩니다.\n'
            '- 비로그인 시 `my_membership_status`는 null입니다.'
        ),
        parameters=[
            OpenApiParameter(
                name='game',
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description='게임 슬러그 (예: lol, valorant)',
            ),
        ],
        responses={200: RoomSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=['rooms'],
        summary='방 상세 조회',
        description='단일 방의 상세 정보와 내 멤버십 상태를 조회합니다.',
        responses={
            200: RoomSerializer,
            404: OpenApiResponse(description='방이 존재하지 않음'),
        },
    ),
    create=extend_schema(
        tags=['rooms'],
        summary='방 생성',
        description=(
            '새 방을 생성합니다. 생성한 유저가 방장이 됩니다.\n\n'
            '- 생성과 동시에 방장은 `approved` 멤버로 등록됩니다.\n'
            '- `game`: 게임 슬러그 (`GET /api/games/` 참고)\n'
            '- `max_members`: 2~12, 기본 5'
        ),
        request=RoomCreateSerializer,
        responses={201: RoomSerializer},
    ),
    mine=extend_schema(
        tags=['rooms'],
        summary='내가 속한 방 목록',
        description=(
            '내가 **승인(approved)** 된 방만 조회합니다.\n\n'
            '- 방장으로 만든 방과, 가입 수락된 방이 포함됩니다.'
        ),
        responses={200: RoomSerializer(many=True)},
    ),
    apply=extend_schema(
        tags=['rooms'],
        summary='방 가입 신청',
        description=(
            '모집 중인 방에 가입을 신청합니다. 상태는 `pending`입니다.\n\n'
            '제한:\n'
            '- 방장 본인은 신청 불가\n'
            '- `closed` 방 또는 정원 초과 시 불가\n'
            '- 이미 pending/approved/rejected 이력이 있으면 재신청 불가'
        ),
        request=None,
        responses={
            201: RoomMembershipSerializer,
            400: OpenApiResponse(description='신청 불가 (이미 신청, 마감, 정원 등)'),
        },
    ),
    applications=extend_schema(
        tags=['rooms'],
        summary='가입 신청 목록 (방장)',
        description=(
            '해당 방의 **대기(pending)** 신청 목록을 조회합니다.\n\n'
            '- 방장만 호출 가능\n'
            '- 채팅방 우측 패널의 신청자 목록에 사용'
        ),
        responses={
            200: RoomMembershipSerializer(many=True),
            403: OpenApiResponse(description='방장이 아님'),
        },
    ),
    members=extend_schema(
        tags=['rooms'],
        summary='참여 중 멤버 목록',
        description=(
            '해당 방의 **승인(approved)** 멤버 목록을 조회합니다.\n\n'
            '- 승인된 방 멤버만 호출 가능\n'
            '- 채팅방 우측 패널(방장·비방장 공통)에 사용'
        ),
        responses={
            200: RoomMembershipSerializer(many=True),
            403: OpenApiResponse(description='승인된 방 멤버가 아님'),
        },
    ),
)
class RoomViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_permissions(self):
        if self.action == 'list':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = rooms_with_counts()
        if self.action == 'list':
            game_slug = self.request.query_params.get('game')
            if game_slug:
                qs = qs.filter(game__slug=game_slug)
        return qs

    def get_serializer_class(self):
        if self.action == 'create':
            return RoomCreateSerializer
        return RoomSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        request = self.request
        if not request.user.is_authenticated:
            return context

        room_ids = []
        if self.action == 'list':
            room_ids = list(
                self.filter_queryset(self.get_queryset()).values_list('id', flat=True)
            )
        elif self.action == 'mine':
            room_ids = list(
                self.filter_queryset(self.get_queryset())
                .filter(
                    memberships__user=request.user,
                    memberships__status=RoomMembership.Status.APPROVED,
                )
                .values_list('id', flat=True)
            )
        elif self.action in ('retrieve', 'members', 'applications', 'apply'):
            room_ids = [self.kwargs['pk']]

        if room_ids:
            memberships = RoomMembership.objects.filter(
                user=request.user,
                room_id__in=room_ids,
            ).values_list('room_id', 'status')
            context['membership_status_map'] = dict(memberships)
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        room = serializer.save()
        room = rooms_with_counts().get(pk=room.pk)
        output = RoomSerializer(
            room,
            context={
                **self.get_serializer_context(),
                'membership_status_map': {room.id: RoomMembership.Status.APPROVED},
            },
        )
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def mine(self, request):
        qs = self.filter_queryset(self.get_queryset()).filter(
            memberships__user=request.user,
            memberships__status=RoomMembership.Status.APPROVED,
        ).distinct()
        page = self.paginate_queryset(qs)
        context = self.get_serializer_context()
        if page is not None:
            serializer = RoomSerializer(page, many=True, context=context)
            return self.get_paginated_response(serializer.data)
        serializer = RoomSerializer(qs, many=True, context=context)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def apply(self, request, pk=None):
        room = self.get_object()

        if room.owner_id == request.user.id:
            raise ValidationError('방장은 자신의 방에 가입 신청할 수 없습니다.')
        if room.status != Room.Status.OPEN:
            raise ValidationError('모집이 마감된 방입니다.')
        if not RoomMembership.can_apply(room=room, user=request.user):
            raise ValidationError('이미 신청했거나 거절된 방에는 다시 신청할 수 없습니다.')
        if room.approved_member_count >= room.max_members:
            raise ValidationError('정원에 도달한 방입니다.')

        membership = RoomMembership.objects.create(
            room=room,
            user=request.user,
            status=RoomMembership.Status.PENDING,
        )
        return Response(
            RoomMembershipSerializer(membership).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['get'])
    def applications(self, request, pk=None):
        room = self.get_object()
        if room.owner_id != request.user.id:
            raise PermissionDenied('방장만 신청 목록을 볼 수 있습니다.')

        qs = room.memberships.filter(
            status=RoomMembership.Status.PENDING,
        ).select_related('user')
        return Response(RoomMembershipSerializer(qs, many=True).data)

    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        room = self.get_object()
        is_member = RoomMembership.objects.filter(
            room=room,
            user=request.user,
            status=RoomMembership.Status.APPROVED,
        ).exists()
        if not is_member:
            raise PermissionDenied('승인된 방 멤버만 멤버 목록을 볼 수 있습니다.')

        qs = (
            room.memberships.filter(status=RoomMembership.Status.APPROVED)
            .select_related('user')
            .order_by('created_at')
        )
        return Response(RoomMembershipSerializer(qs, many=True).data)


@extend_schema_view(
    approve=extend_schema(
        tags=['rooms'],
        summary='가입 신청 수락 (방장)',
        description=(
            'pending 상태의 멤버십을 `approved`로 변경합니다.\n\n'
            '- 해당 방의 방장만 가능\n'
            '- 정원에 도달하면 방 상태가 `closed`로 바뀔 수 있습니다.\n'
            '- 수락 시 채팅방에 입장 안내(시스템) 메시지가 남고 WebSocket으로 푸시됩니다.'
        ),
        request=None,
        responses={
            200: RoomMembershipSerializer,
            400: OpenApiResponse(description='대기 신청이 아니거나 정원 초과'),
            403: OpenApiResponse(description='방장이 아님'),
        },
    ),
    reject=extend_schema(
        tags=['rooms'],
        summary='가입 신청 거절 (방장)',
        description=(
            'pending 상태의 멤버십을 `rejected`로 변경합니다.\n\n'
            '- 거절된 유저는 같은 방에 재신청할 수 없습니다.'
        ),
        request=None,
        responses={
            200: RoomMembershipSerializer,
            400: OpenApiResponse(description='대기 신청이 아님'),
            403: OpenApiResponse(description='방장이 아님'),
        },
    ),
)
class MembershipViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, IsRoomOwner]
    queryset = RoomMembership.objects.select_related('room', 'user')
    serializer_class = RoomMembershipSerializer
    http_method_names = ['post', 'head', 'options']

    def get_object(self):
        obj = get_object_or_404(self.get_queryset(), pk=self.kwargs['pk'])
        self.check_object_permissions(self.request, obj)
        return obj

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        membership = self.get_object()

        if membership.status != RoomMembership.Status.PENDING:
            raise ValidationError('대기 중인 신청만 수락할 수 있습니다.')

        room = membership.room
        if room.approved_member_count >= room.max_members:
            raise ValidationError('정원에 도달한 방입니다.')

        with transaction.atomic():
            membership.status = RoomMembership.Status.APPROVED
            membership.save(update_fields=['status', 'updated_at'])
            if room.approved_member_count >= room.max_members:
                room.status = Room.Status.CLOSED
                room.save(update_fields=['status', 'updated_at'])

        notify_member_joined(room=room, user=membership.user)
        return Response(RoomMembershipSerializer(membership).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        membership = self.get_object()

        if membership.status != RoomMembership.Status.PENDING:
            raise ValidationError('대기 중인 신청만 거절할 수 있습니다.')

        membership.status = RoomMembership.Status.REJECTED
        membership.full_clean()
        membership.save(update_fields=['status', 'updated_at'])
        return Response(RoomMembershipSerializer(membership).data)
