from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.finance.models import Expense, Salary, StudentBalance, TuitionPayment
from apps.students.models import Student
from apps.university.models import AcademicYear, Department, Faculty, Level, Program


class FinanceDashboardAnalyticsRegressionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username='finance-analytics-admin',
            password='testpass123',
            role=User.Role.ADMIN,
        )
        employee = User.objects.create_user(
            username='finance-analytics-employee',
            password='testpass123',
            role=User.Role.TEACHER,
            first_name='Awa',
            last_name='Traore',
        )
        student_user = User.objects.create_user(
            username='finance-analytics-student',
            password='testpass123',
            role=User.Role.STUDENT,
        )
        faculty = Faculty.objects.create(name='Finance Faculty', code='FIN-FAC')
        department = Department.objects.create(name='Finance Department', code='FIN-DEP', faculty=faculty)
        level, _ = Level.objects.get_or_create(name='L1', defaults={'order': 1})
        program = Program.objects.create(name='Finance Program', code='FIN-PROG', department=department)
        program.levels.add(level)
        student = Student.objects.create(
            user=student_user,
            student_id='FIN-STUDENT-1',
            program=program,
            current_level=level,
            enrollment_date=date(2025, 9, 1),
        )
        academic_year = AcademicYear.objects.create(
            name='2025-2026',
            start_date=date(2025, 9, 1),
            end_date=date(2026, 8, 31),
            is_current=True,
        )

        TuitionPayment.objects.create(
            student=student,
            academic_year=academic_year,
            level=level,
            amount=Decimal('100000.00'),
            payment_method=TuitionPayment.PaymentMethod.MOBILE_MONEY,
            status=TuitionPayment.PaymentStatus.COMPLETED,
            reference='FIN-ANALYTICS-PAYMENT',
            payment_date=date(2025, 9, 15),
            received_by=self.admin,
        )
        StudentBalance.objects.update_or_create(
            student=student,
            academic_year=academic_year,
            defaults={
                'total_due': Decimal('200000.00'),
                'total_paid': Decimal('100000.00'),
            },
        )
        Salary.objects.create(
            employee=employee,
            month=9,
            year=2025,
            base_salary=Decimal('20000.00'),
            bonuses=Decimal('0.00'),
            deductions=Decimal('0.00'),
            net_salary=Decimal('20000.00'),
            status=Salary.PaymentStatus.PAID,
            payment_date=date(2025, 9, 25),
            processed_by=self.admin,
        )
        Expense.objects.create(
            category=Expense.ExpenseCategory.UTILITIES,
            description='Internet',
            amount=Decimal('10000.00'),
            date=date(2025, 9, 20),
            approved_by=self.admin,
            created_by=self.admin,
        )
        self.client.force_authenticate(self.admin)

    def test_dashboard_returns_chart_ready_financial_series(self):
        response = self.client.get('/api/v1/finance/dashboard/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['collection_rate'], 50.0)
        self.assertEqual(len(response.data['monthly_cash_flow']), 12)

        september = next(
            row for row in response.data['monthly_cash_flow']
            if row['month'] == '2025-09'
        )
        self.assertEqual(Decimal(str(september['revenue'])), Decimal('100000.00'))
        self.assertEqual(Decimal(str(september['salaries'])), Decimal('20000.00'))
        self.assertEqual(Decimal(str(september['expenses'])), Decimal('10000.00'))
        self.assertEqual(Decimal(str(september['net'])), Decimal('70000.00'))

        self.assertEqual(response.data['expense_categories'][0]['category'], 'UTILITIES')
        self.assertEqual(response.data['payment_methods'][0]['method'], 'MOBILE_MONEY')
        self.assertEqual(response.data['payment_statuses'][0]['status'], 'COMPLETED')
