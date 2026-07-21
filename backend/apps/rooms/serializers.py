from django.db.models import Count, Q
from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.serializers import PublicUserSerializer

from .discord_validation import normalize_discord_invite_url
from .models import Game, Room, RoomMembership


def user_can_view_discord_invite(room: Room, context) -> bool:
    request = context.get('request')
    if not request or not request.user.is_authenticated:
        return False
    if room.owner_id == request.user.id:
        return True
    status_map = context.get('membership_status_map')
    if status_map is not None:
        return status_map.get(room.id) == RoomMembership.Status.APPROVED
    return RoomMembership.objects.filter(
        room=room,
        user=request.user,
        status=RoomMembership.Status.APPROVED,
    ).exists()


class GameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Game
        fields = (
            'id',
            'slug',
            'name',
            'name_ko',
            'short_name',
            'color',
            'icon',
        )
        read_only_fields = fields


class RoomSerializer(serializers.ModelSerializer):
    owner = PublicUserSerializer(read_only=True)
    game = GameSerializer(read_only=True)
    play_time_label = serializers.CharField(
        source='get_play_time_slot_display',
        read_only=True,
        allow_null=True,
    )
    approved_member_count = serializers.SerializerMethodField()
    my_membership_status = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    discord_invite_url = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = (
            'id',
            'title',
            'description',
            'play_time_slot',
            'play_time_label',
            'game',
            'owner',
            'max_members',
            'status',
            'discord_invite_url',
            'approved_member_count',
            'my_membership_status',
            'unread_count',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields

    @extend_schema_field(serializers.IntegerField())
    def get_approved_member_count(self, obj):
        if hasattr(obj, '_approved_count'):
            return obj._approved_count
        return obj.approved_member_count

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_my_membership_status(self, obj):
        status_map = self.context.get('membership_status_map')
        if status_map is not None:
            return status_map.get(obj.id)
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        membership = obj.memberships.filter(user=request.user).only('status').first()
        return membership.status if membership else None

    @extend_schema_field(
        serializers.IntegerField(
            help_text=(
                '미읽음 타인 유저 메시지 수. '
                'GET /rooms/mine/ 에서만 의미 있음(그 외 0). '
                '0이면 뱃지 숨김.'
            ),
        )
    )
    def get_unread_count(self, obj):
        """mine에서 annotate된 값. 그 외 list/retrieve 등은 0."""
        if hasattr(obj, '_unread_count'):
            return int(obj._unread_count or 0)
        return 0

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_discord_invite_url(self, obj):
        if not user_can_view_discord_invite(obj, self.context):
            return None
        return obj.discord_invite_url or None


class RoomCreateSerializer(serializers.ModelSerializer):
    play_time_slot = serializers.ChoiceField(
        choices=Room.PlayTimeSlot.choices,
        required=True,
        allow_blank=False,
        allow_null=False,
        error_messages={
            'required': '플레이 시간대를 선택해 주세요.',
            'invalid_choice': '올바른 플레이 시간대를 선택해 주세요.',
        },
    )
    game = serializers.SlugRelatedField(
        slug_field='slug',
        queryset=Game.objects.filter(is_active=True),
        error_messages={
            'does_not_exist': '존재하지 않거나 비활성화된 게임입니다.',
            'invalid': '게임 슬러그가 올바르지 않습니다.',
        },
    )
    discord_invite_url = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        max_length=512,
    )

    class Meta:
        model = Room
        fields = (
            'title',
            'description',
            'game',
            'play_time_slot',
            'max_members',
            'discord_invite_url',
        )

    def validate_discord_invite_url(self, value):
        try:
            return normalize_discord_invite_url(value)
        except ValidationError as exc:
            raise serializers.ValidationError(exc.messages[0]) from exc

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


class RoomUpdateSerializer(serializers.ModelSerializer):
    discord_invite_url = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        max_length=512,
    )

    class Meta:
        model = Room
        fields = ('discord_invite_url',)

    def validate_discord_invite_url(self, value):
        try:
            return normalize_discord_invite_url(value)
        except ValidationError as exc:
            raise serializers.ValidationError(exc.messages[0]) from exc

    def update(self, instance, validated_data):
        if 'discord_invite_url' in validated_data:
            instance.discord_invite_url = validated_data['discord_invite_url']
            instance.save(update_fields=['discord_invite_url', 'updated_at'])
        return instance


class RoomMembershipSerializer(serializers.ModelSerializer):
    user = PublicUserSerializer(read_only=True)
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


class RoomReadSerializer(serializers.Serializer):
    last_read_message_id = serializers.IntegerField(
        required=False,
        min_value=1,
        help_text=(
            '이 메시지 ID까지 읽음 처리. '
            '생략 시 방의 최신 메시지 ID로 설정(방 전체 읽음). '
            '현재 커서보다 작으면 무시됩니다.'
        ),
    )


class RoomReadResponseSerializer(serializers.Serializer):
    room_id = serializers.IntegerField(help_text='읽음 처리한 방 ID')
    last_read_message_id = serializers.IntegerField(
        allow_null=True,
        help_text='갱신된 읽음 커서. 메시지가 없으면 null',
    )
    unread_count = serializers.IntegerField(
        help_text='갱신 후 미읽음 개수(보통 0). 로컬 뱃지 즉시 반영에 사용',
    )


def rooms_with_counts():
    return Room.objects.select_related('owner', 'game').annotate(
        _approved_count=Count(
            'memberships',
            filter=Q(memberships__status=RoomMembership.Status.APPROVED),
        )
    )
