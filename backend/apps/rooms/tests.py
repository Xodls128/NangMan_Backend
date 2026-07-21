from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from .models import Game, Room, RoomMembership

User = get_user_model()


def _create_user(**kwargs):
    defaults = {
        'password': 'StrongPass123!',
        'provider': User.Provider.LOCAL,
    }
    defaults.update(kwargs)
    password = defaults.pop('password')
    user = User.objects.create_user(password=password, **defaults)
    return user


class RoomLeaveDeleteTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.game = Game.objects.create(
            slug='test-game-leave',
            name='Test Game Leave',
            name_ko='테스트',
            short_name='TL',
            color='#654321',
        )
        self.owner = _create_user(
            username='leave_owner',
            nickname='방장',
            provider_uid='local_leave_owner',
        )
        self.member = _create_user(
            username='leave_member',
            nickname='멤버',
            provider_uid='local_leave_member',
        )
        self.outsider = _create_user(
            username='leave_outsider',
            nickname='외부',
            provider_uid='local_leave_outsider',
        )
        self.room = Room.create_with_owner(
            owner=self.owner,
            title='나가기 테스트 방',
            game=self.game,
            max_members=5,
            play_time_slot=Room.PlayTimeSlot.EVENING,
        )
        RoomMembership.objects.create(
            room=self.room,
            user=self.member,
            status=RoomMembership.Status.APPROVED,
        )

    def test_member_can_leave_and_reapply(self):
        self.client.force_authenticate(self.member)
        response = self.client.post(f'/api/rooms/{self.room.id}/leave/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            RoomMembership.objects.filter(room=self.room, user=self.member).exists()
        )

        self.room.status = Room.Status.OPEN
        self.room.save(update_fields=['status'])
        apply_response = self.client.post(f'/api/rooms/{self.room.id}/apply/')
        self.assertEqual(apply_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(apply_response.data['status'], RoomMembership.Status.PENDING)

    def test_leave_reopens_closed_room_when_under_capacity(self):
        self.room.max_members = 2
        self.room.status = Room.Status.CLOSED
        self.room.save(update_fields=['max_members', 'status'])

        self.client.force_authenticate(self.member)
        response = self.client.post(f'/api/rooms/{self.room.id}/leave/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.room.refresh_from_db()
        self.assertEqual(self.room.status, Room.Status.OPEN)

    def test_owner_cannot_leave(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(f'/api/rooms/{self.room.id}/leave/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_member_cannot_leave(self):
        self.client.force_authenticate(self.outsider)
        response = self.client.post(f'/api/rooms/{self.room.id}/leave/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_delete_room(self):
        room_id = self.room.id
        self.client.force_authenticate(self.owner)
        response = self.client.delete(f'/api/rooms/{room_id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Room.objects.filter(pk=room_id).exists())

        detail = self.client.get(f'/api/rooms/{room_id}/')
        self.assertEqual(detail.status_code, status.HTTP_404_NOT_FOUND)

    def test_non_owner_cannot_delete_room(self):
        self.client.force_authenticate(self.member)
        response = self.client.delete(f'/api/rooms/{self.room.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Room.objects.filter(pk=self.room.id).exists())


class RoomPlayTimeSlotTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='room_owner',
            password='StrongPass123!',
            nickname='방장',
            provider=User.Provider.LOCAL,
            provider_uid='local_room_owner',
        )
        self.game = Game.objects.create(
            slug='test-game',
            name='Test Game',
            name_ko='테스트 게임',
            short_name='TG',
            color='#123456',
        )
        self.client.force_authenticate(self.user)

    def test_create_room_requires_play_time_slot(self):
        response = self.client.post(
            '/api/rooms/',
            {
                'title': '시간대 없는 방',
                'game': self.game.slug,
                'max_members': 5,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['play_time_slot'][0], '플레이 시간대를 선택해 주세요.')

    def test_create_room_rejects_invalid_play_time_slot(self):
        response = self.client.post(
            '/api/rooms/',
            {
                'title': '잘못된 시간대 방',
                'game': self.game.slug,
                'play_time_slot': 'midnight',
                'max_members': 5,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['play_time_slot'][0], '올바른 플레이 시간대를 선택해 주세요.')

    def test_create_and_retrieve_room_with_play_time_slot(self):
        create_response = self.client.post(
            '/api/rooms/',
            {
                'title': '저녁 파티',
                'description': '저녁에 함께 플레이해요.',
                'game': self.game.slug,
                'play_time_slot': Room.PlayTimeSlot.EVENING,
                'max_members': 5,
            },
            format='json',
        )

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_response.data['play_time_slot'], 'evening')
        self.assertEqual(create_response.data['play_time_label'], '저녁 (18:00~24:00)')

        room_id = create_response.data['id']
        detail_response = self.client.get(f'/api/rooms/{room_id}/')
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data['play_time_slot'], 'evening')
        self.assertEqual(detail_response.data['play_time_label'], '저녁 (18:00~24:00)')

    def test_existing_room_can_have_unspecified_play_time(self):
        room = Room.create_with_owner(
            owner=self.user,
            title='기존 방',
            game=self.game,
            max_members=5,
        )

        response = self.client.get(f'/api/rooms/{room.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['play_time_slot'])
        self.assertIsNone(response.data['play_time_label'])


DISCORD_URL = 'https://discord.gg/testinvite123'


class RoomDiscordInviteTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.game = Game.objects.create(
            slug='discord-game',
            name='Discord Game',
            name_ko='디스코드 게임',
            short_name='DG',
            color='#5865F2',
        )
        self.owner = _create_user(
            username='discord_owner',
            nickname='방장',
            provider_uid='local_discord_owner',
        )
        self.member = _create_user(
            username='discord_member',
            nickname='멤버',
            provider_uid='local_discord_member',
        )
        self.outsider = _create_user(
            username='discord_outsider',
            nickname='외부',
            provider_uid='local_discord_outsider',
        )

    def test_create_room_with_optional_discord_url(self):
        self.client.force_authenticate(self.owner)
        res = self.client.post(
            '/api/rooms/',
            {
                'title': '디스코드 방',
                'game': self.game.slug,
                'play_time_slot': Room.PlayTimeSlot.EVENING,
                'max_members': 5,
                'discord_invite_url': DISCORD_URL,
            },
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['discord_invite_url'], DISCORD_URL)
        room = Room.objects.get(pk=res.data['id'])
        self.assertEqual(room.discord_invite_url, DISCORD_URL)

    def test_create_room_without_discord_url(self):
        self.client.force_authenticate(self.owner)
        res = self.client.post(
            '/api/rooms/',
            {
                'title': '링크 없음',
                'game': self.game.slug,
                'play_time_slot': Room.PlayTimeSlot.MORNING,
                'max_members': 5,
            },
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(res.data['discord_invite_url'])

    def test_owner_can_patch_discord_url(self):
        room = Room.create_with_owner(
            owner=self.owner,
            title='패치 테스트',
            game=self.game,
            play_time_slot=Room.PlayTimeSlot.AFTERNOON,
        )
        self.client.force_authenticate(self.owner)
        res = self.client.patch(
            f'/api/rooms/{room.id}/',
            {'discord_invite_url': DISCORD_URL},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['discord_invite_url'], DISCORD_URL)

    def test_owner_can_clear_discord_url(self):
        room = Room.create_with_owner(
            owner=self.owner,
            title='삭제 테스트',
            game=self.game,
            play_time_slot=Room.PlayTimeSlot.AFTERNOON,
            discord_invite_url=DISCORD_URL,
        )
        self.client.force_authenticate(self.owner)
        res = self.client.patch(
            f'/api/rooms/{room.id}/',
            {'discord_invite_url': ''},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIsNone(res.data['discord_invite_url'])

    def test_non_owner_cannot_patch(self):
        room = Room.create_with_owner(
            owner=self.owner,
            title='권한 테스트',
            game=self.game,
            play_time_slot=Room.PlayTimeSlot.AFTERNOON,
        )
        RoomMembership.objects.create(
            room=room,
            user=self.member,
            status=RoomMembership.Status.APPROVED,
        )
        self.client.force_authenticate(self.member)
        res = self.client.patch(
            f'/api/rooms/{room.id}/',
            {'discord_invite_url': DISCORD_URL},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_sees_discord_url_outsider_does_not(self):
        room = Room.create_with_owner(
            owner=self.owner,
            title='노출 테스트',
            game=self.game,
            play_time_slot=Room.PlayTimeSlot.EVENING,
            discord_invite_url=DISCORD_URL,
        )
        RoomMembership.objects.create(
            room=room,
            user=self.member,
            status=RoomMembership.Status.APPROVED,
        )
        self.client.force_authenticate(self.member)
        member_res = self.client.get(f'/api/rooms/{room.id}/')
        self.assertEqual(member_res.data['discord_invite_url'], DISCORD_URL)

        self.client.force_authenticate(self.outsider)
        outsider_res = self.client.get(f'/api/rooms/{room.id}/')
        self.assertIsNone(outsider_res.data['discord_invite_url'])
