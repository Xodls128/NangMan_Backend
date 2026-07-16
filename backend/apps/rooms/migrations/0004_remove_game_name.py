from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('rooms', '0003_room_game_fk'),
    ]

    operations = [
        migrations.AlterField(
            model_name='room',
            name='game',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='rooms',
                to='rooms.game',
                verbose_name='게임',
            ),
        ),
        migrations.RemoveField(
            model_name='room',
            name='game_name',
        ),
    ]
