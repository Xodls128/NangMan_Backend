from django.urls import path

from .views import RoomMessageListCreateView

urlpatterns = [
    path(
        'rooms/<int:room_id>/messages/',
        RoomMessageListCreateView.as_view(),
        name='room-messages',
    ),
]
