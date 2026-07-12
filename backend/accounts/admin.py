from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ('username', 'nickname', 'email', 'is_staff', 'is_active', 'created_at')
    list_filter = ('is_staff', 'is_active', 'is_superuser')
    search_fields = ('username', 'nickname', 'email')
    ordering = ('-created_at',)

    fieldsets = DjangoUserAdmin.fieldsets + (
        ('추가 정보', {'fields': ('nickname',)}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ('추가 정보', {'fields': ('nickname',)}),
    )
    readonly_fields = ('created_at', 'updated_at')
