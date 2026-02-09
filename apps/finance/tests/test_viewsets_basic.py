"""
Basic integration tests for finance viewsets.

This module tests that all finance viewsets are properly configured and accessible.
"""

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from apps.finance.models import TuitionPayment, TuitionFee, StudentBalance, Salary, Expense
from apps.students.models import Student
from apps.university.models import AcademicYear, Program, Department, Faculty, Level
from decimal import Decimal
from datetime import date

User = get_user_model()


class FinanceViewSetBasicTests(TestCase):
    """Basic tests for finance viewsets."""
    
    def setUp(self):
        """Set up test data."""
        # Create users
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            role='ADMIN'
        )
        
        self.accountant_user = User.objects.create_user(
            username='accountant',
            email='accountant@test.com',
            password='testpass123',
            first_name='Accountant',
            last_name='User',
            role='ACCOUNTANT'
        )
        
        self.student_user = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='testpass123',
            first_name='Student',
            last_name='User',
            role='STUDENT'
        )
        
        # Create academic structure
        self.academic_year = AcademicYear.objects.create(
            name='2023-2024',
            start_date=date(2023, 9, 1),
            end_date=date(2024, 6, 30),
            is_current=True
        )
        
        self.level = Level.objects.create(
            name='L1',
            order=1
        )
        
        self.faculty = Faculty.objects.create(
            name='Faculty of Science',
            code='SCI'
        )
        
        self.department = Department.objects.create(
            name='Computer Science',
            code='CS',
            faculty=self.faculty
        )
        
        self.program = Program.objects.create(
            name='Computer Science',
            code='CS-L1',
            department=self.department,
            level=self.level
        )
        
        # Create student
        self.student = Student.objects.create(
            user=self.student_user,
            student_id='STU001',
            program=self.program,
            current_level=self.level,
            enrollment_date=date(2023, 9, 1)
        )
        
        # Set up API client
        self.client = APIClient()
    
    def test_tuition_payment_viewset_requires_authentication(self):
        """Test that tuition payment endpoints require authentication."""
        response = self.client.get('/api/finance/tuition-payments/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_tuition_payment_viewset_requires_accountant_or_admin(self):
        """Test that tuition payment endpoints require accountant or admin role."""
        self.client.force_authenticate(user=self.student_user)
        response = self.client.get('/api/finance/tuition-payments/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_tuition_payment_list_as_accountant(self):
        """Test that accountants can list tuition payments."""
        self.client.force_authenticate(user=self.accountant_user)
        response = self.client.get('/api/finance/tuition-payments/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_tuition_payment_list_as_admin(self):
        """Test that admins can list tuition payments."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/finance/tuition-payments/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_tuition_fee_viewset_accessible_by_accountant(self):
        """Test that tuition fee endpoints are accessible by accountants."""
        self.client.force_authenticate(user=self.accountant_user)
        response = self.client.get('/api/finance/tuition-fees/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_student_balance_viewset_accessible_by_accountant(self):
        """Test that student balance endpoints are accessible by accountants."""
        self.client.force_authenticate(user=self.accountant_user)
        response = self.client.get('/api/finance/student-balances/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_salary_viewset_accessible_by_accountant(self):
        """Test that salary endpoints are accessible by accountants."""
        self.client.force_authenticate(user=self.accountant_user)
        response = self.client.get('/api/finance/salaries/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_expense_viewset_accessible_by_accountant(self):
        """Test that expense endpoints are accessible by accountants."""
        self.client.force_authenticate(user=self.accountant_user)
        response = self.client.get('/api/finance/expenses/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_tuition_payment_filtering_by_student(self):
        """Test filtering tuition payments by student."""
        # Create a payment
        payment = TuitionPayment.objects.create(
            student=self.student,
            academic_year=self.academic_year,
            amount=Decimal('1000.00'),
            reference='PAY001',
            payment_date=date.today(),
            received_by=self.accountant_user
        )
        
        self.client.force_authenticate(user=self.accountant_user)
        response = self.client.get(f'/api/finance/tuition-payments/?student={self.student.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_tuition_payment_search_by_reference(self):
        """Test searching tuition payments by reference."""
        # Create a payment
        payment = TuitionPayment.objects.create(
            student=self.student,
            academic_year=self.academic_year,
            amount=Decimal('1000.00'),
            reference='PAY001',
            payment_date=date.today(),
            received_by=self.accountant_user
        )
        
        self.client.force_authenticate(user=self.accountant_user)
        response = self.client.get('/api/finance/tuition-payments/?search=PAY001')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_tuition_payment_ordering(self):
        """Test ordering tuition payments."""
        self.client.force_authenticate(user=self.accountant_user)
        response = self.client.get('/api/finance/tuition-payments/?ordering=-payment_date')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_salary_filtering_by_year_and_month(self):
        """Test filtering salaries by year and month."""
        self.client.force_authenticate(user=self.accountant_user)
        response = self.client.get('/api/finance/salaries/?year=2024&month=1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_expense_filtering_by_category(self):
        """Test filtering expenses by category."""
        self.client.force_authenticate(user=self.accountant_user)
        response = self.client.get('/api/finance/expenses/?category=SALARIES')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
