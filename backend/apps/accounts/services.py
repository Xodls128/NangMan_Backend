from django.db import transaction

from .kakao import KakaoProfile
from .models import User


@transaction.atomic
def upsert_kakao_user(profile: KakaoProfile) -> User:
    """카카오 프로필로 User를 생성하거나 갱신합니다."""
    username = f'kakao_{profile.id}'
    user, created = User.objects.get_or_create(
        provider=User.Provider.KAKAO,
        provider_uid=profile.id,
        defaults={
            'username': username,
            'nickname': profile.nickname,
        },
    )
    if created:
        user.set_unusable_password()
        user.save(update_fields=['password'])
    else:
        fields: list[str] = []
        if profile.nickname and user.nickname != profile.nickname:
            user.nickname = profile.nickname
            fields.append('nickname')
        if fields:
            user.save(update_fields=[*fields, 'updated_at'])
    return user
