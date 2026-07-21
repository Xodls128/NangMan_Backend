"""Discord 초대 URL 검증."""

from urllib.parse import urlparse

from django.core.exceptions import ValidationError

DISCORD_INVITE_MAX_LENGTH = 512

_ALLOWED_HOSTS = frozenset(
    {
        'discord.gg',
        'discord.com',
        'www.discord.com',
        'ptb.discord.com',
        'canary.discord.com',
    }
)


def normalize_discord_invite_url(value: str | None) -> str | None:
    """
    빈 값은 None. 유효한 https Discord 초대 URL만 허용.
    """
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    if len(text) > DISCORD_INVITE_MAX_LENGTH:
        raise ValidationError('디스코드 초대 링크는 512자 이하여야 합니다.')

    parsed = urlparse(text)
    if parsed.scheme != 'https':
        raise ValidationError('디스코드 초대 링크는 https:// 로 시작해야 합니다.')

    host = (parsed.netloc or '').lower()
    if host not in _ALLOWED_HOSTS:
        raise ValidationError('discord.gg 또는 discord.com 초대 링크만 등록할 수 있습니다.')

    path = parsed.path or ''
    if host == 'discord.gg':
        # https://discord.gg/CODE
        if len(path.strip('/')) < 1:
            raise ValidationError('올바른 디스코드 초대 코드가 포함된 링크를 입력해 주세요.')
    else:
        # https://discord.com/invite/CODE
        if '/invite/' not in path.lower():
            raise ValidationError('discord.com/invite/ 형식의 초대 링크를 입력해 주세요.')

    return text
