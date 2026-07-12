from django.urls import path

from .views import (
    DocumentedTokenBlacklistView,
    DocumentedTokenObtainPairView,
    DocumentedTokenRefreshView,
    MeView,
)

urlpatterns = [
    # 개발·어드민용 (추후 카카오 로그인이 메인 진입점)
    path('token/', DocumentedTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', DocumentedTokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', DocumentedTokenBlacklistView.as_view(), name='token_blacklist'),
    path('me/', MeView.as_view(), name='me'),
]
