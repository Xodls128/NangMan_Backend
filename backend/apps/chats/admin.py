from django.contrib import admin

from .models import ChatMessage


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'room', 'sender', 'content_preview', 'created_at')
    list_filter = ('room',)
    search_fields = ('content', 'sender__username', 'sender__nickname', 'room__title')
    raw_id_fields = ('room', 'sender')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

    @admin.display(description='내용')
    def content_preview(self, obj):
        if len(obj.content) <= 50:
            return obj.content
        return f'{obj.content[:50]}...'
