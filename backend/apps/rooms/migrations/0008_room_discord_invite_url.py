from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rooms', '0007_game_etc'),
    ]

    operations = [
        migrations.AddField(
            model_name='room',
            name='discord_invite_url',
            field=models.URLField(
                blank=True,
                max_length=512,
                null=True,
                verbose_name='디스코드 초대 링크',
            ),
        ),
    ]
