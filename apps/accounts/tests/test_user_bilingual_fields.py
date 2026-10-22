"""
User profiles capture French AND Arabic names/address (student registration
requires: Prénom/Nom in French + Arabic, Adresse in French + Arabic).
"""

from django.test import TestCase
from rest_framework.test import APIRequestFactory
from django.contrib.auth import get_user_model

from apps.accounts.serializers import UserCreateSerializer, UserSerializer

User = get_user_model()


class UserBilingualFieldsTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='bilingual_admin',
            email='bilingual_admin@test.com',
            password='testpass123',
            role='ADMIN',
        )
        self.factory = APIRequestFactory()

    def _create_context(self, user):
        request = self.factory.get('/')
        request.user = user
        return {'request': request}

    def test_create_user_with_bilingual_fields(self):
        serializer = UserCreateSerializer(
            data={
                'username': 'binom',
                'email': 'binom@test.com',
                'password': 'S3curePass!',
                'password_confirm': 'S3curePass!',
                'first_name': 'Aminata',
                'last_name': 'Diallo',
                'first_name_ar': 'أمينة',
                'last_name_ar': 'ديالو',
                'address': 'Bamako, Mali',
                'address_ar': 'باماكو، مالي',
            },
            context=self._create_context(self.admin_user),
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()

        self.assertEqual(user.first_name_ar, 'أمينة')
        self.assertEqual(user.last_name_ar, 'ديالو')
        self.assertEqual(user.address_ar, 'باماكو، مالي')

    def test_bilingual_fields_are_optional(self):
        user = User.objects.create_user(
            username='u_plain',
            password='testpass123',
            role='STUDENT',
        )
        self.assertEqual(user.first_name_ar, '')
        self.assertEqual(user.last_name_ar, '')
        self.assertEqual(user.address_ar, '')

    def test_user_serializer_exposes_bilingual_fields(self):
        user = User.objects.create_user(
            username='u_ar',
            password='testpass123',
            role='STUDENT',
            first_name_ar='أحمد',
            address_ar='باماكو',
        )
        data = UserSerializer(user).data
        self.assertEqual(data['first_name_ar'], 'أحمد')
        self.assertEqual(data['last_name_ar'], '')
        self.assertEqual(data['address_ar'], 'باماكو')
