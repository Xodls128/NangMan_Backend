"""서버에 고정된 프로필 아바타 ID (이미지는 프론트 정적 자산)."""

PROFILE_AVATAR_IDS: tuple[str, ...] = tuple(f'{i:02d}' for i in range(1, 11))
DEFAULT_PROFILE_AVATAR = '01'


def is_valid_profile_avatar(value: str) -> bool:
    return value in PROFILE_AVATAR_IDS
