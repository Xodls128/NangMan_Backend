from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.chats.content_validation import validate_user_chat_content
from apps.chats.moderation import (
    clear_profanity_wordlist_cache,
    contains_profanity,
    normalize_for_profanity_check,
)
from apps.chats.models import ChatMessage, ProfanityTerm
from apps.rooms.models import Game, Room


class NormalizeProfanityTests(SimpleTestCase):
    def test_normalize_strips_obfuscation(self):
        self.assertEqual(
            normalize_for_profanity_check('금  지 · 단어xyz'),
            '금지단어xyz',
        )

    def test_separated_jamo_recomposed_to_syllable(self):
        # 자모 분리("ㅅㅣㅂㅏㄹ")와 낱자 사이 공백은 원래 음절로 복원되어야 한다.
        self.assertEqual(normalize_for_profanity_check('ㅅㅣㅂㅏㄹ'), '시발')
        self.assertEqual(normalize_for_profanity_check('ㅅ ㅣ ㅂ ㅏ ㄹ'), '시발')

    def test_completed_syllables_are_not_corrupted(self):
        # 완성형 음절 뒤의 낱자를 앞 음절에 잘못 붙이면 안 된다("야"+"ㅅ" != "얏").
        self.assertNotIn('얏', normalize_for_profanity_check('야 ㅅㅂ'))
        # 정상 어절의 음절 경계는 보존되어 오검열이 없어야 한다.
        self.assertEqual(normalize_for_profanity_check('시 바람'), '시바람')


@override_settings(CHAT_PROFANITY_FILTER_ENABLED=True)
class ProfanityFilterDbTests(TestCase):
    def setUp(self):
        clear_profanity_wordlist_cache()
        ProfanityTerm.objects.create(term='금지단어xyz', is_active=True)

    def tearDown(self):
        clear_profanity_wordlist_cache()

    def test_detects_banned_term(self):
        self.assertTrue(contains_profanity('여기 금지단어xyz 포함'))

    def test_obfuscated_banned_term(self):
        self.assertTrue(contains_profanity('금..지..단어xyz'))

    def test_clean_message_allowed(self):
        self.assertFalse(contains_profanity('오늘 저녁에 게임 할 사람?'))

    def test_inactive_term_ignored(self):
        ProfanityTerm.objects.filter(term='금지단어xyz').update(is_active=False)
        clear_profanity_wordlist_cache()
        self.assertFalse(contains_profanity('금지단어xyz'))

    def test_admin_add_term_applies_immediately(self):
        self.assertFalse(contains_profanity('신규금지어abc'))
        ProfanityTerm.objects.create(term='신규금지어abc', is_active=True)
        self.assertTrue(contains_profanity('신규금지어abc'))

    def test_validate_user_chat_content_rejects_profanity(self):
        text, error = validate_user_chat_content('  금지단어xyz  ')
        self.assertIsNone(text)
        self.assertEqual(error, '부적절한 표현이 포함되어 있습니다.')

    @override_settings(CHAT_PROFANITY_FILTER_ENABLED=False)
    def test_filter_disabled(self):
        clear_profanity_wordlist_cache()
        self.assertFalse(contains_profanity('금지단어xyz'))

    def test_duplicate_normalized_rejected(self):
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            ProfanityTerm.objects.create(term='금 지 단어xyz')


@override_settings(CHAT_PROFANITY_FILTER_ENABLED=True)
class ProfanityEvasionTests(TestCase):
    """자모 분리 / 초성체 우회 및 오검열 방지 회귀 테스트."""

    def setUp(self):
        clear_profanity_wordlist_cache()
        # 시드 마이그레이션이 이미 등록했을 수 있으므로 get_or_create로 보장.
        for term in ('시발', 'ㅅㅂ', '병신', 'ㅂㅅ', '개새끼'):
            obj, _ = ProfanityTerm.objects.get_or_create(term=term)
            if not obj.is_active:
                obj.is_active = True
                obj.save()
        clear_profanity_wordlist_cache()

    def tearDown(self):
        clear_profanity_wordlist_cache()

    def test_detects_separated_jamo(self):
        self.assertTrue(contains_profanity('ㅅㅣㅂㅏㄹ'))
        self.assertTrue(contains_profanity('ㅅ ㅣ ㅂ ㅏ ㄹ'))

    def test_detects_chosung_abbreviation(self):
        self.assertTrue(contains_profanity('야 ㅅㅂ 뭐하냐'))
        self.assertTrue(contains_profanity('ㅂㅅ같네'))

    def test_detects_spaced_word(self):
        self.assertTrue(contains_profanity('개 새 끼'))

    def test_no_false_positive_on_normal_sentences(self):
        # 음절 경계가 보존되어 정상 어절이 검열되면 안 된다.
        for clean in ('시 바람이 분다', '시원한 발라드', '소방서 갔다옴',
                      '신발 사러 가자', 'ㅋㅋㅋ 재밌다', 'class 수업 끝'):
            self.assertFalse(contains_profanity(clean), msg=clean)


def _create_user(**kwargs):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    defaults = {
        'password': 'StrongPass123!',
        'provider': User.Provider.LOCAL,
    }
    defaults.update(kwargs)
    password = defaults.pop('password')
    return User.objects.create_user(password=password, **defaults)


@override_settings(CHAT_PROFANITY_FILTER_ENABLED=True)
class ChatProfanityApiTests(TestCase):
    def setUp(self):
        clear_profanity_wordlist_cache()
        ProfanityTerm.objects.create(term='금지단어xyz', is_active=True)
        self.client = APIClient()
        self.game = Game.objects.create(
            slug='mod-game',
            name='Mod Game',
            name_ko='검열',
            short_name='MD',
            color='#112233',
        )
        self.owner = _create_user(
            username='mod_owner',
            nickname='방장',
            provider_uid='local_mod_owner',
        )
        self.room = Room.create_with_owner(
            owner=self.owner,
            title='검열 테스트',
            game=self.game,
            max_members=5,
            play_time_slot=Room.PlayTimeSlot.EVENING,
        )
        self.client.force_authenticate(self.owner)

    def tearDown(self):
        clear_profanity_wordlist_cache()

    def test_post_message_rejects_profanity(self):
        before = ChatMessage.objects.filter(room=self.room).count()
        response = self.client.post(
            f'/api/rooms/{self.room.id}/messages/',
            {'content': '금지단어xyz'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('content', response.data)
        self.assertEqual(ChatMessage.objects.filter(room=self.room).count(), before)

    def test_post_message_allows_clean_content(self):
        response = self.client.post(
            f'/api/rooms/{self.room.id}/messages/',
            {'content': '안녕하세요'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['content'], '안녕하세요')
