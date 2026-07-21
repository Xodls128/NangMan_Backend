from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.chats.models import ChatMessage
from apps.rooms.models import Game, Room, RoomMembership

User = get_user_model()


def _create_user(**kwargs):
    defaults = {
        'password': 'StrongPass123!',
        'provider': User.Provider.LOCAL,
    }
    defaults.update(kwargs)
    password = defaults.pop('password')
    return User.objects.create_user(password=password, **defaults)


class UnreadCountTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.game = Game.objects.create(
            slug='unread-game',
            name='Unread Game',
            name_ko='미읽음',
            short_name='UR',
            color='#abcdef',
        )
        self.owner = _create_user(
            username='unread_owner',
            nickname='방장',
            provider_uid='local_unread_owner',
        )
        self.member = _create_user(
            username='unread_member',
            nickname='멤버',
            provider_uid='local_unread_member',
        )
        self.room = Room.create_with_owner(
            owner=self.owner,
            title='미읽음 테스트 방',
            game=self.game,
            max_members=5,
            play_time_slot=Room.PlayTimeSlot.EVENING,
        )
        # 가입 전 과거 메시지
        self.old_msg = ChatMessage.objects.create(
            room=self.room,
            sender=self.owner,
            content='과거 메시지',
        )
        pending = RoomMembership.objects.create(
            room=self.room,
            user=self.member,
            status=RoomMembership.Status.PENDING,
        )
        self.client.force_authenticate(self.owner)
        approve = self.client.post(f'/api/memberships/{pending.id}/approve/')
        self.assertEqual(approve.status_code, status.HTTP_200_OK)

    def _mine_unread(self, user):
        self.client.force_authenticate(user)
        response = self.client.get('/api/rooms/mine/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rooms = response.data if isinstance(response.data, list) else response.data['results']
        by_id = {r['id']: r for r in rooms}
        self.assertIn(self.room.id, by_id)
        return by_id[self.room.id]['unread_count']

    def test_approve_ignores_past_messages(self):
        self.assertEqual(self._mine_unread(self.member), 0)
        membership = RoomMembership.objects.get(room=self.room, user=self.member)
        self.assertEqual(membership.last_read_message_id, self.old_msg.id)

    def test_other_user_message_increments_unread(self):
        ChatMessage.objects.create(
            room=self.room,
            sender=self.owner,
            content='새 메시지',
        )
        self.assertEqual(self._mine_unread(self.member), 1)

    def test_own_and_system_messages_not_counted(self):
        ChatMessage.objects.create(
            room=self.room,
            sender=self.member,
            content='내 메시지',
        )
        ChatMessage.objects.create(
            room=self.room,
            sender=self.owner,
            message_type=ChatMessage.MessageType.SYSTEM,
            content='시스템 안내',
        )
        self.assertEqual(self._mine_unread(self.member), 0)

    def test_read_endpoint_clears_unread(self):
        ChatMessage.objects.create(
            room=self.room,
            sender=self.owner,
            content='읽을 메시지',
        )
        self.assertEqual(self._mine_unread(self.member), 1)

        self.client.force_authenticate(self.member)
        response = self.client.post(f'/api/rooms/{self.room.id}/read/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['unread_count'], 0)
        self.assertEqual(self._mine_unread(self.member), 0)

    def test_messages_list_advances_cursor(self):
        msg = ChatMessage.objects.create(
            room=self.room,
            sender=self.owner,
            content='목록 조회 시 읽음',
        )
        self.assertEqual(self._mine_unread(self.member), 1)

        self.client.force_authenticate(self.member)
        response = self.client.get(f'/api/rooms/{self.room.id}/messages/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        membership = RoomMembership.objects.get(room=self.room, user=self.member)
        self.assertEqual(membership.last_read_message_id, msg.id)
        self.assertEqual(self._mine_unread(self.member), 0)

    def test_read_ignores_smaller_cursor(self):
        msg = ChatMessage.objects.create(
            room=self.room,
            sender=self.owner,
            content='최신',
        )
        self.client.force_authenticate(self.member)
        self.client.post(f'/api/rooms/{self.room.id}/read/', {}, format='json')

        response = self.client.post(
            f'/api/rooms/{self.room.id}/read/',
            {'last_read_message_id': self.old_msg.id},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['last_read_message_id'], msg.id)

    def test_non_member_cannot_read(self):
        outsider = _create_user(
            username='unread_outsider',
            nickname='외부',
            provider_uid='local_unread_outsider',
        )
        self.client.force_authenticate(outsider)
        response = self.client.post(f'/api/rooms/{self.room.id}/read/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_rooms_unread_is_zero(self):
        ChatMessage.objects.create(
            room=self.room,
            sender=self.owner,
            content='목록에는 안 보임',
        )
        self.client.force_authenticate(self.member)
        response = self.client.get('/api/rooms/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rooms = response.data if isinstance(response.data, list) else response.data['results']
        target = next(r for r in rooms if r['id'] == self.room.id)
        self.assertEqual(target['unread_count'], 0)
