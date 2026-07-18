from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.db import models
from django.db.models.functions import Lower


class UserManager(DjangoUserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('provider', User.Provider.LOCAL)
        extra_fields.setdefault('provider_uid', f'local_{username}')
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    """커스텀 유저. 방장/일반 구분은 방 소속으로 판단 (방 생성자 = 방장)."""

    class Provider(models.TextChoices):
        KAKAO = 'kakao', '카카오'
        LOCAL = 'local', '로컬'  # 개발·어드민용

    provider = models.CharField(
        '로그인 제공자',
        max_length=20,
        choices=Provider.choices,
        default=Provider.KAKAO,
    )
    provider_uid = models.CharField(
        '소셜 고유 ID',
        max_length=64,
        help_text='카카오 user id 등. 로컬 계정은 local_<username> 형식.',
    )
    nickname = models.CharField('닉네임', max_length=50, blank=True)
    created_at = models.DateTimeField('가입일', auto_now_add=True)
    updated_at = models.DateTimeField('수정일', auto_now=True)

    objects = UserManager()

    class Meta:
        verbose_name = '유저'
        verbose_name_plural = '유저'
        constraints = [
            models.UniqueConstraint(
                fields=['provider', 'provider_uid'],
                name='uniq_accounts_user_provider_uid',
            ),
            models.UniqueConstraint(
                Lower('username'),
                name='uniq_accounts_user_username_ci',
            ),
        ]

    def __str__(self):
        return self.nickname or self.username
