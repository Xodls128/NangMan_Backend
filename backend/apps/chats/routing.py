from django.urls import re_path

from .consumers import RoomChatConsumer

websocket_urlpatterns = [
    re_path(r'ws/rooms/(?P<room_id>\d+)/$', RoomChatConsumer.as_asgi()),
]
