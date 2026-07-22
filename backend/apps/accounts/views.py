from django.conf import settings
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
from .serializers import (
    AuthModeSerializer,
    KakaoLoginSerializer,
    MeUpdateSerializer,
    MvpAuthResponseSerializer,
    MvpLoginSerializer,
    TokenPairSerializer,
    UserSerializer,
    tokens_for_user,
)
from .services import mvp_login_or_register, upsert_kakao_user


def _mvp_test_enabled() -> bool:
    return bool(getattr(settings, 'MVP_TEST', False))


def _kakao_disabled_response() -> Response:
    return Response(
        {'detail': 'MVP 테스트 모드에서는 카카오 로그인을 사용할 수 없습니다.'},
        status=status.HTTP_403_FORBIDDEN,
    )


def _mvp_disabled_response() -> Response:
    return Response(
        {'detail': 'MVP 테스트 모드가 비활성화되어 있습니다.'},
        status=status.HTTP_403_FORBIDDEN,
    )


class DocumentedTokenObtainPairView(TokenObtainPairView):
    @extend_schema(
        tags=['auth'],
        summary='로그인 (JWT 발급)',
        description=(
            'username / password로 로그인하여 access·refresh 토큰을 발급합니다.\n\n'
            '- **access**: API·WebSocket 인증에 사용 (기본 30분)\n'
            '- **refresh**: access 재발급에 사용 (기본 7일)\n'
            '- 개발·시드 계정용. 일반 유저는 카카오 로그인을 사용하세요.\n'
            '- `MVP_TEST=true`일 때는 `POST /api/auth/mvp/` 를 사용하세요.'
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

    @extend_schema(
        tags=['auth'],
        summary='내 프로필 수정',
        description=(
            '현재 로그인 유저의 프로필을 수정합니다.\n\n'
            '- **닉네임은 변경할 수 없습니다.**\n'
            '- `profile_avatar`만 아바타 ID(`01`~`10`) 중 선택 가능합니다.\n'
            '- 이미지 URL이 아니라 ID만 저장·반환합니다. 실제 이미지 표시는 클라이언트가 ID로 매핑합니다.'
        ),
        request=MeUpdateSerializer,
        responses={
            200: UserSerializer,
            400: OpenApiResponse(description='잘못된 아바타 ID'),
            401: OpenApiResponse(description='인증 필요'),
        },
    )
    def patch(self, request):
        serializer = MeUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        if not serializer.validated_data:
            return Response(
                {'detail': '변경할 항목이 없습니다.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = request.user
        user.profile_avatar = serializer.validated_data['profile_avatar']
        user.save(update_fields=['profile_avatar', 'updated_at'])
        return Response(UserSerializer(user).data)


class AuthModeView(APIView):
    """프론트 로그인 UI가 따를 인증 모드."""

    permission_classes = [AllowAny]

    @extend_schema(
        tags=['auth'],
        summary='인증 모드 조회',
        description=(
            '서버 `MVP_TEST` 설정에 따른 로그인 모드를 반환합니다.\n\n'
            '- `mvp_test=true` / `auth_mode=mvp`: 카카오 비활성, 닉네임·비밀번호 통합 인증\n'
            '- 그 외: 카카오 로그인 모드'
        ),
        responses={200: AuthModeSerializer},
    )
    def get(self, request):
        mvp = _mvp_test_enabled()
        return Response(
            {
                'mvp_test': mvp,
                'auth_mode': 'mvp' if mvp else 'kakao',
            }
        )


class MvpLoginView(APIView):
    """닉네임·비밀번호로 가입 또는 로그인 (MVP_TEST 전용)."""

    permission_classes = [AllowAny]

    @extend_schema(
        tags=['auth'],
        summary='MVP 통합 가입/로그인',
        description=(
            '`MVP_TEST=true`일 때만 사용할 수 있습니다.\n\n'
            '- 닉네임이 없으면 회원가입 후 JWT 발급 (`profile_avatar`로 프로필 사진 지정)\n'
            '- 닉네임이 있으면 비밀번호로만 로그인 (`profile_avatar`는 무시)\n'
            '- 닉네임은 대소문자를 구분하지 않고 고유해야 합니다\n'
            '- 비밀번호가 틀리면 '
            '`해당 닉네임이 이미 존재하며 비밀번호가 다릅니다.` 메시지를 반환합니다'
        ),
        request=MvpLoginSerializer,
        responses={
            200: MvpAuthResponseSerializer,
            201: MvpAuthResponseSerializer,
            400: OpenApiResponse(description='입력 검증 실패'),
            401: OpenApiResponse(description='비밀번호 불일치'),
            403: OpenApiResponse(description='MVP_TEST 비활성'),
        },
    )
    def post(self, request):
        if not _mvp_test_enabled():
            return _mvp_disabled_response()

        serializer = MvpLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user, created = mvp_login_or_register(
            serializer.validated_data['nickname'],
            serializer.validated_data['password'],
            profile_avatar=serializer.validated_data.get('profile_avatar'),
        )
        payload = tokens_for_user(user, request=request)
        payload['created'] = created
        if created:
            payload['message'] = '회원가입이 완료되었고 로그인되었습니다.'
            http_status = status.HTTP_201_CREATED
        else:
            payload['message'] = '로그인되었습니다.'
            http_status = status.HTTP_200_OK
        return Response(payload, status=http_status)


class KakaoLoginUrlView(APIView):
    """프론트/수동 테스트용 카카오 인가 URL."""

    permission_classes = [AllowAny]

    @extend_schema(
        tags=['auth'],
        summary='카카오 인가 URL 조회',
        description=(
            '브라우저에서 열 카카오 로그인 URL을 반환합니다.\n\n'
            '- Redirect URI는 서버 `KAKAO_REDIRECT_URI` 설정을 사용합니다.\n'
            '- 로그인 후 콜백 URL의 `code`를 `POST /api/auth/kakao/` 로 보내세요.\n'
            '- `MVP_TEST=true`이면 403을 반환합니다.'
        ),
        responses={
            200: OpenApiResponse(description='{ "authorize_url": "..." }'),
            403: OpenApiResponse(description='MVP 테스트 모드로 카카오 비활성'),
        },
    )
    def get(self, request):
        if _mvp_test_enabled():
            return _kakao_disabled_response()
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
            'Redirect URI는 카카오 콘솔 등록값과 `KAKAO_REDIRECT_URI`가 일치해야 합니다.\n'
            '`MVP_TEST=true`이면 403을 반환합니다.'
        ),
        request=KakaoLoginSerializer,
        responses={
            200: TokenPairSerializer,
            400: OpenApiResponse(description='잘못된 code 또는 카카오 오류'),
            403: OpenApiResponse(description='MVP 테스트 모드로 카카오 비활성'),
            502: OpenApiResponse(description='카카오 서버 통신 실패'),
        },
    )
    def post(self, request):
        if _mvp_test_enabled():
            return _kakao_disabled_response()

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

        return Response(tokens_for_user(user, request=request))
