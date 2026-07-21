from django.db import migrations, models
from django.db.models import Max


def backfill_last_read_message_id(apps, schema_editor):
    RoomMembership = apps.get_model('rooms', 'RoomMembership')
    ChatMessage = apps.get_model('chats', 'ChatMessage')

    max_by_room = {
        row['room_id']: row['max_id']
        for row in ChatMessage.objects.values('room_id').annotate(max_id=Max('id'))
    }
    memberships = RoomMembership.objects.filter(status='approved')
    to_update = []
    for membership in memberships.iterator():
        max_id = max_by_room.get(membership.room_id)
        if max_id is None:
            continue
        membership.last_read_message_id = max_id
        to_update.append(membership)

    if to_update:
        RoomMembership.objects.bulk_update(to_update, ['last_read_message_id'], batch_size=500)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('rooms', '0005_room_play_time_slot'),
        ('chats', '0002_chatmessage_system_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='roommembership',
            name='last_read_message_id',
            field=models.PositiveBigIntegerField(
                blank=True,
                db_index=True,
                help_text='이 ID 이하의 메시지는 읽음. null은 0과 동일하게 취급.',
                null=True,
                verbose_name='마지막 읽은 메시지 ID',
            ),
        ),
        migrations.RunPython(backfill_last_read_message_id, noop_reverse),
    ]
