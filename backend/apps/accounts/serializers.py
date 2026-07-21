from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .profile_avatars import PROFILE_AVATAR_IDS


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'nickname',
            'email',
            'provider',
            'provider_uid',
            'profile_avatar',
            'created_at',
        )
        read_only_fields = fields


class MeUpdateSerializer(serializers.Serializer):
    profile_avatar = serializers.ChoiceField(
        choices=[(v, v) for v in PROFILE_AVATAR_IDS],
        required=True,
    )


class PublicUserSerializer(serializers.Serializer):
    """방·채팅 등에 노출되는 유저 요약."""

    id = serializers.IntegerField()
    username = serializers.CharField()
    nickname = serializers.CharField()
    profile_avatar = serializers.CharField()


class KakaoLoginSerializer(serializers.Serializer):
    code = serializers.CharField(help_text='카카오 인가 코드')


class MvpLoginSerializer(serializers.Serializer):
    nickname = serializers.CharField(
        max_length=50,
        trim_whitespace=True,
        help_text='로그인/가입에 사용할 닉네임 (대소문자 구분 없이 고유)',
    )
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        help_text='비밀번호',
    )


class TokenPairSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()


class MvpAuthResponseSerializer(TokenPairSerializer):
    created = serializers.BooleanField(
        help_text='True면 신규 가입 후 로그인, False면 기존 계정 로그인',
    )
    message = serializers.CharField(help_text='사용자 안내 문구')


class AuthModeSerializer(serializers.Serializer):
    mvp_test = serializers.BooleanField(
        help_text='True면 카카오 비활성, 닉네임/비밀번호 통합 인증 사용',
    )
    auth_mode = serializers.ChoiceField(
        choices=['kakao', 'mvp'],
        help_text='프론트 로그인 UI 모드',
    )


def tokens_for_user(user: User, request=None) -> dict:
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': UserSerializer(user).data,
    }
