from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from .models import Game, Room

User = get_user_model()


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
