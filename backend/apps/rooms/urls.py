from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import MembershipViewSet, RoomViewSet

router = DefaultRouter()
router.register('rooms', RoomViewSet, basename='room')
router.register('memberships', MembershipViewSet, basename='membership')

urlpatterns = [
    path('', include(router.urls)),
]
