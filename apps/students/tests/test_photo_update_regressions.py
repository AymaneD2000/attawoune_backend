import tempfile
from datetime import date
from io import BytesIO
from urllib.parse import urlparse

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.students.models import Student
from apps.students.services.id_card import IDCardGenerator
from apps.university.models import Department, Faculty, Level, Program


def uploaded_photo(name, color):
    output = BytesIO()
    Image.new('RGB', (120, 150), color).save(output, format='PNG')
    return SimpleUploadedFile(name, output.getvalue(), content_type='image/png')


class StudentPhotoUpdateRegressionTests(TestCase):
    def setUp(self):
        cache.clear()
        self.media_directory = tempfile.TemporaryDirectory()
        self.media_override = self.settings(MEDIA_ROOT=self.media_directory.name)
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        self.addCleanup(self.media_directory.cleanup)

        self.admin = User.objects.create_user(
            username='photo_admin', password='ComplexPass123!', role='ADMIN'
        )
        student_user = User.objects.create_user(
            username='photo_student', password='ComplexPass123!', role='STUDENT',
            first_name='Aminata', last_name='Traoré',
        )
        faculty = Faculty.objects.create(name='Photo Faculty', code='PHO')
        department = Department.objects.create(
            name='Photo Department', code='PHD', faculty=faculty,
        )
        level = Level.objects.get_or_create(name='L1', defaults={'order': 1})[0]
        program = Program.objects.create(
            name='Photo Program', code='PHP', department=department,
            duration_years=1,
        )
        program.levels.add(level)
        self.student = Student.objects.create(
            user=student_user,
            student_id='PHOTO0001',
            program=program,
            current_level=level,
            enrollment_date=date(2026, 9, 1),
            photo=uploaded_photo('profile.png', 'red'),
        )
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_replacing_photo_updates_profile_media_and_next_id_card(self):
        old_card_key = IDCardGenerator(self.student).cache_key()
        first_card = self.client.get(
            f'/api/v1/students/{self.student.id}/generate_id_card/'
        )
        self.assertEqual(first_card.status_code, 200)
        self.assertIsNotNone(cache.get(old_card_key))

        update = self.client.patch(
            f'/api/v1/students/{self.student.id}/',
            {'photo': uploaded_photo('profile.png', 'blue')},
            format='multipart',
        )
        self.assertEqual(update.status_code, 200, update.data)
        self.assertIn('/media/students/photos/', update.data['photo'])
        self.assertIsNone(cache.get(old_card_key))

        self.student.refresh_from_db()
        self.assertNotEqual(self.student.photo.name, 'students/photos/profile.png')

        media_path = urlparse(update.data['photo']).path
        self.client.force_authenticate(user=None)
        media_response = self.client.get(media_path)
        self.assertEqual(media_response.status_code, 200)
        self.assertEqual(media_response['Content-Type'], 'image/png')

        self.client.force_authenticate(self.admin)
        second_card = self.client.get(
            f'/api/v1/students/{self.student.id}/generate_id_card/'
        )
        self.assertEqual(second_card.status_code, 200)
        self.assertEqual(
            second_card['Cache-Control'], 'private, no-store, max-age=0'
        )
        self.assertNotEqual(first_card['ETag'], second_card['ETag'])
        self.assertNotEqual(first_card.content, second_card.content)
