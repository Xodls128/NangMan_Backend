from pathlib import Path
from datetime import timedelta
import os

from dotenv import load_dotenv

# config/settings/base.py → backend/
BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError('SECRET_KEY environment variable is required')

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'channels',
    'rest_framework',
    'corsheaders',
    'rest_framework_simplejwt.token_blacklist',
    'drf_spectacular',
]

LOCAL_APPS = [
    'apps.accounts',
    'apps.rooms',
    'apps.chats',
]

# daphne는 staticfiles보다 앞에 있어야 함
INSTALLED_APPS = ['daphne'] + DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# 로컬·단일 프로세스용. production에서는 Redis Channel Layer로 교체.
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

# DATABASES는 development(SQLite) / production(PostgreSQL)에서 각각 정의

AUTH_USER_MODEL = 'accounts.User'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'NangMan API',
    'DESCRIPTION': (
        '게임 친구 매칭 서비스 REST API.\n\n'
        '채팅 WebSocket(문서 외):\n'
        '`ws://<host>/ws/rooms/{room_id}/?token=<access_jwt>`\n'
        '메시지 전송 JSON: `{"type": "chat.message", "content": "..."}`'
    ),
    'VERSION': '0.1.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv('CORS_ALLOWED_ORIGINS', '').split(',')
    if o.strip()
]

LANGUAGE_CODE = 'ko-kr'
TIME_ZONE = 'Asia/Seoul'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'mediafiles'

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# 목업/시드 데이터 — development에서만 True로 덮어씀
SEED_MOCK_DATA = False

# MVP 테스트 모드: 카카오 로그인 비활성 + 닉네임/비밀번호 통합 가입·로그인
# 표준 활성화 값: MVP_TEST=true (대소문자 무시). 오타(TURE 등)는 비활성.
MVP_TEST = os.getenv('MVP_TEST', 'false').strip().lower() in ('1', 'true', 'yes', 'on')

# 카카오 OAuth (로컬 Redirect URI 예: http://localhost:5173/auth/kakao/callback)
KAKAO_REST_API_KEY = os.getenv('KAKAO_REST_API_KEY', '')
KAKAO_CLIENT_SECRET = os.getenv('KAKAO_CLIENT_SECRET', '')
KAKAO_REDIRECT_URI = os.getenv(
    'KAKAO_REDIRECT_URI',
    'http://localhost:5173/auth/kakao/callback',
)

# 채팅 욕설 검열 (기본 활성). 금지어는 Django Admin / ProfanityTerm DB로 관리.
# 텍스트 파일은 초기 시드·`seed_profanity_terms` 커맨드용입니다.
CHAT_PROFANITY_FILTER_ENABLED = os.getenv(
    'CHAT_PROFANITY_FILTER_ENABLED',
    'true',
).strip().lower() in ('1', 'true', 'yes', 'on')
CHAT_PROFANITY_WORDLIST_PATH = os.getenv(
    'CHAT_PROFANITY_WORDLIST_PATH',
    str(BASE_DIR / 'apps' / 'chats' / 'moderation' / 'wordlists' / 'ko_profanity.txt'),
)
