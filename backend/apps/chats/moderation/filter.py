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

# 한글 낱자(호환 자모) 조합용 테이블. 자모 분리("ㅅㅣㅂㅏㄹ")나
# 낱자 사이 띄어쓰기 우회를 원래 음절("시발")로 되돌리기 위해 사용합니다.
_CHO = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ',
        'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
_JUNG = ['ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ', 'ㅙ', 'ㅚ', 'ㅛ',
         'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ']
_JONG = ['', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ',
         'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
_CHO_IDX = {c: i for i, c in enumerate(_CHO)}
_JUNG_IDX = {c: i for i, c in enumerate(_JUNG)}
_JONG_IDX = {c: i for i, c in enumerate(_JONG) if c}


def _compose_compat_jamo(text: str) -> str:
    """이어진 호환 자모(낱자)를 완성형 음절로 합칩니다.

    완성형 음절(예: '시', '야')은 건드리지 않고, 사용자가 낱자로 흘려 쓴
    "ㅅㅣㅂㅏㄹ" 같은 입력만 "시발"로 되돌립니다. 종성 판정은 뒤 낱자가
    모음이면 다음 글자의 초성으로 보는 lookahead 방식이라, 음절 경계를
    임의로 훼손하지 않습니다.
    """
    out = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in _CHO_IDX and i + 1 < n and text[i + 1] in _JUNG_IDX:
            cho = _CHO_IDX[c]
            jung = _JUNG_IDX[text[i + 1]]
            i += 2
            jong = 0
            # 다음 자음이 모음을 동반하지 않을 때만 종성으로 결합
            if i < n and text[i] in _JONG_IDX and not (i + 1 < n and text[i + 1] in _JUNG_IDX):
                jong = _JONG_IDX[text[i]]
                i += 1
            out.append(chr(0xAC00 + (cho * 21 + jung) * 28 + jong))
        else:
            out.append(c)
            i += 1
    return ''.join(out)


def normalize_for_profanity_check(text: str) -> str:
    """우회(공백·특수문자·반복자·자모 분리 등)를 줄이기 위한 검사용 정규화."""
    if not text:
        return ''
    normalized = text.casefold()
    normalized = normalized.translate(_LEET_MAP)
    # 특수문자·공백을 먼저 제거해 흩어진 낱자를 붙인 뒤 음절로 조합
    normalized = _OBFUSCATION_RE.sub('', normalized)
    normalized = _compose_compat_jamo(normalized)
    normalized = unicodedata.normalize('NFKC', normalized)
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
