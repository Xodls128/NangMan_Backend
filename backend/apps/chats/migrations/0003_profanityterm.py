from django.conf import settings
from django.db import migrations, models


def seed_profanity_terms(apps, schema_editor):
    ProfanityTerm = apps.get_model('chats', 'ProfanityTerm')
    # 마이그레이션 중에는 앱 모델의 save()/정규화를 쓰지 않고 직접 채웁니다.
    from apps.chats.moderation.filter import normalize_for_profanity_check

    path = settings.CHAT_PROFANITY_WORDLIST_PATH
    try:
        with open(path, encoding='utf-8') as fh:
            lines = fh.read().splitlines()
    except OSError:
        return

    to_create = []
    seen = set()
    for line in lines:
        raw = line.strip()
        if not raw or raw.startswith('#'):
            continue
        normalized = normalize_for_profanity_check(raw)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        to_create.append(
            ProfanityTerm(
                term=raw,
                normalized_term=normalized,
                is_active=True,
                category='profanity',
                note='초기 wordlist 시드',
            )
        )
    if to_create:
        ProfanityTerm.objects.bulk_create(to_create, ignore_conflicts=True)


def unseed_profanity_terms(apps, schema_editor):
    ProfanityTerm = apps.get_model('chats', 'ProfanityTerm')
    ProfanityTerm.objects.filter(note='초기 wordlist 시드').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('chats', '0002_chatmessage_system_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProfanityTerm',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('term', models.CharField(help_text='관리자가 입력한 원문. 매칭은 정규화 형태 기준입니다.', max_length=100, verbose_name='금지어')),
                ('normalized_term', models.CharField(db_index=True, editable=False, help_text='우회 문자 제거 후 검사용 문자열. 저장 시 자동 설정.', max_length=100, verbose_name='정규화 형태')),
                ('is_active', models.BooleanField(db_index=True, default=True, verbose_name='활성')),
                ('category', models.CharField(choices=[('profanity', '욕설/비속어'), ('hate', '혐오'), ('sexual', '성희롱'), ('other', '기타')], default='profanity', max_length=20, verbose_name='분류')),
                ('note', models.CharField(blank=True, max_length=200, verbose_name='메모')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성일')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='수정일')),
            ],
            options={
                'verbose_name': '금지어',
                'verbose_name_plural': '금지어',
                'ordering': ['term'],
            },
        ),
        migrations.AddConstraint(
            model_name='profanityterm',
            constraint=models.UniqueConstraint(fields=('normalized_term',), name='uniq_chats_profanity_normalized'),
        ),
        migrations.RunPython(seed_profanity_terms, unseed_profanity_terms),
    ]
