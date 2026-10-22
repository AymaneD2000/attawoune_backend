"""
Regression test: deliberation must stay display-only.

Deliberation records the decision (promoted / repeated) and the grades
for its own academic year. It must NOT create enrollments or balances in
another academic year — cross-year data only flows through the manual
re-inscription flow (students.views.reinscription).
"""

from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.academics.services.deliberation import DeliberationService
from apps.students.models import Enrollment, Student
from apps.finance.models import StudentBalance
from apps.university.models import AcademicYear, Program, Department, Faculty, Level, Semester

User = get_user_model()


class DeliberationIsolationTests(TestCase):
    def setUp(self):
        self.student_user = User.objects.create_user(
            username='delib_isolation',
            email='delib_isolation@test.com',
            password='testpass123',
            first_name='Del',
            last_name='Iber',
            role='STUDENT',
        )

        self.level_l1, _ = Level.objects.get_or_create(name='L1', defaults={'order': 1})
        self.level_l2, _ = Level.objects.get_or_create(name='L2', defaults={'order': 2})

        faculty = Faculty.objects.create(name='Deliberation Faculty', code='DLB-F')
        department = Department.objects.create(name='Deliberation Dept', code='DLB-D', faculty=faculty)
        self.program = Program.objects.create(
            name='Deliberation Program',
            code='DLB-PG',
            department=department,
            tuition_fee=Decimal('250000.00'),
        )
        self.program.levels.add(self.level_l1, self.level_l2)

        self.year_a = AcademicYear.objects.create(
            name='2024-25D',
            start_date=date(2024, 9, 1),
            end_date=date(2025, 6, 30),
        )
        self.year_b = AcademicYear.objects.create(
            name='2025-26D',
            start_date=date(2025, 9, 1),
            end_date=date(2026, 6, 30),
        )

        # Deliberation needs both semesters on its own year.
        Semester.objects.create(
            academic_year=self.year_a,
            semester_type='S1',
            start_date=date(2024, 9, 1),
            end_date=date(2024, 12, 20),
        )
        Semester.objects.create(
            academic_year=self.year_a,
            semester_type='S2',
            start_date=date(2025, 1, 15),
            end_date=date(2025, 6, 20),
        )

        self.student = Student.objects.create(
            user=self.student_user,
            student_id='DLB-1',
            program=self.program,
            current_level=self.level_l1,
            enrollment_date=date(2024, 9, 1),
        )
        Enrollment.objects.create(
            student=self.student,
            academic_year=self.year_a,
            program=self.program,
            level=self.level_l1,
        )

    def test_deliberation_does_not_create_next_year_data(self):
        promotion = DeliberationService.deliberate_student(self.student, self.year_a)

        # The decision is recorded in the deliberated year only.
        self.assertEqual(promotion.decision, 'REPEATED')  # no grades => GPA 0
        self.assertEqual(promotion.academic_year, self.year_a)
        self.assertEqual(promotion.level_to, self.level_l1)

        # But no enrollment / balance may leak into the next academic year.
        self.assertFalse(
            Enrollment.objects.filter(student=self.student, academic_year=self.year_b).exists(),
            'Deliberation must not create next-year enrollments.',
        )
        self.assertFalse(
            StudentBalance.objects.filter(student=self.student, academic_year=self.year_b).exists(),
            'Deliberation must not create next-year financial balances.',
        )

    def test_enroll_for_next_year_helper_is_removed(self):
        """The automatic transfer helper must no longer exist (manual flow only)."""
        self.assertFalse(hasattr(DeliberationService, 'enroll_for_next_year'))
