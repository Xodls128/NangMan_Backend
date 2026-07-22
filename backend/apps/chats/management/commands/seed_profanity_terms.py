from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.chats.models import ProfanityTerm
from apps.chats.moderation import clear_profanity_wordlist_cache, normalize_for_profanity_check


def iter_wordlist_terms(path: Path):
    for line in path.read_text(encoding='utf-8').splitlines():
        raw = line.strip()
        if not raw or raw.startswith('#'):
            continue
        yield raw


class Command(BaseCommand):
    help = (
        '텍스트 wordlist에서 금지어를 DB로 가져옵니다. '
        '이미 같은 정규화 형태가 있으면 건너뜁니다.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            default=settings.CHAT_PROFANITY_WORDLIST_PATH,
            help='금지어 텍스트 파일 경로 (한 줄에 하나)',
        )
        parser.add_argument(
            '--deactivate-missing',
            action='store_true',
            help='파일에 없는 기존 활성 금지어를 비활성화합니다.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        path = Path(options['file'])
        if not path.is_file():
            self.stderr.write(self.style.ERROR(f'파일이 없습니다: {path}'))
            return

        created = 0
        skipped = 0
        seen_normalized: set[str] = set()

        for raw in iter_wordlist_terms(path):
            normalized = normalize_for_profanity_check(raw)
            if not normalized:
                skipped += 1
                continue
            seen_normalized.add(normalized)
            _, was_created = ProfanityTerm.objects.get_or_create(
                normalized_term=normalized,
                defaults={
                    'term': raw.strip(),
                    'is_active': True,
                    'category': ProfanityTerm.Category.PROFANITY,
                },
            )
            if was_created:
                created += 1
            else:
                skipped += 1

        deactivated = 0
        if options['deactivate_missing']:
            deactivated = (
                ProfanityTerm.objects.filter(is_active=True)
                .exclude(normalized_term__in=seen_normalized)
                .update(is_active=False)
            )

        clear_profanity_wordlist_cache()
        self.stdout.write(
            self.style.SUCCESS(
                f'완료: 생성 {created}, 건너뜀 {skipped}, 비활성화 {deactivated} '
                f'(파일: {path})'
            )
        )
