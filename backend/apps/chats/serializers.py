from rest_framework import serializers

from .models import ChatMessage


class SenderSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    nickname = serializers.CharField()


class ChatMessageSerializer(serializers.ModelSerializer):
    sender = SenderSerializer(read_only=True)

    class Meta:
        model = ChatMessage
        fields = (
            'id',
            'room',
            'sender',
            'content',
            'created_at',
        )
        read_only_fields = ('id', 'room', 'sender', 'created_at')


class ChatMessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ('content',)

    def validate_content(self, value):
        text = value.strip()
        if not text:
            raise serializers.ValidationError('메시지 내용을 입력하세요.')
        if len(text) > ChatMessage.MAX_CONTENT_LENGTH:
            raise serializers.ValidationError(
                f'메시지는 {ChatMessage.MAX_CONTENT_LENGTH}자까지 가능합니다.'
            )
        return text

    def create(self, validated_data):
        return ChatMessage.objects.create(
            room=self.context['room'],
            sender=self.context['request'].user,
            **validated_data,
        )
