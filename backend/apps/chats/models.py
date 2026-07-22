from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator
from django.db import models


class ChatMessage(models.Model):
    class MessageType(models.TextChoices):
        USER = 'user', '유저'
        SYSTEM = 'system', '시스템'

    MAX_CONTENT_LENGTH = 1000

    room = models.ForeignKey(
        'rooms.Room',
        on_delete=models.CASCADE,
        related_name='chat_messages',
        verbose_name='방',
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_messages',
        verbose_name='보낸 사람',
        null=True,
        blank=True,
        help_text='시스템 안내 메시지는 비울 수 있습니다.',
    )
    message_type = models.CharField(
        '메시지 유형',
        max_length=20,
        choices=MessageType.choices,
        default=MessageType.USER,
    )
    content = models.TextField(
        '내용',
        validators=[MaxLengthValidator(MAX_CONTENT_LENGTH)],
    )
    created_at = models.DateTimeField('전송 시각', auto_now_add=True)

    class Meta:
        verbose_name = '채팅 메시지'
        verbose_name_plural = '채팅 메시지'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['room', 'created_at'], name='chats_msg_room_created_idx'),
        ]

    def __str__(self):
        preview = self.content[:30]
        if len(self.content) > 30:
            preview += '...'
        return f'[{self.room_id}] {self.sender_id}: {preview}'


class ProfanityTerm(models.Model):
    """채팅 욕설 검열용 금지어. Admin에서 CRUD하며 배포 없이 반영됩니다."""

    class Category(models.TextChoices):
        PROFANITY = 'profanity', '욕설/비속어'
        HATE = 'hate', '혐오'
        SEXUAL = 'sexual', '성희롱'
        OTHER = 'other', '기타'

    MAX_TERM_LENGTH = 100

    term = models.CharField(
        '금지어',
        max_length=MAX_TERM_LENGTH,
        help_text='관리자가 입력한 원문. 매칭은 정규화 형태 기준입니다.',
    )
    normalized_term = models.CharField(
        '정규화 형태',
        max_length=MAX_TERM_LENGTH,
        editable=False,
        db_index=True,
        help_text='우회 문자 제거 후 검사용 문자열. 저장 시 자동 설정.',
    )
    is_active = models.BooleanField('활성', default=True, db_index=True)
    category = models.CharField(
        '분류',
        max_length=20,
        choices=Category.choices,
        default=Category.PROFANITY,
    )
    note = models.CharField('메모', max_length=200, blank=True)
    created_at = models.DateTimeField('생성일', auto_now_add=True)
    updated_at = models.DateTimeField('수정일', auto_now=True)

    class Meta:
        verbose_name = '금지어'
        verbose_name_plural = '금지어'
        ordering = ['term']
        constraints = [
            models.UniqueConstraint(
                fields=['normalized_term'],
                name='uniq_chats_profanity_normalized',
            ),
        ]

    def __str__(self):
        status = '활성' if self.is_active else '비활성'
        return f'{self.term} ({status})'

    def clean(self):
        super().clean()
        from apps.chats.moderation import normalize_for_profanity_check

        raw = (self.term or '').strip()
        if not raw:
            raise ValidationError({'term': '금지어를 입력하세요.'})
        normalized = normalize_for_profanity_check(raw)
        if not normalized:
            raise ValidationError({'term': '특수문자만으로는 금지어를 등록할 수 없습니다.'})
        self.term = raw
        self.normalized_term = normalized

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        from apps.chats.moderation import clear_profanity_wordlist_cache

        clear_profanity_wordlist_cache()

    def delete(self, *args, **kwargs):
        result = super().delete(*args, **kwargs)
        from apps.chats.moderation import clear_profanity_wordlist_cache

        clear_profanity_wordlist_cache()
        return result
