from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.accounts.urls')),
    path('api/', include('apps.rooms.urls')),
    path('api/', include('apps.chats.urls')),
]

# API 문서는 로컬(DEBUG)에서만 노출
if settings.DEBUG:
    from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

    urlpatterns += [
        path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
        path(
            'api/docs/',
            SpectacularSwaggerView.as_view(url_name='schema'),
            name='swagger-ui',
        ),
    ]
