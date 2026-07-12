from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import (
    TokenBlacklistView,
    TokenObtainPairView,
    TokenRefreshView,
)

from .kakao import KakaoAPIError, build_authorize_url, exchange_code_for_token, fetch_kakao_profile
from .serializers import KakaoLoginSerializer, TokenPairSerializer, UserSerializer, tokens_for_user
from .services import upsert_kakao_user


class DocumentedTokenObtainPairView(TokenObtainPairView):
    @extend_schema(
        tags=['auth'],
        summary='로그인 (JWT 발급)',
        description=(
            'username / password로 로그인하여 access·refresh 토큰을 발급합니다.\n\n'
            '- **access**: API·WebSocket 인증에 사용 (기본 30분)\n'
            '- **refresh**: access 재발급에 사용 (기본 7일)\n'
            '- 개발·시드 계정용. 일반 유저는 카카오 로그인을 사용하세요.'
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


class KakaoLoginUrlView(APIView):
    """프론트/수동 테스트용 카카오 인가 URL."""

    permission_classes = [AllowAny]

    @extend_schema(
        tags=['auth'],
        summary='카카오 인가 URL 조회',
        description=(
            '브라우저에서 열 카카오 로그인 URL을 반환합니다.\n\n'
            '- Redirect URI는 서버 `KAKAO_REDIRECT_URI` 설정을 사용합니다.\n'
            '- 로그인 후 콜백 URL의 `code`를 `POST /api/auth/kakao/` 로 보내세요.'
        ),
        responses={200: OpenApiResponse(description='{ "authorize_url": "..." }')},
    )
    def get(self, request):
        try:
            url = build_authorize_url()
        except KakaoAPIError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({'authorize_url': url})


class KakaoLoginView(APIView):
    """카카오 인가 코드로 로그인하고 JWT를 발급합니다."""

    permission_classes = [AllowAny]

    @extend_schema(
        tags=['auth'],
        summary='카카오 로그인 (인가 코드 → JWT)',
        description=(
            '카카오 OAuth 인가 코드로 로그인합니다.\n\n'
            '1. 프론트에서 카카오 인가 화면으로 이동\n'
            '2. Redirect URI로 `code` 수신\n'
            '3. 이 API에 `code` POST\n'
            '4. access / refresh JWT + user 반환\n\n'
            'Redirect URI는 카카오 콘솔 등록값과 `KAKAO_REDIRECT_URI`가 일치해야 합니다.'
        ),
        request=KakaoLoginSerializer,
        responses={
            200: TokenPairSerializer,
            400: OpenApiResponse(description='잘못된 code 또는 카카오 오류'),
            502: OpenApiResponse(description='카카오 서버 통신 실패'),
        },
    )
    def post(self, request):
        serializer = KakaoLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data['code'].strip()

        try:
            token_payload = exchange_code_for_token(code)
            profile = fetch_kakao_profile(token_payload['access_token'])
            user = upsert_kakao_user(profile)
        except KakaoAPIError as exc:
            if exc.status_code and 400 <= exc.status_code < 500:
                http_status = status.HTTP_400_BAD_REQUEST
            else:
                http_status = status.HTTP_502_BAD_GATEWAY
            return Response({'detail': str(exc)}, status=http_status)

        return Response(tokens_for_user(user))
