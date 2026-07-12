from django.urls import path

from .views import (
    DocumentedTokenBlacklistView,
    DocumentedTokenObtainPairView,
    DocumentedTokenRefreshView,
    KakaoLoginUrlView,
    KakaoLoginView,
    MeView,
)

urlpatterns = [
    # 개발·시드 계정용
    path('token/', DocumentedTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', DocumentedTokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', DocumentedTokenBlacklistView.as_view(), name='token_blacklist'),
    path('me/', MeView.as_view(), name='me'),
    # 카카오 소셜 로그인
    path('kakao/login-url/', KakaoLoginUrlView.as_view(), name='kakao_login_url'),
    path('kakao/', KakaoLoginView.as_view(), name='kakao_login'),
]
