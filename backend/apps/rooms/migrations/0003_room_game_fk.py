from django.db import migrations, models
import django.db.models.deletion
from django.utils.text import slugify


def link_rooms_to_games(apps, schema_editor):
    Game = apps.get_model('rooms', 'Game')
    Room = apps.get_model('rooms', 'Room')

    # 이름 / 슬러그 / 약어를 모두 색인해 대소문자 무시로 매칭 (예: 'LOL' → lol)
    by_key = {}
    for g in Game.objects.all():
        by_key[g.name.lower()] = g
        by_key[g.slug.lower()] = g
        if g.short_name:
            by_key.setdefault(g.short_name.lower(), g)

    for room in Room.objects.all():
        raw = (room.game_name or '').strip()
        game = by_key.get(raw.lower())
        if game is None:
            # 카탈로그에 없는 게임명은 비활성 게임으로 보존 (필터에는 미노출).
            # slug 충돌 시 create가 아니라 get_or_create로 기존 게임에 흡수.
            base = slugify(raw)[:50] or f'unknown-{room.pk}'
            game, _ = Game.objects.get_or_create(
                slug=base,
                defaults={
                    'name': raw or f'Unknown {room.pk}',
                    'name_ko': raw or f'Unknown {room.pk}',
                    'short_name': raw[:10],
                    'color': '#2c3846',
                    'is_active': False,
                    'sort_order': 999,
                },
            )
            by_key[raw.lower()] = game
        room.game = game
        room.save(update_fields=['game'])


def unlink_rooms(apps, schema_editor):
    Room = apps.get_model('rooms', 'Room')
    for room in Room.objects.select_related('game'):
        room.game_name = room.game.name if room.game else ''
        room.save(update_fields=['game_name'])


class Migration(migrations.Migration):

    dependencies = [
        ('rooms', '0002_game'),
    ]

    operations = [
        migrations.AddField(
            model_name='room',
            name='game',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='rooms',
                to='rooms.game',
                verbose_name='게임',
            ),
        ),
        migrations.RunPython(link_rooms_to_games, unlink_rooms),
    ]
