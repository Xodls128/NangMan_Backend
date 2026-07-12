from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = (
        'username',
        'nickname',
        'provider',
        'provider_uid',
        'email',
        'is_staff',
        'is_active',
        'created_at',
    )
    list_filter = ('provider', 'is_staff', 'is_active', 'is_superuser')
    search_fields = ('username', 'nickname', 'email', 'provider_uid')
    ordering = ('-created_at',)

    fieldsets = DjangoUserAdmin.fieldsets + (
        ('소셜 로그인', {'fields': ('provider', 'provider_uid', 'nickname')}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ('소셜 로그인', {'fields': ('provider', 'provider_uid', 'nickname')}),
    )
    readonly_fields = ('created_at', 'updated_at')
