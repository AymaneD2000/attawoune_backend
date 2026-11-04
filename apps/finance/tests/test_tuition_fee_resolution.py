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

    def test_saving_program_fees_updates_existing_balances(self):
        l1_student = self._student(self.l1)
        register_student_in_year(l1_student, self.year, level=self.l1, program=self.program)
        l2_student = self._student(self.l2)
        register_student_in_year(l2_student, self.year, level=self.l2, program=self.program)
        StudentBalance.objects.filter(student=l1_student).update(total_paid=Decimal('20000.00'))

        client = APIClient()
        client.force_authenticate(self.admin)
        response = client.patch(
            f'/api/v1/university/programs/{self.program.id}/',
            {'fees_config': {str(self.l1.id): '100000.00', str(self.l2.id): '150000.00'}},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)

        l1_balance = StudentBalance.objects.get(student=l1_student, academic_year=self.year)
        l2_balance = StudentBalance.objects.get(student=l2_student, academic_year=self.year)
        self.assertEqual(l1_balance.total_due, Decimal('100000.00'))
        self.assertEqual(l1_balance.total_paid, Decimal('20000.00'))
        self.assertEqual(l2_balance.total_due, Decimal('150000.00'))

        # The Recouvrement list reads the stored balances.
        response = client.get('/api/v1/finance/student-balances/outstanding/')
        dues = {row['student']: Decimal(str(row['total_due'])) for row in response.data['results']}
        self.assertEqual(dues[l1_student.id], Decimal('100000.00'))
        self.assertEqual(dues[l2_student.id], Decimal('150000.00'))

    def _next_year(self):
        self.year.is_current = False
        self.year.save(update_fields=['is_current'])
        return AcademicYear.objects.create(
            name='2096-2097', start_date=date(2096, 9, 1),
            end_date=date(2097, 7, 1), is_current=True,
        )

    def test_level_fees_carry_over_to_the_next_academic_year(self):
        next_year = self._next_year()
        # No fee row was saved for the new year: the L1 fee carries over.
        self.assertEqual(resolve_tuition_due(self.program, self.l1, next_year), Decimal('125000.00'))

        client = APIClient()
        client.force_authenticate(self.admin)
        response = client.get('/api/v1/university/programs/')
        item = next(p for p in response.data['results'] if p['id'] == self.program.id)
        self.assertEqual(
            {f['level']: f['amount'] for f in item['fees']},
            {self.l1.id: '125000.00'},
        )

    def test_finished_year_balance_is_frozen(self):
        student = self._student(self.l1)
        register_student_in_year(student, self.year, level=self.l1, program=self.program)
        StudentBalance.objects.filter(student=student, academic_year=self.year).update(
            total_due=Decimal('300000.00'),
        )
        self._next_year()

        # Fees change during the new year…
        client = APIClient()
        client.force_authenticate(self.admin)
        response = client.patch(
            f'/api/v1/university/programs/{self.program.id}/',
            {'fees_config': {str(self.l1.id): '90000.00'}}, format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)

        # …and a late payment is recorded for the finished year.
        response = client.post('/api/v1/finance/tuition-payments/', {
            'student': student.id,
            'academic_year': self.year.id,
            'amount': '40000.00',
            'payment_method': 'CASH',
            'payment_date': '2096-10-01',
        })
        self.assertEqual(response.status_code, 201, response.data)

        old_balance = StudentBalance.objects.get(student=student, academic_year=self.year)
        self.assertEqual(old_balance.total_due, Decimal('300000.00'))
        self.assertEqual(old_balance.total_paid, Decimal('40000.00'))
        # The old year's fee row is untouched; the new price is stored for the new year.
        self.assertEqual(
            ProgramFee.objects.get(program=self.program, level=self.l1, academic_year=self.year).amount,
            Decimal('125000.00'),
        )
