from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework.exceptions import AuthenticationFailed, ValidationError

from .kakao import KakaoProfile
from .models import User
from .profile_avatars import is_valid_profile_avatar, random_profile_avatar


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
            'profile_avatar': random_profile_avatar(),
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


def find_user_by_nickname(nickname: str) -> User | None:
    """대소문자를 무시해 username(=닉네임)으로 사용자를 찾습니다."""
    return User.objects.filter(username__iexact=nickname).first()


@transaction.atomic
def mvp_login_or_register(
    nickname: str,
    password: str,
    profile_avatar: str | None = None,
) -> tuple[User, bool]:
    """
    닉네임이 없으면 가입 후 로그인, 있으면 비밀번호로 로그인합니다.
    profile_avatar는 신규 가입 시에만 반영하며, 기존 계정 로그인 시에는 무시합니다.

    Returns:
        (user, created)
    """
    nickname = nickname.strip()
    if not nickname:
        raise ValidationError({'nickname': '닉네임을 입력해 주세요.'})
    if len(nickname) > 50:
        raise ValidationError({'nickname': '닉네임은 50자 이하여야 합니다.'})
    if not password:
        raise ValidationError({'password': '비밀번호를 입력해 주세요.'})

    existing = find_user_by_nickname(nickname)
    if existing is not None:
        user = authenticate(username=existing.username, password=password)
        if user is None:
            raise AuthenticationFailed('해당 닉네임이 이미 존재하며 비밀번호가 다릅니다.')
        if not user.is_active:
            raise AuthenticationFailed('비활성화된 계정입니다.')
        return user, False

    avatar = profile_avatar or random_profile_avatar()
    if not is_valid_profile_avatar(avatar):
        raise ValidationError({'profile_avatar': '올바른 프로필 아바타 ID를 선택해 주세요.'})

    try:
        validate_password(password, user=User(username=nickname, nickname=nickname))
    except DjangoValidationError as exc:
        raise ValidationError({'password': list(exc.messages)}) from exc

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=nickname,
                password=password,
                nickname=nickname,
                provider=User.Provider.LOCAL,
                provider_uid=f'local_{nickname}',
                profile_avatar=avatar,
            )
    except IntegrityError:
        # 동시 가입 등으로 닉네임이 방금 생성된 경우 → 로그인 시도로 전환
        existing = find_user_by_nickname(nickname)
        if existing is None:
            raise ValidationError({'nickname': '이미 사용 중인 닉네임입니다.'}) from None
        user = authenticate(username=existing.username, password=password)
        if user is None:
            raise AuthenticationFailed('해당 닉네임이 이미 존재하며 비밀번호가 다릅니다.') from None
        return user, False

    return user, True
