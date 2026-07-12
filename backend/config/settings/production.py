import os

from .base import *  # noqa: F403

DEBUG = False

ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv('ALLOWED_HOSTS', '').split(',')
    if h.strip()
]
if not ALLOWED_HOSTS:
    raise RuntimeError('ALLOWED_HOSTS environment variable is required in production')

SEED_MOCK_DATA = False

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'True') == 'True'
