from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """커스텀 유저. 방장/일반 구분은 방 소속으로 판단 (방 생성자 = 방장)."""

    nickname = models.CharField('닉네임', max_length=50, blank=True)
    created_at = models.DateTimeField('가입일', auto_now_add=True)
    updated_at = models.DateTimeField('수정일', auto_now=True)

    class Meta:
        verbose_name = '유저'
        verbose_name_plural = '유저'

    def __str__(self):
        return self.nickname or self.username
