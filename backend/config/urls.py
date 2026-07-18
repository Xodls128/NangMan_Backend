from django.conf import settings
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def health(_request):
    return JsonResponse({'status': 'ok'})


urlpatterns = [
    path('health/', health, name='health'),
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.accounts.urls')),
    path('api/', include('apps.rooms.urls')),
    path('api/', include('apps.chats.urls')),
    # API 문서 (프로덕션 포함)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path(
        'api/docs/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='swagger-ui',
    ),
]

if settings.DEBUG:
    from django.conf.urls.static import static

    # 게임 아이콘 등 업로드 파일 서빙 (로컬 전용)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
