from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.services.bulletin import (
    _course_labels,
    _format_score,
    _shape_arabic,
    generate_bulletin_pdf,
)


class BulletinPDFTests(SimpleTestCase):
    def test_bilingual_helpers_keep_french_arabic_and_french_decimal_format(self):
        course = SimpleNamespace(
            name="مبادئ البحث العلمي",
            description="Principes de la recherche scientifique",
            code="ISL-S1-04",
        )

        french, arabic = _course_labels(course)

        self.assertEqual(french, "Principes de la recherche scientifique")
        self.assertEqual(arabic, "مبادئ البحث العلمي")
        self.assertEqual(_format_score(Decimal("18.70")), "18,7")
        self.assertIn("/20", _shape_arabic("الدرجة /20"))
        self.assertIn("2025 - 2026", _shape_arabic("العام الجامعي 2025 - 2026"))
        self.assertTrue(any("\uFB50" <= character <= "\uFEFF" for character in _shape_arabic(arabic)))

    def test_generated_bulletin_uses_the_template_assets_and_two_semester_tables(self):
        faculty = SimpleNamespace(
            name="كلية الدراسات الاسلامية",
            code="الاسلامية",
        )
        department = SimpleNamespace(faculty=faculty)
        program = SimpleNamespace(
            name="الدراسات الاسلامية",
            code="الفقه وأصوله",
            department=department,
        )
        level = SimpleNamespace(name="L1")
        user = SimpleNamespace(
            username="student",
            get_full_name=lambda: "أحمد تراوري",
        )
        student = SimpleNamespace(
            student_id="ISL2526MA000001",
            program=program,
            current_level=level,
            user=user,
        )
        academic_year = SimpleNamespace(name="2025 - 2026")
        semester_one = SimpleNamespace(id=1, semester_type="S1", academic_year=academic_year)
        semester_two = SimpleNamespace(id=2, semester_type="S2", academic_year=academic_year)
        report_card = SimpleNamespace(
            student=student,
            semester=semester_one,
            semester_id=1,
            is_published=True,
            gpa=Decimal("16.25"),
        )

        grades = []
        for index in range(10):
            course = SimpleNamespace(
                name=f"مادة دراسية {index + 1}",
                description=f"Matière académique {index + 1}",
                code=f"S1-{index + 1:02d}",
                credits=1,
            )
            grades.append(SimpleNamespace(
                final_score=Decimal("15.50") + Decimal(index) / 10,
                course=course,
                semester_id=1,
            ))
        for index in range(11):
            course = SimpleNamespace(
                name=f"مقرر الفصل الثاني {index + 1}",
                description=f"Cours du second semestre {index + 1}",
                code=f"S2-{index + 1:02d}",
                credits=1,
            )
            grades.append(SimpleNamespace(
                final_score=Decimal("14.00") + Decimal(index) / 10,
                course=course,
                semester_id=2,
            ))

        with (
            patch(
                "apps.core.services.bulletin._selected_semesters",
                return_value=[semester_one, semester_two],
            ),
            patch(
                "apps.core.services.bulletin._course_grades",
                return_value=grades,
            ),
        ):
            pdf = generate_bulletin_pdf(report_card).getvalue()

        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 100_000)
