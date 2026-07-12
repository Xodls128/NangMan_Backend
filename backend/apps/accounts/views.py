from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import (
    TokenBlacklistView,
    TokenObtainPairView,
    TokenRefreshView,
)

from .serializers import UserSerializer


class DocumentedTokenObtainPairView(TokenObtainPairView):
    @extend_schema(
        tags=['auth'],
        summary='로그인 (JWT 발급)',
        description=(
            'username / password로 로그인하여 access·refresh 토큰을 발급합니다.\n\n'
            '- **access**: API·WebSocket 인증에 사용 (기본 30분)\n'
            '- **refresh**: access 재발급에 사용 (기본 7일)\n'
            '- 현재는 개발·어드민용이며, 추후 카카오 로그인이 메인 진입점이 됩니다.'
        ),
        responses={
            200: OpenApiResponse(description='토큰 발급 성공'),
            401: OpenApiResponse(description='인증 실패 (잘못된 계정/비밀번호)'),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class DocumentedTokenRefreshView(TokenRefreshView):
    @extend_schema(
        tags=['auth'],
        summary='Access 토큰 갱신',
        description=(
            'refresh 토큰으로 새 access 토큰을 발급합니다.\n\n'
            '- `ROTATE_REFRESH_TOKENS=True` 이므로 응답에 새 refresh도 포함될 수 있습니다.\n'
            '- 이전 refresh는 블랙리스트 처리됩니다.'
        ),
        responses={
            200: OpenApiResponse(description='갱신 성공'),
            401: OpenApiResponse(description='refresh 토큰이 유효하지 않음'),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class DocumentedTokenBlacklistView(TokenBlacklistView):
    @extend_schema(
        tags=['auth'],
        summary='로그아웃 (Refresh 블랙리스트)',
        description=(
            'refresh 토큰을 블랙리스트에 등록하여 재사용을 막습니다.\n\n'
            '- body에 `refresh`를 전달합니다.\n'
            '- access는 만료까지 유효할 수 있으므로, 클라이언트는 로컬 토큰도 삭제해야 합니다.'
        ),
        responses={
            200: OpenApiResponse(description='블랙리스트 등록 성공'),
            400: OpenApiResponse(description='잘못된 refresh 토큰'),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class MeView(APIView):
    """현재 로그인한 유저 정보 (JWT 필요)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['auth'],
        summary='내 정보 조회',
        description=(
            'Authorization Bearer access 토큰 기준으로 현재 로그인 유저 정보를 반환합니다.\n\n'
            '- `provider` / `provider_uid`: 소셜(또는 로컬) 식별자\n'
            '- `nickname`: 화면에 표시할 이름'
        ),
        responses={
            200: UserSerializer,
            401: OpenApiResponse(description='인증 필요 또는 토큰 만료'),
        },
    )
    def get(self, request):
        return Response(UserSerializer(request.user).data)
