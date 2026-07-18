from django.contrib import admin

from .models import Game, Room, RoomMembership


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'name_ko',
        'slug',
        'short_name',
        'color',
        'is_active',
        'sort_order',
    )
    list_filter = ('is_active',)
    search_fields = ('name', 'name_ko', 'slug')
    ordering = ('sort_order', 'id')
    readonly_fields = ('created_at', 'updated_at')


class RoomMembershipInline(admin.TabularInline):
    model = RoomMembership
    extra = 0
    raw_id_fields = ('user',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'game',
        'owner',
        'play_time_slot',
        'max_members',
        'status',
        'created_at',
    )
    list_filter = ('status', 'game', 'play_time_slot')
    search_fields = ('title', 'game__name', 'owner__username', 'owner__nickname')
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
