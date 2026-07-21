from django.db import migrations

ETC_GAME = {
    'slug': 'etc',
    'name': 'Other',
    'name_ko': '기타',
    'short_name': 'ETC',
    'color': '#6b7280',
    'sort_order': 7,
    'is_active': True,
}


def add_etc_game(apps, schema_editor):
    Game = apps.get_model('rooms', 'Game')
    Game.objects.update_or_create(slug=ETC_GAME['slug'], defaults=ETC_GAME)


def remove_etc_game(apps, schema_editor):
    Game = apps.get_model('rooms', 'Game')
    Game.objects.filter(slug=ETC_GAME['slug']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('rooms', '0006_roommembership_last_read_message_id'),
    ]

    operations = [
        migrations.RunPython(add_etc_game, remove_etc_game),
    ]
