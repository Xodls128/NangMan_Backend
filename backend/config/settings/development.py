import os

from .base import *  # noqa: F403

DEBUG = True

ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
    if h.strip()
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',  # noqa: F405
    }
}

# 로컬에서 CORS를 느슨하게 (임시 프론트 테스트용)
CORS_ALLOW_ALL_ORIGINS = True

# 로컬 목업·시드 데이터 허용 (management command / fixtures에서 이 플래그를 확인)
SEED_MOCK_DATA = True
