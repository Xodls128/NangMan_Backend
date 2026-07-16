from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import User
from apps.chats.models import ChatMessage
from apps.rooms.models import Game, Room, RoomMembership

PASSWORD = 'testpass123'

USERS = [
    {
        'username': 'ws_owner',
        'nickname': '방장테스터',
        'email': 'owner@example.com',
    },
    {
        'username': 'ws_member',
        'nickname': '멤버테스터',
        'email': 'member@example.com',
    },
    {
        'username': 'ws_pending',
        'nickname': '대기테스터',
        'email': 'pending@example.com',
    },
    {
        'username': 'ws_outsider',
        'nickname': '외부테스터',
        'email': 'outsider@example.com',
    },
    {
        'username': 'ws_rejected',
        'nickname': '거절테스터',
        'email': 'rejected@example.com',
    },
]

MOCK_USERNAMES = {u['username'] for u in USERS}


class Command(BaseCommand):
    help = (
        '로컬 테스트용 목업 유저/방/멤버십/채팅을 시드합니다. '
        f'비밀번호는 모두 {PASSWORD} 입니다.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--flush',
            action='store_true',
            help='목업 유저가 소유·참여한 방/메시지와 목업 유저를 지운 뒤 다시 시드합니다.',
        )

    def handle(self, *args, **options):
        if not getattr(settings, 'SEED_MOCK_DATA', False):
            raise CommandError(
                'SEED_MOCK_DATA가 비활성화되어 있습니다. '
                'development 설정에서만 실행하세요.'
            )

        with transaction.atomic():
            if options['flush']:
                self._flush_mock()
            users = self._seed_users()
            rooms = self._seed_rooms(users)
            self._seed_messages(users, rooms)

        self.stdout.write(self.style.SUCCESS('목업 시드 완료'))
        self.stdout.write('')
        self.stdout.write('로그인 계정 (비밀번호 공통: testpass123)')
        for u in USERS:
            self.stdout.write(f"  - {u['username']:12} {u['nickname']}")
        self.stdout.write('')
        self.stdout.write('시나리오 요약')
        self.stdout.write('  ws_owner    : 방장 - 대기 신청 수락/거절, 채팅')
        self.stdout.write('  ws_member   : 승인 멤버 - 채팅 입장')
        self.stdout.write('  ws_pending  : 가입 대기 - 메인/나의 방 대기 UI')
        self.stdout.write('  ws_outsider : 미신청 - 가입 신청 모달')
        self.stdout.write('  ws_rejected : 거절됨 - 재신청 불가 안내')

    def _flush_mock(self):
        mock_users = User.objects.filter(username__in=MOCK_USERNAMES)
        room_ids = set(
            Room.objects.filter(owner__in=mock_users).values_list('id', flat=True)
        )
        room_ids.update(
            RoomMembership.objects.filter(user__in=mock_users).values_list('room_id', flat=True)
        )
        ChatMessage.objects.filter(room_id__in=room_ids).delete()
        RoomMembership.objects.filter(room_id__in=room_ids).delete()
        Room.objects.filter(id__in=room_ids).delete()
        deleted, _ = mock_users.delete()
        self.stdout.write(f'기존 목업 데이터 삭제 ({deleted} users cascade 포함)')

    def _seed_users(self):
        users = {}
        for spec in USERS:
            user, created = User.objects.get_or_create(
                username=spec['username'],
                defaults={
                    'email': spec['email'],
                    'nickname': spec['nickname'],
                    'provider': User.Provider.LOCAL,
                    'provider_uid': f"local_{spec['username']}",
                },
            )
            user.set_password(PASSWORD)
            user.email = spec['email']
            user.nickname = spec['nickname']
            user.provider = User.Provider.LOCAL
            user.provider_uid = f"local_{spec['username']}"
            user.save()
            users[spec['username']] = user
            self.stdout.write(f"  user {'created' if created else 'updated'}: {user.username}")
        return users

    def _seed_rooms(self, users):
        owner = users['ws_owner']
        member = users['ws_member']
        pending = users['ws_pending']
        rejected = users['ws_rejected']
        games = {g.slug: g for g in Game.objects.all()}

        # Room A: 방장=ws_owner — 멤버/대기/거절 상태 한곳에
        room_a, created_a = self._get_or_create_owned_room(
            owner=owner,
            title='발로란트 듀오 구함',
            defaults={
                'description': '랭크 골드 이상 / 마이크 필수. 목업 시드 방입니다.',
                'game': games['valorant'],
                'max_members': 5,
                'status': Room.Status.OPEN,
            },
        )
        self._ensure_membership(room_a, member, RoomMembership.Status.APPROVED)
        self._ensure_membership(room_a, pending, RoomMembership.Status.PENDING)
        self._ensure_membership(room_a, rejected, RoomMembership.Status.REJECTED)
        self.stdout.write(f"  room {'created' if created_a else 'ready'}: #{room_a.id} {room_a.title}")

        # Room B: 방장=ws_member — 마이페이지/나의 방용 두 번째 방
        room_b, created_b = self._get_or_create_owned_room(
            owner=member,
            title='리그 스크림 모집',
            defaults={
                'description': '주말 저녁 스크림. ws_member가 방장입니다.',
                'game': games['lol'],
                'max_members': 5,
                'status': Room.Status.OPEN,
            },
        )
        self._ensure_membership(room_b, owner, RoomMembership.Status.APPROVED)
        self.stdout.write(f"  room {'created' if created_b else 'ready'}: #{room_b.id} {room_b.title}")

        # Room C: 빈 오픈 방 — outsider 가입 신청 테스트용
        room_c, created_c = self._get_or_create_owned_room(
            owner=owner,
            title='오버워치 캐주얼',
            defaults={
                'description': '가볍게 한판. 아직 신청자가 없는 방입니다.',
                'game': games['overwatch2'],
                'max_members': 5,
                'status': Room.Status.OPEN,
            },
        )
        self.stdout.write(f"  room {'created' if created_c else 'ready'}: #{room_c.id} {room_c.title}")

        return {'a': room_a, 'b': room_b, 'c': room_c}

    def _get_or_create_owned_room(self, *, owner, title, defaults):
        existing = Room.objects.filter(owner=owner, title=title).first()
        if existing:
            for key, value in defaults.items():
                setattr(existing, key, value)
            existing.save()
            RoomMembership.objects.get_or_create(
                room=existing,
                user=owner,
                defaults={'status': RoomMembership.Status.APPROVED},
            )
            return existing, False
        room = Room.create_with_owner(owner=owner, title=title, **defaults)
        return room, True

    def _ensure_membership(self, room, user, status):
        membership, created = RoomMembership.objects.get_or_create(
            room=room,
            user=user,
            defaults={'status': status},
        )
        if not created and membership.status != status:
            membership.status = status
            membership.save(update_fields=['status', 'updated_at'])

    def _seed_messages(self, users, rooms):
        room = rooms['a']
        owner = users['ws_owner']
        member = users['ws_member']
        samples = [
            (owner, '안녕하세요. 방장입니다. 오늘 몇 시에 가능하세요?'),
            (member, '저 9시 이후 가능합니다!'),
            (owner, '좋아요. 포지션은 듀얼리스트로 구해요.'),
            (member, '네, 제트/레이나 가능합니다.'),
        ]
        # 멱등: 동일 내용이 이미 있으면 스킵
        created_count = 0
        for sender, content in samples:
            exists = ChatMessage.objects.filter(
                room=room,
                sender=sender,
                content=content,
            ).exists()
            if not exists:
                ChatMessage.objects.create(room=room, sender=sender, content=content)
                created_count += 1
        self.stdout.write(f'  chat messages: +{created_count} (room #{room.id})')
