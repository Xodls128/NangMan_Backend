from django.contrib import admin

from .models import Room, RoomMembership


class RoomMembershipInline(admin.TabularInline):
    model = RoomMembership
    extra = 0
    raw_id_fields = ('user',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'game_name',
        'owner',
        'max_members',
        'status',
        'created_at',
    )
    list_filter = ('status', 'game_name')
    search_fields = ('title', 'game_name', 'owner__username', 'owner__nickname')
    raw_id_fields = ('owner',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [RoomMembershipInline]


@admin.register(RoomMembership)
class RoomMembershipAdmin(admin.ModelAdmin):
    list_display = ('room', 'user', 'status', 'created_at', 'updated_at')
    list_filter = ('status',)
    search_fields = (
        'room__title',
        'user__username',
        'user__nickname',
    )
    raw_id_fields = ('room', 'user')
    readonly_fields = ('created_at', 'updated_at')
