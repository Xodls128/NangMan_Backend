from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken


@database_sync_to_async
def _user_from_token(token_str: str):
    User = get_user_model()
    try:
        access = AccessToken(token_str)
        user_id = access.get('user_id')
        return User.objects.get(pk=user_id)
    except (InvalidToken, TokenError, User.DoesNotExist, KeyError):
        return AnonymousUser()


class JwtAuthMiddleware(BaseMiddleware):
    """WebSocket 연결 시 ?token=<access> 로 JWT 인증."""

    async def __call__(self, scope, receive, send):
        query = parse_qs(scope.get('query_string', b'').decode())
        token_list = query.get('token') or []
        token = token_list[0] if token_list else None

        if token:
            scope['user'] = await _user_from_token(token)
        else:
            scope['user'] = AnonymousUser()

        return await super().__call__(scope, receive, send)


def JwtAuthMiddlewareStack(inner):
    return JwtAuthMiddleware(inner)
