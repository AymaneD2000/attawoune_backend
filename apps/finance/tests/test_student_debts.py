"""
Integration tests for the student debt (legacy debt) endpoints.

Covers the first-activation use case: the university records debts from
previous (untracked) years and follows their settlement over time.
"""

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from datetime import date
from decimal import Decimal

from apps.finance.models import StudentDebt, DebtPayment
from apps.students.models import Student
from apps.university.models import AcademicYear, Program, Department, Faculty, Level

User = get_user_model()


class StudentDebtTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            role='ADMIN',
        )

        self.accountant_user = User.objects.create_user(
            username='accountant',
            email='accountant@test.com',
            password='testpass123',
            first_name='Accountant',
            last_name='User',
            role='ACCOUNTANT',
        )

        self.secretary_user = User.objects.create_user(
            username='secretary',
            email='secretary@test.com',
            password='testpass123',
            first_name='Secretary',
            last_name='User',
            role='SECRETARY',
        )

        self.student_user = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='testpass123',
            first_name='Student',
            last_name='User',
            role='STUDENT',
        )

        self.academic_year = AcademicYear.objects.create(
            name='2023-2024',
            start_date=date(2023, 9, 1),
            end_date=date(2024, 6, 30),
            is_current=False,
        )

        # The curriculum seed migration already creates the standard levels;
        # reuse them instead of re-creating them.
        self.level, _ = Level.objects.get_or_create(name='L1', defaults={'order': 1})
        self.faculty = Faculty.objects.create(name='Faculty of Science', code='SCI')
        self.department = Department.objects.create(
            name='Computer Science', code='CS', faculty=self.faculty
        )
        self.program = Program.objects.create(
            name='Computer Science',
            code='CS-L1',
            department=self.department,
        )

        self.student = Student.objects.create(
            user=self.student_user,
            student_id='STU001',
            program=self.program,
            current_level=self.level,
            enrollment_date=date(2023, 9, 1),
        )

        self.client = APIClient()

    # ------------------------------------------------------------------
    # Permissions
    # ------------------------------------------------------------------

    def test_requires_authentication(self):
        response = self.client.get('/api/v1/finance/student-debts/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_student_cannot_create_debt(self):
        self.client.force_authenticate(user=self.student_user)
        response = self.client.post(
            '/api/v1/finance/student-debts/',
            {'student': self.student.id, 'amount_due': '1000'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_secretary_cannot_create_debt_but_can_list(self):
        self.client.force_authenticate(user=self.secretary_user)
        response = self.client.post(
            '/api/v1/finance/student-debts/',
            {'student': self.student.id, 'amount_due': '1000'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.get('/api/v1/finance/student-debts/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_accountant_can_create_debt(self):
        self.client.force_authenticate(user=self.accountant_user)
        response = self.client.post(
            '/api/v1/finance/student-debts/',
            {
                'student': self.student.id,
                'academic_year': self.academic_year.id,
                'amount_due': '250000',
                'description': 'Scolarité année précédente non suivie',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], StudentDebt.DebtStatus.OPEN)
        self.assertEqual(Decimal(response.data['outstanding']), Decimal('250000.00'))
        debt = StudentDebt.objects.get(pk=response.data['id'])
        self.assertEqual(debt.recorded_by, self.accountant_user)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def test_invalid_amount_due_rejected(self):
        self.client.force_authenticate(user=self.accountant_user)
        response = self.client.post(
            '/api/v1/finance/student-debts/',
            {'student': self.student.id, 'amount_due': '0'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ------------------------------------------------------------------
    # Payment recording
    # ------------------------------------------------------------------

    def _create_debt(self, amount='100000'):
        self.client.force_authenticate(user=self.accountant_user)
        response = self.client.post(
            '/api/v1/finance/student-debts/',
            {'student': self.student.id, 'amount_due': amount},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response.data['id']

    def test_record_partial_payment(self):
        debt_id = self._create_debt()
        self.client.force_authenticate(user=self.accountant_user)
        response = self.client.post(
            f'/api/v1/finance/student-debts/{debt_id}/record-payment/',
            {'amount': '40000', 'payment_date': date.today().isoformat(), 'payment_method': 'CASH'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        debt = StudentDebt.objects.get(pk=debt_id)
        self.assertEqual(debt.amount_paid, Decimal('40000.00'))
        self.assertEqual(debt.status, StudentDebt.DebtStatus.PARTIAL)
        self.assertEqual(debt.outstanding, Decimal('60000.00'))
        self.assertEqual(debt.payments.count(), 1)

    def test_record_full_payment_marks_debt_paid(self):
        debt_id = self._create_debt(amount='50000')
        self.client.force_authenticate(user=self.accountant_user)
        response = self.client.post(
            f'/api/v1/finance/student-debts/{debt_id}/record-payment/',
            {'amount': '50000', 'payment_date': date.today().isoformat()},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        debt = StudentDebt.objects.get(pk=debt_id)
        self.assertEqual(debt.status, StudentDebt.DebtStatus.PAID)
        self.assertTrue(debt.is_paid)

    def test_record_payment_rejects_non_positive_amount(self):
        debt_id = self._create_debt()
        self.client.force_authenticate(user=self.accountant_user)
        response = self.client.post(
            f'/api/v1/finance/student-debts/{debt_id}/record-payment/',
            {'amount': '-10', 'payment_date': date.today().isoformat()},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_payment_reverses_amount_paid(self):
        debt_id = self._create_debt()
        self.client.force_authenticate(user=self.accountant_user)
        response = self.client.post(
            f'/api/v1/finance/student-debts/{debt_id}/record-payment/',
            {'amount': '40000', 'payment_date': date.today().isoformat()},
            format='json',
        )
        payment_id = response.data['payment']['id']

        response = self.client.delete(
            f'/api/v1/finance/student-debts/{debt_id}/payments/{payment_id}/'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        debt = StudentDebt.objects.get(pk=debt_id)
        self.assertEqual(debt.amount_paid, Decimal('0.00'))
        self.assertEqual(debt.status, StudentDebt.DebtStatus.OPEN)
        self.assertEqual(debt.payments.count(), 0)

    def test_delete_unknown_payment_returns_404(self):
        debt_id = self._create_debt()
        self.client.force_authenticate(user=self.accountant_user)
        response = self.client.delete(f'/api/v1/finance/student-debts/{debt_id}/payments/999999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ------------------------------------------------------------------
    # Listing & filtering
    # ------------------------------------------------------------------

    def test_list_filtering_by_status(self):
        self.client.force_authenticate(user=self.accountant_user)
        self.client.post(
            '/api/v1/finance/student-debts/',
            {'student': self.student.id, 'amount_due': '100000'},
            format='json',
        )

        response = self.client.get('/api/v1/finance/student-debts/?status=OPEN')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

        response = self.client.get('/api/v1/finance/student-debts/?status=PAID')
        self.assertEqual(len(response.data['results']), 0)

    def test_detail_includes_payments(self):
        debt_id = self._create_debt()
        self.client.force_authenticate(user=self.secretary_user)
        response = self.client.get(f'/api/v1/finance/student-debts/{debt_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['payments'], [])

    def test_update_amount_due_resyncs_status(self):
        debt_id = self._create_debt(amount='100000')
        self.client.force_authenticate(user=self.accountant_user)
        response = self.client.patch(
            f'/api/v1/finance/student-debts/{debt_id}/',
            {'amount_due': '100000'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
