from rest_framework import serializers

from apps.accounts.serializers import PublicUserSerializer

from .content_validation import validate_user_chat_content
from .models import ChatMessage


class ChatMessageSerializer(serializers.ModelSerializer):
    sender = PublicUserSerializer(read_only=True, allow_null=True)

    class Meta:
        model = ChatMessage
        fields = (
            'id',
            'room',
            'sender',
            'message_type',
            'content',
            'created_at',
        )
        read_only_fields = ('id', 'room', 'sender', 'message_type', 'created_at')


class ChatMessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ('content',)

    def validate_content(self, value):
        text, error = validate_user_chat_content(value)
        if error:
            raise serializers.ValidationError(error)
        return text

    def create(self, validated_data):
        return ChatMessage.objects.create(
            room=self.context['room'],
            sender=self.context['request'].user,
            **validated_data,
        )
