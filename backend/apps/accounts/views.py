from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import UserSerializer


class MeView(APIView):
    """현재 로그인한 유저 정보 (JWT 필요)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['auth'], responses=UserSerializer)
    def get(self, request):
        return Response(UserSerializer(request.user).data)
