from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.finance.models import StudentBalance
from apps.students.models import Student
from apps.university.models import AcademicYear, Department, Faculty, Level, Program


class BalanceReconciliationRegressionTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='balance_admin', password='ComplexPass123!', role='ADMIN'
        )
        student_user = User.objects.create_user(
            username='balance_student', password='ComplexPass123!', role='STUDENT'
        )
        self.year = AcademicYear.objects.create(
            name='2097-2098', start_date=date(2097, 9, 1),
            end_date=date(2098, 7, 1), is_current=True,
        )
        faculty = Faculty.objects.create(name='Balance Faculty', code='BLF')
        department = Department.objects.create(
            name='Balance Department', code='BLD', faculty=faculty,
        )
        level = Level.objects.get_or_create(name='L1', defaults={'order': 1})[0]
        program = Program.objects.create(
            name='Balance Program', code='BLP', department=department,
            duration_years=1, tuition_fee=Decimal('1000.00'),
        )
        program.levels.add(level)
        self.student = Student.objects.create(
            user=student_user, student_id='BLS0001', program=program,
            current_level=level, enrollment_date=date(2097, 9, 1),
        )
        second_user = User.objects.create_user(
            username='balance_student_two', password='ComplexPass123!', role='STUDENT'
        )
        self.second_student = Student.objects.create(
            user=second_user, student_id='BLS0002', program=program,
            current_level=level, enrollment_date=date(2097, 9, 1),
        )
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_create_update_refund_and_delete_reconcile_from_ledger(self):
        response = self.client.post('/api/v1/finance/tuition-payments/', {
            'student': self.student.id,
            'academic_year': self.year.id,
            'amount': '100.00',
            'payment_method': 'CASH',
            'payment_date': '2097-10-01',
        })
        self.assertEqual(response.status_code, 201, response.data)
        payment_id = response.data['id']
        balance = StudentBalance.objects.get(student=self.student, academic_year=self.year)
        self.assertEqual(balance.total_paid, Decimal('100.00'))

        response = self.client.patch(
            f'/api/v1/finance/tuition-payments/{payment_id}/',
            {'amount': '150.00'}, format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        balance.refresh_from_db()
        self.assertEqual(balance.total_paid, Decimal('150.00'))

        response = self.client.patch(
            f'/api/v1/finance/tuition-payments/{payment_id}/',
            {'student': self.second_student.id}, format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        balance.refresh_from_db()
        second_balance = StudentBalance.objects.get(
            student=self.second_student, academic_year=self.year
        )
        self.assertEqual(balance.total_paid, Decimal('0.00'))
        self.assertEqual(second_balance.total_paid, Decimal('150.00'))

        response = self.client.patch(
            f'/api/v1/finance/tuition-payments/{payment_id}/',
            {'status': 'REFUNDED'}, format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        second_balance.refresh_from_db()
        self.assertEqual(second_balance.total_paid, Decimal('0.00'))

        self.client.patch(
            f'/api/v1/finance/tuition-payments/{payment_id}/',
            {'status': 'COMPLETED'}, format='json',
        )
        response = self.client.delete(f'/api/v1/finance/tuition-payments/{payment_id}/')
        self.assertEqual(response.status_code, 204)
        second_balance.refresh_from_db()
        self.assertEqual(second_balance.total_paid, Decimal('0.00'))
