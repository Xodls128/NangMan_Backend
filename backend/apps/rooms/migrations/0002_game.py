from django.db import migrations, models

GAME_CATALOG = [
    {
        'slug': 'lol',
        'name': 'League of Legends',
        'name_ko': '리그 오브 레전드',
        'short_name': 'LoL',
        'color': '#c89b3c',
        'sort_order': 1,
    },
    {
        'slug': 'valorant',
        'name': 'Valorant',
        'name_ko': '발로란트',
        'short_name': 'VAL',
        'color': '#fa4454',
        'sort_order': 2,
    },
    {
        'slug': 'overwatch2',
        'name': 'Overwatch 2',
        'name_ko': '오버워치 2',
        'short_name': 'OW2',
        'color': '#f99e1a',
        'sort_order': 3,
    },
    {
        'slug': 'pubg',
        'name': 'PUBG',
        'name_ko': '배틀그라운드',
        'short_name': 'PUBG',
        'color': '#4a90d9',
        'sort_order': 4,
    },
    {
        'slug': 'lostark',
        'name': 'Lost Ark',
        'name_ko': '로스트아크',
        'short_name': 'LA',
        'color': '#8a63d2',
        'sort_order': 5,
    },
    {
        'slug': 'minecraft',
        'name': 'Minecraft',
        'name_ko': '마인크래프트',
        'short_name': 'MC',
        'color': '#3fa34d',
        'sort_order': 6,
    },
]


def seed_games(apps, schema_editor):
    Game = apps.get_model('rooms', 'Game')
    for spec in GAME_CATALOG:
        Game.objects.update_or_create(slug=spec['slug'], defaults=spec)


def unseed_games(apps, schema_editor):
    Game = apps.get_model('rooms', 'Game')
    Game.objects.filter(slug__in=[g['slug'] for g in GAME_CATALOG]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('rooms', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Game',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.SlugField(max_length=50, unique=True, verbose_name='슬러그')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='게임명')),
                ('name_ko', models.CharField(max_length=100, verbose_name='한국어명')),
                ('short_name', models.CharField(help_text='아이콘 플레이스홀더에 표시', max_length=10, verbose_name='약어')),
                ('color', models.CharField(help_text='#rrggbb', max_length=7, verbose_name='브랜드 색')),
                ('icon', models.ImageField(blank=True, upload_to='games/', verbose_name='아이콘')),
                ('is_active', models.BooleanField(default=True, verbose_name='활성')),
                ('sort_order', models.PositiveSmallIntegerField(default=0, verbose_name='정렬 순서')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성일')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='수정일')),
            ],
            options={
                'verbose_name': '게임',
                'verbose_name_plural': '게임',
                'ordering': ['sort_order', 'id'],
            },
        ),
        migrations.RunPython(seed_games, unseed_games),
    ]
