from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import GameViewSet, MembershipViewSet, RoomViewSet

router = DefaultRouter()
router.register('games', GameViewSet, basename='game')
router.register('rooms', RoomViewSet, basename='room')
router.register('memberships', MembershipViewSet, basename='membership')

urlpatterns = [
    path('', include(router.urls)),
]
