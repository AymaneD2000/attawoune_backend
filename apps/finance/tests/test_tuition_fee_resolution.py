from datetime import date
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.finance.models import StudentBalance
from apps.finance.services.fees import resolve_tuition_due
from apps.students.models import Student
from apps.students.services.registration import register_student_in_year
from apps.university.models import (
    AcademicYear, Department, Faculty, Level, Program, ProgramFee,
)


class TuitionFeeResolutionTests(TestCase):
    """Per-level fees configured on the Filières page must be what students owe;
    the program's tuition_fee is the yearly fallback."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username='fee_admin', password='ComplexPass123!', role='ADMIN'
        )
        self.year = AcademicYear.objects.create(
            name='2095-2096', start_date=date(2095, 9, 1),
            end_date=date(2096, 7, 1), is_current=True,
        )
        faculty = Faculty.objects.create(name='Fee Faculty', code='FEF')
        department = Department.objects.create(
            name='Fee Department', code='FED', faculty=faculty,
        )
        self.l1 = Level.objects.get_or_create(name='L1', defaults={'order': 1})[0]
        self.l2 = Level.objects.get_or_create(name='L2', defaults={'order': 2})[0]
        self.program = Program.objects.create(
            name='Fee Program', code='FEP', department=department,
            duration_years=3, tuition_fee=Decimal('375000.00'),
        )
        self.program.levels.add(self.l1, self.l2)
        ProgramFee.objects.create(
            program=self.program, level=self.l1,
            academic_year=self.year, amount=Decimal('125000.00'),
        )
        self.counter = 0

    def _student(self, level):
        self.counter += 1
        user = User.objects.create_user(
            username=f'fee_student_{self.counter}',
            password='ComplexPass123!', role='STUDENT',
        )
        return Student.objects.create(
            user=user, student_id=f'FES{self.counter:04d}', program=self.program,
            current_level=level, enrollment_date=date(2095, 9, 1),
        )

    def test_resolver_prefers_level_fee_and_falls_back_to_yearly_fee(self):
        self.assertEqual(resolve_tuition_due(self.program, self.l1, self.year), Decimal('125000.00'))
        self.assertEqual(resolve_tuition_due(self.program, self.l2, self.year), Decimal('375000.00'))

    def test_new_student_balance_uses_level_fee(self):
        student = self._student(self.l1)
        register_student_in_year(student, self.year, level=self.l1, program=self.program)
        balance = StudentBalance.objects.get(student=student, academic_year=self.year)
        self.assertEqual(balance.total_due, Decimal('125000.00'))

    def test_registration_aligns_balance_to_enrolled_level(self):
        # Profile says L2 (balance created by the signal) but enrollment is L1.
        student = self._student(self.l2)
        register_student_in_year(student, self.year, level=self.l1, program=self.program)
        balance = StudentBalance.objects.get(student=student, academic_year=self.year)
        self.assertEqual(balance.total_due, Decimal('125000.00'))

    def test_payment_keeps_level_fee_as_total_due(self):
        student = self._student(self.l1)
        register_student_in_year(student, self.year, level=self.l1, program=self.program)
        client = APIClient()
        client.force_authenticate(self.admin)
        response = client.post('/api/v1/finance/tuition-payments/', {
            'student': student.id,
            'academic_year': self.year.id,
            'amount': '50000.00',
            'payment_method': 'CASH',
            'payment_date': '2095-10-01',
        })
        self.assertEqual(response.status_code, 201, response.data)
        balance = StudentBalance.objects.get(student=student, academic_year=self.year)
        self.assertEqual(balance.total_due, Decimal('125000.00'))
        self.assertEqual(balance.total_paid, Decimal('50000.00'))

    def test_recalculate_command_dry_run_then_apply(self):
        student = self._student(self.l1)
        register_student_in_year(student, self.year, level=self.l1, program=self.program)
        StudentBalance.objects.filter(student=student).update(
            total_due=Decimal('375000.00'), total_paid=Decimal('10000.00'),
        )

        out = StringIO()
        call_command('recalculate_balances', '--dry-run', stdout=out)
        self.assertIn('Would update 1', out.getvalue())
        balance = StudentBalance.objects.get(student=student)
        self.assertEqual(balance.total_due, Decimal('375000.00'))

        call_command('recalculate_balances', stdout=StringIO())
        balance.refresh_from_db()
        self.assertEqual(balance.total_due, Decimal('125000.00'))
        self.assertEqual(balance.total_paid, Decimal('10000.00'))
