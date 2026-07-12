from django.db import migrations, models


def fill_provider_fields(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    for user in User.objects.all():
        user.provider = 'local'
        user.provider_uid = f'local_{user.username}'
        user.save(update_fields=['provider', 'provider_uid'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='provider',
            field=models.CharField(
                choices=[('kakao', '카카오'), ('local', '로컬')],
                default='kakao',
                max_length=20,
                verbose_name='로그인 제공자',
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='provider_uid',
            field=models.CharField(
                help_text='카카오 user id 등. 로컬 계정은 local_<username> 형식.',
                max_length=64,
                null=True,
                verbose_name='소셜 고유 ID',
            ),
        ),
        migrations.RunPython(fill_provider_fields, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='user',
            name='provider_uid',
            field=models.CharField(
                help_text='카카오 user id 등. 로컬 계정은 local_<username> 형식.',
                max_length=64,
                verbose_name='소셜 고유 ID',
            ),
        ),
        migrations.AddConstraint(
            model_name='user',
            constraint=models.UniqueConstraint(
                fields=('provider', 'provider_uid'),
                name='uniq_accounts_user_provider_uid',
            ),
        ),
    ]
