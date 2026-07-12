from django.db.models import Count, Q
from rest_framework import serializers

from .models import Room, RoomMembership


class OwnerSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    nickname = serializers.CharField()


class RoomSerializer(serializers.ModelSerializer):
    owner = OwnerSerializer(read_only=True)
    approved_member_count = serializers.SerializerMethodField()
    my_membership_status = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = (
            'id',
            'title',
            'description',
            'game_name',
            'owner',
            'max_members',
            'status',
            'approved_member_count',
            'my_membership_status',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields

    def get_approved_member_count(self, obj):
        if hasattr(obj, '_approved_count'):
            return obj._approved_count
        return obj.approved_member_count

    def get_my_membership_status(self, obj):
        status_map = self.context.get('membership_status_map')
        if status_map is not None:
            return status_map.get(obj.id)
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        membership = obj.memberships.filter(user=request.user).only('status').first()
        return membership.status if membership else None


class RoomCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = (
            'title',
            'description',
            'game_name',
            'max_members',
        )

    def validate_max_members(self, value):
        if value > Room.MAX_MEMBERS_LIMIT:
            raise serializers.ValidationError(
                f'최대 인원은 {Room.MAX_MEMBERS_LIMIT}명까지 가능합니다.'
            )
        if value < 2:
            raise serializers.ValidationError('최대 인원은 최소 2명입니다.')
        return value

    def create(self, validated_data):
        return Room.create_with_owner(
            owner=self.context['request'].user,
            **validated_data,
        )


class RoomMembershipSerializer(serializers.ModelSerializer):
    user = OwnerSerializer(read_only=True)
    room_id = serializers.IntegerField(source='room.id', read_only=True)

    class Meta:
        model = RoomMembership
        fields = (
            'id',
            'room_id',
            'user',
            'status',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


def rooms_with_counts():
    return Room.objects.select_related('owner').annotate(
        _approved_count=Count(
            'memberships',
            filter=Q(memberships__status=RoomMembership.Status.APPROVED),
        )
    )
