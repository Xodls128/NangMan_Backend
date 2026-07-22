from django.contrib import admin, messages
from django.utils import timezone

from .models import ChatMessage, ProfanityTerm
from .moderation import clear_profanity_wordlist_cache


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'room', 'message_type', 'sender', 'content_preview', 'created_at')
    list_filter = ('message_type', 'room')
    search_fields = ('content', 'sender__username', 'sender__nickname', 'room__title')
    raw_id_fields = ('room', 'sender')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

    @admin.display(description='내용')
    def content_preview(self, obj):
        if len(obj.content) <= 50:
            return obj.content
        return f'{obj.content[:50]}...'


@admin.register(ProfanityTerm)
class ProfanityTermAdmin(admin.ModelAdmin):
    list_display = (
        'term',
        'normalized_term',
        'category',
        'is_active',
        'updated_at',
    )
    list_filter = ('is_active', 'category')
    search_fields = ('term', 'normalized_term', 'note')
    list_editable = ('is_active',)
    readonly_fields = ('normalized_term', 'created_at', 'updated_at')
    ordering = ('term',)
    actions = ('activate_terms', 'deactivate_terms')

    fieldsets = (
        (None, {
            'fields': ('term', 'normalized_term', 'is_active', 'category', 'note'),
        }),
        ('메타', {
            'fields': ('created_at', 'updated_at'),
        }),
    )

    @admin.action(description='선택한 금지어 활성화')
    def activate_terms(self, request, queryset):
        updated = queryset.update(is_active=True, updated_at=timezone.now())
        clear_profanity_wordlist_cache()
        self.message_user(request, f'{updated}개 금지어를 활성화했습니다.', messages.SUCCESS)

    @admin.action(description='선택한 금지어 비활성화')
    def deactivate_terms(self, request, queryset):
        updated = queryset.update(is_active=False, updated_at=timezone.now())
        clear_profanity_wordlist_cache()
        self.message_user(request, f'{updated}개 금지어를 비활성화했습니다.', messages.SUCCESS)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        clear_profanity_wordlist_cache()

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        clear_profanity_wordlist_cache()

    def delete_queryset(self, request, queryset):
        super().delete_queryset(request, queryset)
        clear_profanity_wordlist_cache()

    def changelist_view(self, request, extra_context=None):
        # list_editable 저장 시에도 캐시 무효화
        response = super().changelist_view(request, extra_context=extra_context)
        if request.method == 'POST' and '_save' in request.POST:
            clear_profanity_wordlist_cache()
        return response
