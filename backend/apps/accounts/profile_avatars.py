"""서버에 고정된 프로필 아바타 ID (이미지 URL이 아니라 ID만 저장·반환)."""

import random

PROFILE_AVATAR_IDS: tuple[str, ...] = tuple(f'{i:02d}' for i in range(1, 11))
DEFAULT_PROFILE_AVATAR = '01'


def is_valid_profile_avatar(value: str) -> bool:
    return value in PROFILE_AVATAR_IDS


def random_profile_avatar() -> str:
    return random.choice(PROFILE_AVATAR_IDS)
