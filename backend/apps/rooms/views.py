from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Room, RoomMembership
from .permissions import IsRoomOwner
from .serializers import (
    RoomCreateSerializer,
    RoomMembershipSerializer,
    RoomSerializer,
    rooms_with_counts,
)


@extend_schema_view(
    list=extend_schema(tags=['rooms']),
    retrieve=extend_schema(tags=['rooms']),
    create=extend_schema(tags=['rooms']),
    mine=extend_schema(tags=['rooms']),
    apply=extend_schema(tags=['rooms']),
    applications=extend_schema(tags=['rooms']),
)
class RoomViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        return rooms_with_counts()

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
        elif self.action == 'retrieve':
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


@extend_schema_view(
    approve=extend_schema(tags=['rooms']),
    reject=extend_schema(tags=['rooms']),
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
