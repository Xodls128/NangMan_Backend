from rest_framework import serializers

from .models import User


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
            'created_at',
        )
        read_only_fields = fields
