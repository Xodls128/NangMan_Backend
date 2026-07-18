from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rooms', '0004_remove_game_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='room',
            name='play_time_slot',
            field=models.CharField(
                blank=True,
                choices=[
                    ('dawn', '새벽 (00:00~06:00)'),
                    ('morning', '오전 (06:00~12:00)'),
                    ('afternoon', '오후 (12:00~18:00)'),
                    ('evening', '저녁 (18:00~24:00)'),
                ],
                help_text='함께 플레이할 선호 시간대. 기존 방은 미지정일 수 있습니다.',
                max_length=20,
                null=True,
                verbose_name='플레이 시간대',
            ),
        ),
    ]
