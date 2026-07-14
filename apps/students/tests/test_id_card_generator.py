from datetime import date
from io import BytesIO
from types import SimpleNamespace

from django.test import SimpleTestCase
from PIL import Image

from apps.students.services.id_card import IDCardGenerator


class FakeEnrollmentManager:
    def __init__(self, enrollment):
        self.enrollment = enrollment

    def select_related(self, *_args):
        return self

    def filter(self, **_kwargs):
        return self

    def order_by(self, *_args):
        return self

    def first(self):
        return self.enrollment


class StudentIDCardTests(SimpleTestCase):
    def test_generates_print_ready_branded_card_with_arabic_identity(self):
        academic_year = SimpleNamespace(
            name="2025 - 2026",
            start_date=date(2025, 10, 6),
            end_date=date(2026, 9, 10),
        )
        student = SimpleNamespace(
            student_id="ISL2526MA000001",
            enrollment_date=date(2025, 10, 6),
            status="ACTIVE",
            get_status_display=lambda: "Actif",
            photo=None,
            user=SimpleNamespace(
                username="ahmed",
                get_full_name=lambda: "أحمد تراوري",
            ),
            program=SimpleNamespace(name="الدراسات الاسلامية"),
            current_level=SimpleNamespace(
                get_name_display=lambda: "Licence 2",
                __str__=lambda self: "Licence 2",
            ),
            enrollments=FakeEnrollmentManager(
                SimpleNamespace(academic_year=academic_year),
            ),
        )

        png = IDCardGenerator(student).generate().getvalue()
        image = Image.open(BytesIO(png))

        self.assertEqual(image.format, "PNG")
        self.assertEqual(image.size, (1011, 638))
        self.assertGreater(len(png), 80_000)
        self.assertNotEqual(image.getpixel((20, 20)), (255, 255, 255))
        self.assertNotEqual(image.getpixel((20, 600)), (255, 255, 255))
