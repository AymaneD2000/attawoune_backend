"""
Tests for finance viewset custom actions.

This module tests:
- outstanding balances action
- pay salary action
- pending salaries action
- expense summary action
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from apps.university.models import AcademicYear, Semester, Faculty, Department, Program, Level
from apps.students.models import Student
from apps.teachers.models import Teacher
from apps.finance.models import StudentBalance, TuitionPayment, Salary, Expense
from datetime import date
from decimal import Decimal

User = get_user_model()


class StudentBalanceCustomActionsTestCase(TestCase):
    """Test cases for StudentBalanceViewSet custom actions."""
    
    def setUp(self):
        """Set up test data."""
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            role='ADMIN'
        )
        
        self.student_user1 = User.objects.create_user(
            username='student1',
            email='student1@test.com',
            password='testpass123',
            first_name='Student1',
            last_name='User',
            role='STUDENT'
        )
        
        self.student_user2 = User.objects.create_user(
            username='student2',
            email='student2@test.com',
            password='testpass123',
            first_name='Student2',
            last_name='User',
            role='STUDENT'
        )
        
        # Create academic structure
        self.academic_year = AcademicYear.objects.create(
            name='2025-2026',
            start_date=date(2025, 9, 1),
            end_date=date(2026, 7, 31),
            is_current=True
        )
        
        self.faculty = Faculty.objects.create(name='Sciences', code='SCI')
        self.department = Department.objects.create(
            name='Informatique', code='INFO', faculty=self.faculty
        )
        self.level = Level.objects.create(name='L1', order=1)
        self.program = Program.objects.create(
            name='Licence Informatique',
            code='LINF',
            department=self.department,
            level=self.level,
            duration_years=3
        )
        
        # Create students
        self.student1 = Student.objects.create(
            user=self.student_user1,
            student_id='ETU2025001',
            program=self.program,
            current_level=self.level,
            enrollment_date=date(2025, 9, 1),
            status='ACTIVE'
        )
        
        self.student2 = Student.objects.create(
            user=self.student_user2,
            student_id='ETU2025002',
            program=self.program,
            current_level=self.level,
            enrollment_date=date(2025, 9, 1),
            status='ACTIVE'
        )
        
        # Create student balances - one with outstanding, one fully paid
        self.balance1 = StudentBalance.objects.create(
            student=self.student1,
            academic_year=self.academic_year,
            total_tuition=Decimal('500000'),
            total_paid=Decimal('250000'),
            balance=Decimal('250000')  # Outstanding balance
        )
        
        self.balance2 = StudentBalance.objects.create(
            student=self.student2,
            academic_year=self.academic_year,
            total_tuition=Decimal('500000'),
            total_paid=Decimal('500000'),
            balance=Decimal('0')  # Fully paid
        )
        
        self.client = APIClient()
    
    def test_outstanding_balances_action(self):
        """Test the outstanding custom action."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/v1/finance/student-balances/outstanding/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('students_with_outstanding', response.data)
        # Only student1 has outstanding balance
        self.assertEqual(response.data['students_with_outstanding'], 1)
    
    def test_list_student_balances(self):
        """Test listing student balances."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/v1/finance/student-balances/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)


class SalaryCustomActionsTestCase(TestCase):
    """Test cases for SalaryViewSet custom actions."""
    
    def setUp(self):
        """Set up test data."""
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            role='ADMIN'
        )
        
        self.teacher_user = User.objects.create_user(
            username='teacher',
            email='teacher@test.com',
            password='testpass123',
            first_name='Teacher',
            last_name='User',
            role='TEACHER'
        )
        
        self.faculty = Faculty.objects.create(name='Sciences', code='SCI')
        self.department = Department.objects.create(
            name='Informatique', code='INFO', faculty=self.faculty
        )
        
        self.teacher = Teacher.objects.create(
            user=self.teacher_user,
            employee_id='EMP001',
            department=self.department,
            rank='LECTURER',
            contract_type='PERMANENT',
            hire_date=date(2020, 1, 1)
        )
        
        # Create salaries
        self.salary_pending = Salary.objects.create(
            teacher=self.teacher,
            month=1,
            year=2026,
            base_salary=Decimal('350000'),
            bonus=Decimal('50000'),
            deductions=Decimal('25000'),
            net_salary=Decimal('375000'),
            status='PENDING'
        )
        
        self.salary_paid = Salary.objects.create(
            teacher=self.teacher,
            month=12,
            year=2025,
            base_salary=Decimal('350000'),
            bonus=Decimal('50000'),
            deductions=Decimal('25000'),
            net_salary=Decimal('375000'),
            status='PAID',
            payment_date=date(2025, 12, 25)
        )
        
        self.client = APIClient()
    
    def test_pending_salaries_action(self):
        """Test the pending custom action."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/v1/finance/salaries/pending/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_pending_amount', response.data)
        self.assertEqual(response.data['pending_count'], 1)
    
    def test_pay_salary_action(self):
        """Test the pay custom action."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(f'/api/v1/finance/salaries/{self.salary_pending.id}/pay/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Refresh from database
        self.salary_pending.refresh_from_db()
        self.assertEqual(self.salary_pending.status, 'PAID')
        self.assertIsNotNone(self.salary_pending.payment_date)
    
    def test_list_salaries(self):
        """Test listing salaries."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/v1/finance/salaries/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)


class ExpenseCustomActionsTestCase(TestCase):
    """Test cases for ExpenseViewSet custom actions."""
    
    def setUp(self):
        """Set up test data."""
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            role='ADMIN'
        )
        
        # Create expenses
        self.expense1 = Expense.objects.create(
            category='UTILITIES',
            description='Facture électricité',
            amount=Decimal('150000'),
            expense_date=date(2026, 1, 15),
            approved=True,
            approved_by=self.admin_user
        )
        
        self.expense2 = Expense.objects.create(
            category='UTILITIES',
            description='Facture eau',
            amount=Decimal('50000'),
            expense_date=date(2026, 1, 20),
            approved=True,
            approved_by=self.admin_user
        )
        
        self.expense3 = Expense.objects.create(
            category='SUPPLIES',
            description='Fournitures bureau',
            amount=Decimal('75000'),
            expense_date=date(2026, 1, 10),
            approved=True,
            approved_by=self.admin_user
        )
        
        self.client = APIClient()
    
    def test_expense_summary_action(self):
        """Test the summary custom action."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/v1/finance/expenses/summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_expenses', response.data)
        self.assertIn('by_category', response.data)
        # Total should be 275000
        self.assertEqual(float(response.data['total_expenses']), 275000.0)
    
    def test_list_expenses(self):
        """Test listing expenses."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/v1/finance/expenses/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)


class TuitionPaymentTestCase(TestCase):
    """Test cases for TuitionPaymentViewSet."""
    
    def setUp(self):
        """Set up test data."""
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            role='ADMIN'
        )
        
        self.student_user = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='testpass123',
            first_name='Student',
            last_name='User',
            role='STUDENT'
        )
        
        self.academic_year = AcademicYear.objects.create(
            name='2025-2026',
            start_date=date(2025, 9, 1),
            end_date=date(2026, 7, 31),
            is_current=True
        )
        
        self.faculty = Faculty.objects.create(name='Sciences', code='SCI')
        self.department = Department.objects.create(
            name='Informatique', code='INFO', faculty=self.faculty
        )
        self.level = Level.objects.create(name='L1', order=1)
        self.program = Program.objects.create(
            name='Licence Informatique',
            code='LINF',
            department=self.department,
            level=self.level,
            duration_years=3
        )
        
        self.student = Student.objects.create(
            user=self.student_user,
            student_id='ETU2025001',
            program=self.program,
            current_level=self.level,
            enrollment_date=date(2025, 9, 1),
            status='ACTIVE'
        )
        
        self.client = APIClient()
    
    def test_create_payment_generates_reference(self):
        """Test that creating a payment auto-generates a reference number."""
        self.client.force_authenticate(user=self.admin_user)
        data = {
            'student': self.student.id,
            'academic_year': self.academic_year.id,
            'amount': '250000',
            'payment_method': 'CASH',
            'payment_date': date.today().isoformat(),
            'description': 'First tuition payment'
        }
        response = self.client.post('/api/v1/finance/tuition-payments/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Reference should be auto-generated
        self.assertIn('reference', response.data)
        self.assertIsNotNone(response.data['reference'])
