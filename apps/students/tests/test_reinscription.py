"""
Re-inscription (year-scoped registration) tests.

Re-inscription is the only allowed cross-year data flow: a student
enrolled in a previous academic year is manually registered into the
active year, which creates the enrollment + the year's financial balance
and syncs the student profile snapshot.
"""

from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from apps.students.models import Student, Enrollment
from apps.finance.models import StudentBalance
from apps.university.models import (
    AcademicYear, Program, ProgramFee, Department, Faculty, Level,
)

User = get_user_model()


class ReinscriptionTests(TestCase):
    def setUp(self):
        self.secretary_user = User.objects.create_user(
            username='secretary_rein',
            email='secretary_rein@test.com',
            password='testpass123',
            first_name='Sec',
            last_name='Retary',
            role='SECRETARY',
        )

        self.student_user_a = User.objects.create_user(
            username='student_rein_a',
            email='rein_a@test.com',
            password='testpass123',
            first_name='Aminata',
            last_name='Diallo',
            role='STUDENT',
        )
        self.student_user_b = User.objects.create_user(
            username='student_rein_b',
            email='rein_b@test.com',
            password='testpass123',
            first_name='Boubacar',
            last_name='Keita',
            role='STUDENT',
        )

        # The curriculum seed migration already creates the standard levels.
        self.level_l1, _ = Level.objects.get_or_create(name='L1', defaults={'order': 1})
        self.level_l2, _ = Level.objects.get_or_create(name='L2', defaults={'order': 2})

        self.faculty = Faculty.objects.create(name='Reinscription Faculty', code='REINF')
        self.department = Department.objects.create(
            name='Reinscription Dept', code='REIND', faculty=self.faculty
        )
        self.program = Program.objects.create(
            name='Reinscription Program',
            code='REIN-PG',
            department=self.department,
            tuition_fee=Decimal('300000.00'),
        )
        self.program.levels.add(self.level_l1, self.level_l2)

        self.previous_year = AcademicYear.objects.create(
            name='2024-25T',
            start_date=date(2024, 9, 1),
            end_date=date(2025, 6, 30),
            is_current=False,
        )
        self.current_year = AcademicYear.objects.create(
            name='2025-26T',
            start_date=date(2025, 9, 1),
            end_date=date(2026, 6, 30),
            is_current=True,
        )
        # Guarantee a single active year (the curriculum seed may create one).
        AcademicYear.objects.exclude(pk=self.current_year.pk).update(is_current=False)

        # Student A: enrolled in the previous year only (re-inscription candidate).
        self.student_a = Student.objects.create(
            user=self.student_user_a,
            student_id='REIN-A',
            program=self.program,
            current_level=self.level_l1,
            enrollment_date=date(2024, 9, 1),
        )
        Enrollment.objects.create(
            student=self.student_a,
            academic_year=self.previous_year,
            program=self.program,
            level=self.level_l1,
            status='ENROLLED',
        )

        # Student B: already enrolled in the current year (not a candidate).
        self.student_b = Student.objects.create(
            user=self.student_user_b,
            student_id='REIN-B',
            program=self.program,
            current_level=self.level_l1,
            enrollment_date=date(2025, 9, 1),
        )
        Enrollment.objects.create(
            student=self.student_b,
            academic_year=self.current_year,
            program=self.program,
            level=self.level_l1,
            status='ENROLLED',
        )

        self.client = APIClient()

    def _as_secretary(self):
        self.client.force_authenticate(user=self.secretary_user)

    # ------------------------------------------------------------------
    # Candidates
    # ------------------------------------------------------------------

    def test_candidates_only_include_previous_year_students(self):
        self._as_secretary()
        response = self.client.get('/api/v1/students/reinscription-candidates/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        ids = [candidate['id'] for candidate in response.data]
        self.assertIn(self.student_a.id, ids)
        self.assertNotIn(self.student_b.id, ids)

        candidate = next(c for c in response.data if c['id'] == self.student_a.id)
        self.assertEqual(candidate['last_year'], self.previous_year.name)
        self.assertEqual(candidate['last_level'], self.level_l1.name)

    def test_candidates_search_by_matricule(self):
        self._as_secretary()
        response = self.client.get('/api/v1/students/reinscription-candidates/?search=REIN-A')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.student_a.id)

    def test_candidates_forbidden_for_non_secretary(self):
        teacher_user = User.objects.create_user(
            username='teacher_rein',
            email='teacher_rein@test.com',
            password='testpass123',
            role='TEACHER',
        )
        self.client.force_authenticate(user=teacher_user)
        response = self.client.get('/api/v1/students/reinscription-candidates/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ------------------------------------------------------------------
    # Re-inscription
    # ------------------------------------------------------------------

    def test_reinscription_creates_enrollment_balance_and_syncs_profile(self):
        self._as_secretary()
        # Remove the auto-created balance so the re-inscription flow creates it.
        StudentBalance.objects.filter(student=self.student_a).delete()

        response = self.client.post(
            '/api/v1/students/reinscription/',
            {'student': self.student_a.id, 'level': self.level_l2.id},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        enrollment = Enrollment.objects.get(student=self.student_a, academic_year=self.current_year)
        self.assertEqual(enrollment.level, self.level_l2)
        self.assertEqual(enrollment.status, 'ENROLLED')

        balance = StudentBalance.objects.get(student=self.student_a, academic_year=self.current_year)
        self.assertEqual(balance.total_due, Decimal('300000.00'))

        self.student_a.refresh_from_db()
        self.assertEqual(self.student_a.current_level, self.level_l2)

    def test_reinscription_balance_uses_program_fee_when_defined(self):
        ProgramFee.objects.create(
            program=self.program,
            level=self.level_l2,
            academic_year=self.current_year,
            amount=Decimal('123456.00'),
        )
        StudentBalance.objects.filter(student=self.student_a).delete()

        self._as_secretary()
        response = self.client.post(
            '/api/v1/students/reinscription/',
            {'student': self.student_a.id, 'level': self.level_l2.id},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        balance = StudentBalance.objects.get(student=self.student_a, academic_year=self.current_year)
        self.assertEqual(balance.total_due, Decimal('123456.00'))

    def test_reinscription_defaults_to_same_level(self):
        self._as_secretary()
        response = self.client.post(
            '/api/v1/students/reinscription/',
            {'student': self.student_a.id},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        enrollment = Enrollment.objects.get(student=self.student_a, academic_year=self.current_year)
        self.assertEqual(enrollment.level, self.level_l1)

    def test_reinscription_rejects_student_already_enrolled(self):
        self._as_secretary()
        response = self.client.post(
            '/api/v1/students/reinscription/',
            {'student': self.student_b.id},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reinscription_requires_active_year(self):
        AcademicYear.objects.filter(pk=self.current_year.pk).update(is_current=False)
        self._as_secretary()
        response = self.client.post(
            '/api/v1/students/reinscription/',
            {'student': self.student_a.id},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ------------------------------------------------------------------
    # New student creation stays year-scoped
    # ------------------------------------------------------------------

    def test_new_student_creation_registers_active_year(self):
        self._as_secretary()
        new_user = User.objects.create_user(
            username='student_rein_c',
            email='rein_c@test.com',
            password='testpass123',
            first_name='Mariam',
            last_name='Sangare',
            role='STUDENT',
        )
        response = self.client.post(
            '/api/v1/students/',
            {
                'user': new_user.id,
                'program': self.program.id,
                'current_level': self.level_l1.id,
                'enrollment_date': '2025-09-01',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        student = Student.objects.get(user=new_user)
        self.assertTrue(
            Enrollment.objects.filter(student=student, academic_year=self.current_year).exists(),
            'New students must be registered in the active academic year.',
        )
        self.assertTrue(
            StudentBalance.objects.filter(student=student, academic_year=self.current_year).exists(),
            'New students must get an active-year financial balance.',
        )
