from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction


class Game(models.Model):
    slug = models.SlugField('슬러그', max_length=50, unique=True)
    name = models.CharField('게임명', max_length=100, unique=True)
    name_ko = models.CharField('한국어명', max_length=100)
    short_name = models.CharField('약어', max_length=10, help_text='아이콘 플레이스홀더에 표시')
    color = models.CharField('브랜드 색', max_length=7, help_text='#rrggbb')
    icon = models.ImageField('아이콘', upload_to='games/', blank=True)
    is_active = models.BooleanField('활성', default=True)
    sort_order = models.PositiveSmallIntegerField('정렬 순서', default=0)
    created_at = models.DateTimeField('생성일', auto_now_add=True)
    updated_at = models.DateTimeField('수정일', auto_now=True)

    class Meta:
        verbose_name = '게임'
        verbose_name_plural = '게임'
        ordering = ['sort_order', 'id']

    def __str__(self):
        return self.name


class Room(models.Model):
    class Status(models.TextChoices):
        OPEN = 'open', '모집중'
        CLOSED = 'closed', '마감'

    class PlayTimeSlot(models.TextChoices):
        DAWN = 'dawn', '새벽 (00:00~06:00)'
        MORNING = 'morning', '오전 (06:00~12:00)'
        AFTERNOON = 'afternoon', '오후 (12:00~18:00)'
        EVENING = 'evening', '저녁 (18:00~24:00)'

    MAX_MEMBERS_LIMIT = 12
    DEFAULT_MAX_MEMBERS = 5

    title = models.CharField('제목', max_length=100)
    description = models.TextField('설명', blank=True)
    play_time_slot = models.CharField(
        '플레이 시간대',
        max_length=20,
        choices=PlayTimeSlot.choices,
        null=True,
        blank=True,
        help_text='함께 플레이할 선호 시간대. 기존 방은 미지정일 수 있습니다.',
    )
    game = models.ForeignKey(
        Game,
        on_delete=models.PROTECT,
        related_name='rooms',
        verbose_name='게임',
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_rooms',
        verbose_name='방장',
    )
    max_members = models.PositiveSmallIntegerField(
        '최대 인원',
        default=DEFAULT_MAX_MEMBERS,
        validators=[
            MinValueValidator(2),
            MaxValueValidator(MAX_MEMBERS_LIMIT),
        ],
        help_text=f'2~{MAX_MEMBERS_LIMIT}명, 기본 {DEFAULT_MAX_MEMBERS}명',
    )
    status = models.CharField(
        '상태',
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )
    created_at = models.DateTimeField('생성일', auto_now_add=True)
    updated_at = models.DateTimeField('수정일', auto_now=True)

    class Meta:
        verbose_name = '방'
        verbose_name_plural = '방'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} ({self.game.name})'

    @property
    def approved_member_count(self):
        return self.memberships.filter(status=RoomMembership.Status.APPROVED).count()

    @classmethod
    @transaction.atomic
    def create_with_owner(cls, *, owner, **kwargs):
        """방 생성과 동시에 방장을 approved 멤버로 등록."""
        room = cls.objects.create(owner=owner, **kwargs)
        RoomMembership.objects.create(
            room=room,
            user=owner,
            status=RoomMembership.Status.APPROVED,
        )
        return room


class RoomMembership(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', '대기'
        APPROVED = 'approved', '승인'
        REJECTED = 'rejected', '거절'

    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name='memberships',
        verbose_name='방',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='room_memberships',
        verbose_name='유저',
    )
    status = models.CharField(
        '상태',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField('신청일', auto_now_add=True)
    updated_at = models.DateTimeField('수정일', auto_now=True)

    class Meta:
        verbose_name = '방 멤버십'
        verbose_name_plural = '방 멤버십'
        constraints = [
            models.UniqueConstraint(
                fields=['room', 'user'],
                name='uniq_rooms_membership_room_user',
            ),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.room_id}:{self.user_id} ({self.status})'

    def clean(self):
        super().clean()
        if self.pk:
            previous = RoomMembership.objects.filter(pk=self.pk).values_list('status', flat=True).first()
            if previous == self.Status.REJECTED and self.status == self.Status.PENDING:
                raise ValidationError('거절된 신청은 재신청할 수 없습니다.')

    @classmethod
    def can_apply(cls, *, room, user) -> bool:
        """가입 신청 가능 여부. 거절 이력이 있으면 False."""
        existing = cls.objects.filter(room=room, user=user).first()
        if existing is None:
            return room.status == Room.Status.OPEN
        return False  # pending/approved/rejected 모두 재신청 불가
