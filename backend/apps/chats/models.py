from django.conf import settings
from django.core.validators import MaxLengthValidator
from django.db import models


class ChatMessage(models.Model):
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
