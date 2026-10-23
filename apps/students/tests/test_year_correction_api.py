"""
API tests for the bulk academic-year correction endpoint (Task 2).

Covers:
- request validation (empty list, missing fields, identical years,
  invalid date, nonexistent year IDs, non-integer IDs) with field-specific
  errors and no side effects;
- permission enforcement: only ADMIN and SECRETARY may call the endpoint
  (DEAN, TEACHER, ACCOUNTANT, STUDENT all receive 403);
- mixed batches: eligible students are transferred while students with a
  source-year payment are blocked and left completely untouched;
- nonexistent student IDs reported as blocked without a matricule.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.university.models import (
    AcademicYear, Faculty, Program, Department, Level, ProgramFee,
)
from apps.students.models import Student, Enrollment
from apps.finance.models import StudentBalance, TuitionPayment

User = get_user_model()

URL = '/api/v1/students/correct-academic-year/'
ENROLLMENT_DATE = '2026-10-22'
ORIGINAL_ENROLLMENT_DATE = date(2025, 9, 1)


def _make_user(username, role, **kwargs):
    return User.objects.create_user(
        username=username,
        email=f'{username}@test.com',
        password='testpass123',
        role=role,
        **kwargs,
    )


class AcademicYearCorrectionAPITests(TestCase):
    """POST /api/v1/students/correct-academic-year/."""

    def setUp(self):
        self.level_l1, _ = Level.objects.get_or_create(name='L1', defaults={'order': 1})
        self.faculty = Faculty.objects.create(name='CYAPI Faculty', code='CYAP')
        self.department = Department.objects.create(
            name='CYAPI Dept', code='CYAD', faculty=self.faculty
        )
        self.program = Program.objects.create(
            name='CYAPI Program',
            code='CYA-PG',
            department=self.department,
            tuition_fee=Decimal('300000.00'),
        )
        self.program.levels.add(self.level_l1)

        self.source_year = AcademicYear.objects.create(
            name='2025-26CYAPI',
            start_date=date(2025, 9, 1),
            end_date=date(2026, 6, 30),
        )
        self.target_year = AcademicYear.objects.create(
            name='2026-27CYAPI',
            start_date=date(2026, 9, 1),
            end_date=date(2027, 6, 30),
        )
        # Keep a single is_current context so student-creation signals stay out of the way.
        AcademicYear.objects.exclude(
            pk__in=[self.source_year.pk, self.target_year.pk]
        ).update(is_current=False)

        # Exact target-year fee for the target level.
        ProgramFee.objects.create(
            program=self.program,
            level=self.level_l1,
            academic_year=self.target_year,
            amount=Decimal('123456.00'),
        )

        self.student = self._create_eligible_student('cyapi_amina', 'CYAP2526MA000020')

        blocked_user = _make_user(
            'cyapi_bilal', 'STUDENT', first_name='Bilal', last_name='Corr', gender='M'
        )
        self.blocked_student = Student.objects.create(
            user=blocked_user,
            student_id='CYAP2526MA000021',
            program=self.program,
            current_level=self.level_l1,
            enrollment_date=ORIGINAL_ENROLLMENT_DATE,
        )
        self._create_source_enrollment(self.blocked_student)
        TuitionPayment.objects.create(
            student=self.blocked_student,
            academic_year=self.source_year,
            amount=Decimal('10000.00'),
            reference='CYAPI-BLK-PAY',
            payment_date=date(2025, 10, 1),
            status='COMPLETED',
        )

        self.admin_user = _make_user('cyapi_admin', 'ADMIN', first_name='Ada', last_name='Root')
        self.secretary_user = _make_user(
            'cyapi_secretary', 'SECRETARY', first_name='Sam', last_name='Sec'
        )
        self.dean_user = _make_user('cyapi_dean', 'DEAN', first_name='Dan', last_name='Dean')
        self.teacher_user = _make_user(
            'cyapi_teacher', 'TEACHER', first_name='Ted', last_name='Teach'
        )
        self.accountant_user = _make_user(
            'cyapi_accountant', 'ACCOUNTANT', first_name='Ann', last_name='Count'
        )
        self.student_viewer = _make_user(
            'cyapi_viewer', 'STUDENT', first_name='Vic', last_name='Viewer'
        )

        self.client = APIClient()

    # ------------------------------------------------------------------
    # Fixtures / helpers
    # ------------------------------------------------------------------

    def _create_eligible_student(self, username, student_id):
        user = _make_user(
            username, 'STUDENT', first_name='Amina', last_name='Corr', gender='M'
        )
        student = Student.objects.create(
            user=user,
            student_id=student_id,
            program=self.program,
            current_level=self.level_l1,
            enrollment_date=ORIGINAL_ENROLLMENT_DATE,
        )
        self._create_source_enrollment(student)
        return student

    def _create_source_enrollment(self, student):
        enrollment = Enrollment.objects.create(
            student=student,
            academic_year=self.source_year,
            program=self.program,
            level=self.level_l1,
            status='ENROLLED',
        )
        StudentBalance.objects.create(
            student=student,
            academic_year=self.source_year,
            total_due=Decimal('300000.00'),
            total_paid=Decimal('0.00'),
        )
        return enrollment

    def _payload(self, student_ids, source=None, target=None, enrollment_date=ENROLLMENT_DATE):
        # Accepts either an AcademicYear instance or a raw pk.
        source = self.source_year if source is None else source
        target = self.target_year if target is None else target
        return {
            'student_ids': student_ids,
            'source_academic_year': getattr(source, 'pk', source),
            'target_academic_year': getattr(target, 'pk', target),
            'enrollment_date': enrollment_date,
        }

    def _post(self, payload, user):
        self.client.force_authenticate(user=user)
        return self.client.post(URL, payload, format='json')

    def _assert_students_unchanged(self):
        self.student.refresh_from_db()
        self.assertEqual(self.student.student_id, 'CYAP2526MA000020')
        self.assertEqual(self.student.enrollment_date, ORIGINAL_ENROLLMENT_DATE)
        self.assertEqual(
            Enrollment.objects.filter(
                student=self.student, academic_year=self.source_year
            ).count(),
            1,
        )
        self.assertFalse(
            Enrollment.objects.filter(
                student=self.student, academic_year=self.target_year
            ).exists()
        )
        self.blocked_student.refresh_from_db()
        self.assertEqual(self.blocked_student.student_id, 'CYAP2526MA000021')
        self.assertEqual(self.blocked_student.enrollment_date, ORIGINAL_ENROLLMENT_DATE)
        self.assertTrue(
            TuitionPayment.objects.filter(
                student=self.blocked_student, academic_year=self.source_year
            ).exists()
        )

    def _assert_validation_error(self, response, *fields):
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error']['code'], 'VALIDATION_ERROR')
        details = response.data['error']['details']
        for field in fields:
            # Per-item errors are flattened with dotted keys (e.g. 'student_ids.0').
            has_field = any(
                key == field or key.startswith(f'{field}.') for key in details
            )
            self.assertTrue(has_field, f'missing error field {field!r}: {details}')

    # ------------------------------------------------------------------
    # Request validation
    # ------------------------------------------------------------------

    def test_rejects_empty_student_list(self):
        response = self._post(self._payload([]), self.admin_user)
        self._assert_validation_error(response, 'student_ids')
        self._assert_students_unchanged()

    def test_rejects_non_integer_student_ids(self):
        response = self._post(self._payload(['abc']), self.admin_user)
        self._assert_validation_error(response, 'student_ids')
        self._assert_students_unchanged()

    def test_rejects_zero_student_id(self):
        response = self._post(self._payload([0]), self.admin_user)
        self._assert_validation_error(response, 'student_ids')

    def test_rejects_missing_source_year(self):
        payload = self._payload([self.student.pk])
        payload.pop('source_academic_year')
        response = self._post(payload, self.admin_user)
        self._assert_validation_error(response, 'source_academic_year')
        self._assert_students_unchanged()

    def test_rejects_missing_target_year(self):
        payload = self._payload([self.student.pk])
        payload.pop('target_academic_year')
        response = self._post(payload, self.admin_user)
        self._assert_validation_error(response, 'target_academic_year')
        self._assert_students_unchanged()

    def test_rejects_missing_enrollment_date(self):
        payload = self._payload([self.student.pk])
        payload.pop('enrollment_date')
        response = self._post(payload, self.admin_user)
        self._assert_validation_error(response, 'enrollment_date')
        self._assert_students_unchanged()

    def test_rejects_invalid_enrollment_date(self):
        response = self._post(
            self._payload([self.student.pk], enrollment_date='2026-13-01'),
            self.admin_user,
        )
        self._assert_validation_error(response, 'enrollment_date')
        self._assert_students_unchanged()

    def test_rejects_identical_years(self):
        response = self._post(
            self._payload([self.student.pk], target=self.source_year),
            self.admin_user,
        )
        self._assert_validation_error(response, 'target_academic_year')
        self._assert_students_unchanged()

    def test_rejects_nonexistent_year_ids(self):
        payload = self._payload([self.student.pk])
        payload['source_academic_year'] = 999999
        payload['target_academic_year'] = 999998
        response = self._post(payload, self.admin_user)
        self._assert_validation_error(response, 'source_academic_year', 'target_academic_year')
        self._assert_students_unchanged()

    def test_deduplicates_repeated_student_ids(self):
        response = self._post(
            self._payload([self.student.pk, self.student.pk]), self.admin_user
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['transferred']), 1)
        self.assertEqual(response.data['transferred'][0]['student'], self.student.pk)

    # ------------------------------------------------------------------
    # Permissions
    # ------------------------------------------------------------------

    def test_only_admin_and_secretary_may_correct(self):
        for user in (
            self.teacher_user,
            self.accountant_user,
            self.dean_user,
            self.student_viewer,
        ):
            response = self._post(self._payload([self.student.pk]), user)
            self.assertEqual(response.status_code, 403, user.role)

        self.client.force_authenticate(user=None)
        response = self.client.post(
            URL, self._payload([self.student.pk]), format='json'
        )
        self.assertEqual(response.status_code, 401)
        self._assert_students_unchanged()

    def test_admin_can_correct(self):
        response = self._post(self._payload([self.student.pk]), self.admin_user)
        self.assertEqual(response.status_code, 200)
        transferred = response.data['transferred']
        self.assertEqual(len(transferred), 1)
        self.assertEqual(transferred[0]['student'], self.student.pk)
        self.assertEqual(transferred[0]['old_student_id'], 'CYAP2526MA000020')
        self.assertIn('2627', transferred[0]['new_student_id'])
        self.assertEqual(response.data['blocked'], [])

        self.student.refresh_from_db()
        self.assertIn('2627', self.student.student_id)
        self.assertEqual(self.student.enrollment_date, date(2026, 10, 22))
        self.assertFalse(
            Enrollment.objects.filter(
                student=self.student, academic_year=self.source_year
            ).exists()
        )
        self.assertTrue(
            Enrollment.objects.filter(
                student=self.student, academic_year=self.target_year
            ).exists()
        )
        self.assertEqual(
            StudentBalance.objects.get(
                student=self.student, academic_year=self.target_year
            ).total_due,
            Decimal('123456.00'),
        )

    def test_secretary_can_correct(self):
        other = self._create_eligible_student('cyapi_nadia', 'CYAP2526MA000022')
        response = self._post(self._payload([other.pk]), self.secretary_user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['transferred'][0]['student'], other.pk)
        self.assertEqual(response.data['blocked'], [])

    # ------------------------------------------------------------------
    # Mixed batches
    # ------------------------------------------------------------------

    def test_mixed_batch_transfers_eligible_and_blocks_paid_student(self):
        response = self._post(
            self._payload([self.student.pk, self.blocked_student.pk]),
            self.admin_user,
        )
        self.assertEqual(response.status_code, 200)

        transferred = response.data['transferred']
        blocked = response.data['blocked']
        self.assertEqual(len(transferred), 1)
        self.assertEqual(transferred[0]['student'], self.student.pk)
        self.assertEqual(transferred[0]['old_student_id'], 'CYAP2526MA000020')
        self.assertIn('2627', transferred[0]['new_student_id'])

        self.assertEqual(len(blocked), 1)
        self.assertEqual(blocked[0]['student'], self.blocked_student.pk)
        self.assertEqual(blocked[0]['student_id'], 'CYAP2526MA000021')
        self.assertIn('Paiements', blocked[0]['reason'])

        # The blocked student is completely untouched.
        self.blocked_student.refresh_from_db()
        self.assertEqual(self.blocked_student.student_id, 'CYAP2526MA000021')
        self.assertEqual(self.blocked_student.enrollment_date, ORIGINAL_ENROLLMENT_DATE)
        self.assertTrue(
            Enrollment.objects.filter(
                student=self.blocked_student, academic_year=self.source_year
            ).exists()
        )
        self.assertTrue(
            TuitionPayment.objects.filter(
                student=self.blocked_student, academic_year=self.source_year
            ).exists()
        )

        # The eligible student was fully moved.
        self.student.refresh_from_db()
        self.assertIn('2627', self.student.student_id)
        self.assertEqual(self.student.enrollment_date, date(2026, 10, 22))
        self.assertFalse(
            Enrollment.objects.filter(
                student=self.student, academic_year=self.source_year
            ).exists()
        )

    def test_nonexistent_student_is_reported_blocked(self):
        response = self._post(
            self._payload([self.student.pk, 999999]), self.admin_user
        )
        self.assertEqual(response.status_code, 200)
        blocked = response.data['blocked']
        self.assertEqual(len(blocked), 1)
        self.assertEqual(blocked[0]['student'], 999999)
        self.assertIn('introuvable', blocked[0]['reason'])
        self.assertNotIn('student_id', blocked[0])

    def test_preserves_requested_order(self):
        first = self._create_eligible_student('cyapi_omar', 'CYAP2526MA000022')
        second = self._create_eligible_student('cyapi_sara', 'CYAP2526MA000023')
        response = self._post(self._payload([second.pk, first.pk]), self.admin_user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item['student'] for item in response.data['transferred']],
            [second.pk, first.pk],
        )
