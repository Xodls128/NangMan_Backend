import os

from .base import *  # noqa: F403

DEBUG = True

ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
    if h.strip()
]

# 로컬에서 CORS를 느슨하게 둘 때 (프론트 포트가 자주 바뀔 경우)
# CORS_ALLOW_ALL_ORIGINS = True

# 로컬 목업·시드 데이터 허용 (management command / fixtures에서 이 플래그를 확인)
SEED_MOCK_DATA = True
