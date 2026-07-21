from concurrent.futures import ThreadPoolExecutor, as_completed

from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


class AuthModeApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @override_settings(MVP_TEST=False)
    def test_auth_mode_kakao_when_mvp_disabled(self):
        res = self.client.get('/api/auth/mode/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['mvp_test'], False)
        self.assertEqual(res.data['auth_mode'], 'kakao')

    @override_settings(MVP_TEST=True)
    def test_auth_mode_mvp_when_enabled(self):
        res = self.client.get('/api/auth/mode/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['mvp_test'], True)
        self.assertEqual(res.data['auth_mode'], 'mvp')


class KakaoDisabledInMvpTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @override_settings(MVP_TEST=True)
    def test_kakao_login_url_forbidden(self):
        res = self.client.get('/api/auth/kakao/login-url/')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('카카오', res.data['detail'])

    @override_settings(MVP_TEST=True)
    def test_kakao_login_forbidden(self):
        res = self.client.post('/api/auth/kakao/', {'code': 'dummy'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class MvpLoginApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @override_settings(MVP_TEST=False)
    def test_mvp_endpoint_blocked_when_flag_off(self):
        res = self.client.post(
            '/api/auth/mvp/',
            {'nickname': 'newbie', 'password': 'StrongPass123!'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(MVP_TEST=True)
    def test_register_then_login(self):
        create = self.client.post(
            '/api/auth/mvp/',
            {'nickname': 'HeroOne', 'password': 'StrongPass123!'},
            format='json',
        )
        self.assertEqual(create.status_code, status.HTTP_201_CREATED)
        self.assertTrue(create.data['created'])
        self.assertIn('회원가입', create.data['message'])
        self.assertIn('access', create.data)
        self.assertEqual(create.data['user']['username'], 'HeroOne')
        self.assertEqual(create.data['user']['nickname'], 'HeroOne')
        self.assertEqual(create.data['user']['provider'], 'local')

        login = self.client.post(
            '/api/auth/mvp/',
            {'nickname': 'HeroOne', 'password': 'StrongPass123!'},
            format='json',
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK)
        self.assertFalse(login.data['created'])
        self.assertEqual(login.data['message'], '로그인되었습니다.')

    @override_settings(MVP_TEST=True)
    def test_wrong_password_message(self):
        User.objects.create_user(
            username='TakenNick',
            password='CorrectPass123!',
            nickname='TakenNick',
            provider=User.Provider.LOCAL,
            provider_uid='local_TakenNick',
        )
        res = self.client.post(
            '/api/auth/mvp/',
            {'nickname': 'TakenNick', 'password': 'WrongPass123!'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            res.data['detail'],
            '해당 닉네임이 이미 존재하며 비밀번호가 다릅니다.',
        )

    @override_settings(MVP_TEST=True)
    def test_case_insensitive_nickname_collision(self):
        User.objects.create_user(
            username='CaseNick',
            password='StrongPass123!',
            nickname='CaseNick',
            provider=User.Provider.LOCAL,
            provider_uid='local_CaseNick',
        )
        res = self.client.post(
            '/api/auth/mvp/',
            {'nickname': 'casenick', 'password': 'AnotherPass123!'},
            format='json',
        )
        # 대소문자만 다른 닉네임 → 기존 계정 로그인 시도 → 비밀번호 불일치
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            res.data['detail'],
            '해당 닉네임이 이미 존재하며 비밀번호가 다릅니다.',
        )
        self.assertEqual(User.objects.filter(username__iexact='casenick').count(), 1)

    @override_settings(MVP_TEST=True)
    def test_case_insensitive_login_with_different_case(self):
        User.objects.create_user(
            username='MixCase',
            password='StrongPass123!',
            nickname='MixCase',
            provider=User.Provider.LOCAL,
            provider_uid='local_MixCase',
        )
        res = self.client.post(
            '/api/auth/mvp/',
            {'nickname': 'mixcase', 'password': 'StrongPass123!'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(res.data['created'])

    @override_settings(MVP_TEST=True)
    def test_register_with_profile_avatar(self):
        create = self.client.post(
            '/api/auth/mvp/',
            {
                'nickname': 'AvatarHero',
                'password': 'StrongPass123!',
                'profile_avatar': '07',
            },
            format='json',
        )
        self.assertEqual(create.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create.data['user']['profile_avatar'], '07')
        user = User.objects.get(username='AvatarHero')
        self.assertEqual(user.profile_avatar, '07')

    @override_settings(MVP_TEST=True)
    def test_login_ignores_profile_avatar(self):
        User.objects.create_user(
            username='KeepAvatar',
            password='StrongPass123!',
            nickname='KeepAvatar',
            provider=User.Provider.LOCAL,
            provider_uid='local_KeepAvatar',
            profile_avatar='03',
        )
        res = self.client.post(
            '/api/auth/mvp/',
            {
                'nickname': 'KeepAvatar',
                'password': 'StrongPass123!',
                'profile_avatar': '09',
            },
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(res.data['created'])
        self.assertEqual(res.data['user']['profile_avatar'], '03')

    @override_settings(MVP_TEST=True)
    def test_password_validation_on_register(self):
        res = self.client.post(
            '/api/auth/mvp/',
            {'nickname': 'weakuser', 'password': '123'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', res.data)


class ProfileAvatarApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='avatar_user',
            password='StrongPass123!',
            nickname='아바타유저',
            provider=User.Provider.LOCAL,
            provider_uid='local_avatar_user',
        )

    def test_me_includes_profile_avatar(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.get('/api/auth/me/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['profile_avatar'], '01')
        self.assertNotIn('profile_avatar_url', res.data)

    def test_patch_profile_avatar(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.patch(
            '/api/auth/me/',
            {'profile_avatar': '05'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['profile_avatar'], '05')
        self.user.refresh_from_db()
        self.assertEqual(self.user.profile_avatar, '05')

    def test_patch_invalid_avatar(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.patch(
            '/api/auth/me/',
            {'profile_avatar': '99'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class MvpLoginConcurrencyTests(TransactionTestCase):
    @override_settings(MVP_TEST=True)
    def test_concurrent_register_does_not_create_duplicates(self):
        # SQLite 등에서는 스레드별 DB 연결 이슈가 있을 수 있어
        # IntegrityError 경로를 서비스에서 직접 검증한다.
        from apps.accounts.services import mvp_login_or_register

        nickname = 'RaceNick'
        password = 'StrongPass123!'

        def attempt():
            return mvp_login_or_register(nickname, password)

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(attempt) for _ in range(2)]
            results = []
            errors = []
            for fut in as_completed(futures):
                try:
                    results.append(fut.result())
                except Exception as exc:  # noqa: BLE001 — 동시성 테스트
                    errors.append(exc)

        self.assertEqual(User.objects.filter(username__iexact=nickname).count(), 1)
        # 두 요청 모두 성공(한 명은 생성, 한 명은 로그인)하거나, 한 쪽만 성공해도 중복은 없어야 함
        self.assertGreaterEqual(len(results) + len(errors), 1)
        created_flags = [created for _, created in results]
        self.assertLessEqual(sum(1 for c in created_flags if c), 1)
