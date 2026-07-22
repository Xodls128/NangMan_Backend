import re
import unicodedata
from functools import lru_cache

from django.conf import settings
from django.db.models import Count, Max

from .constants import PROFANITY_REJECT_MESSAGE

_LEET_MAP = str.maketrans(
    {
        '0': 'o',
        '1': 'i',
        '3': 'e',
        '4': 'a',
        '5': 's',
        '7': 't',
        '@': 'a',
        '$': 's',
    }
)

_OBFUSCATION_RE = re.compile(r'[\s\-_·.,*!@#$%^&*()+=[\]{}|\\/<>~`"\':;?]+')
_REPEAT_RE = re.compile(r'(.)\1{2,}')


def normalize_for_profanity_check(text: str) -> str:
    """우회(공백·특수문자·반복자 등)를 줄이기 위한 검사용 정규화."""
    if not text:
        return ''
    normalized = unicodedata.normalize('NFKC', text.casefold())
    normalized = normalized.translate(_LEET_MAP)
    normalized = _OBFUSCATION_RE.sub('', normalized)
    normalized = _REPEAT_RE.sub(r'\1\1', normalized)
    return normalized


def _wordlist_cache_key() -> str:
    """활성 금지어 집합 버전. 워커 간 공유 캐시 없이도 Admin 변경이 반영됩니다."""
    from apps.chats.models import ProfanityTerm

    row = ProfanityTerm.objects.filter(is_active=True).aggregate(
        n=Count('id'),
        m=Max('updated_at'),
    )
    return f"{row['n']}:{row['m']}"


@lru_cache(maxsize=16)
def _load_normalized_terms(cache_key: str) -> frozenset[str]:
    from apps.chats.models import ProfanityTerm

    terms = ProfanityTerm.objects.filter(is_active=True).values_list(
        'normalized_term',
        flat=True,
    )
    return frozenset(t for t in terms if t)


def clear_profanity_wordlist_cache() -> None:
    _load_normalized_terms.cache_clear()


def contains_profanity(text: str) -> bool:
    if not settings.CHAT_PROFANITY_FILTER_ENABLED:
        return False
    normalized = normalize_for_profanity_check(text)
    if not normalized:
        return False
    for term in _load_normalized_terms(_wordlist_cache_key()):
        if term in normalized:
            return True
    return False


__all__ = [
    'PROFANITY_REJECT_MESSAGE',
    'clear_profanity_wordlist_cache',
    'contains_profanity',
    'normalize_for_profanity_check',
]
