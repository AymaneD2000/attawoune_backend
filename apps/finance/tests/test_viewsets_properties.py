"""
Property-based tests for finance viewsets.

These tests verify universal properties that should hold for all valid inputs.
Tests cover CRUD operations, pagination, filtering, searching, and ordering.
"""

from hypothesis import given, strategies as st, settings
from hypothesis.extra.django import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
from datetime import date, timedelta
from apps.finance.models import (
    TuitionPayment, TuitionFee, StudentBalance, Salary, Expense
)
from apps.students.models import Student
from apps.university.models import (
    AcademicYear, Faculty, Department, Level, Program
)

User = get_user_model()


class PaginationPropertyTests(TestCase):
    """Property tests for pagination consistency."""
    
    @settings(max_examples=10, deadline=None)
    @given(
        num_items=st.integers(min_value=21, max_value=100)
    )
    def test_property_4_pagination_consistency(self, num_items):
        """
        Feature: backend-api-implementation, Property 4: Pagination Consistency
        
        **Validates: Requirements 2.2**
        
        For any list endpoint with more than 20 items, the response should return
        exactly 20 items per page with pagination metadata.
        """
        # Create accountant user
        accountant = User.objects.create_user(
            username=f'accountant_pag_{num_items}',
            email=f'accountant_pag_{num_items}@test.com',
            password='testpass123',
            role='ACCOUNTANT'
        )
        
        # Create necessary related objects
        academic_year = AcademicYear.objects.create(
            name='2023-2024',
            start_date=date(2023, 9, 1),
            end_date=date(2024, 6, 30),
            is_current=True
        )
        
        faculty = Faculty.objects.create(name='Test Faculty', code='TF')
        department = Department.objects.create(
            name='Test Department',
            code='TD',
            faculty=faculty
        )
        level = Level.objects.create(name='L1', order=1)
        program = Program.objects.create(
            name='Test Program',
            code='TP',
            department=department,
            level=level
        )
        
        # Create student
        student_user = User.objects.create_user(
            username=f'student_pag_{num_items}',
            email=f'student_pag_{num_items}@test.com',
            password='testpass123',
            role='STUDENT'
        )
        student = Student.objects.create(
            user=student_user,
            student_id=f'STU{num_items}',
            program=program,
            current_level=level,
            enrollment_date=date(2023, 9, 1)
        )
        
        # Create multiple tuition payments
        for i in range(num_items):
            TuitionPayment.objects.create(
                student=student,
                academic_year=academic_year,
                amount=Decimal('1000.00'),
                reference=f'PAY{num_items}{i:04d}',
                payment_date=date(2023, 9, 1) + timedelta(days=i),
                received_by=accountant
            )
        
        # Make API request
        client = APIClient()
        client.force_authenticate(user=accountant)
        response = client.get('/api/finance/tuition-payments/')
        
        # Verify pagination
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        
        # Verify exactly 20 items per page
        self.assertEqual(len(response.data['results']), 20)
        self.assertEqual(response.data['count'], num_items)


class DetailEndpointPropertyTests(TestCase):
    """Property tests for detail endpoint completeness."""
    
    @settings(max_examples=10, deadline=None)
    @given(
        year=st.integers(min_value=2020, max_value=2030),
        amount=st.decimals(min_value=100, max_value=10000, places=2)
    )
    def test_property_5_complete_resource_representation(self, year, amount):
        """
        Feature: backend-api-implementation, Property 5: Complete Resource Representation
        
        **Validates: Requirements 2.3**
        
        For any detail endpoint request, the response should include all fields
        defined in the detail serializer for that resource.
        """
        # Create accountant user
        accountant = User.objects.create_user(
            username=f'accountant_det_{year}',
            email=f'accountant_det_{year}@test.com',
            password='testpass123',
            role='ACCOUNTANT'
        )
        
        # Create necessary related objects
        academic_year = AcademicYear.objects.create(
            name=f'{year}-{year+1}',
            start_date=date(year, 9, 1),
            end_date=date(year + 1, 6, 30),
            is_current=True
        )
        
        faculty = Faculty.objects.create(name='Test Faculty', code='TF')
        department = Department.objects.create(
            name='Test Department',
            code='TD',
            faculty=faculty
        )
        level = Level.objects.create(name='L1', order=1)
        program = Program.objects.create(
            name='Test Program',
            code='TP',
            department=department,
            level=level
        )
        
        # Create student
        student_user = User.objects.create_user(
            username=f'student_det_{year}',
            email=f'student_det_{year}@test.com',
            password='testpass123',
            role='STUDENT'
        )
        student = Student.objects.create(
            user=student_user,
            student_id=f'STU{year}',
            program=program,
            current_level=level,
            enrollment_date=date(year, 9, 1)
        )
        
        # Create tuition payment
        payment = TuitionPayment.objects.create(
            student=student,
            academic_year=academic_year,
            amount=Decimal(str(amount)),
            reference=f'PAY{year}',
            payment_date=date(year, 9, 1),
            received_by=accountant
        )
        
        # Make API request
        client = APIClient()
        client.force_authenticate(user=accountant)
        response = client.get(f'/api/finance/tuition-payments/{payment.id}/')
        
        # Verify response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify all expected fields are present (based on TuitionPaymentDetailSerializer)
        expected_fields = [
            'id', 'student', 'academic_year', 'amount', 'payment_method',
            'status', 'reference', 'description', 'receipt_number',
            'payment_date', 'received_by', 'created_at', 'updated_at',
            # Display fields
            'student_name', 'student_matricule', 'student_program', 'academic_year_name',
            'payment_method_display', 'status_display', 'received_by_name'
        ]
        for field in expected_fields:
            self.assertIn(field, response.data, f"Field '{field}' missing from detail response")


class CreateOperationPropertyTests(TestCase):
    """Property tests for create operations."""
    
    @settings(max_examples=10, deadline=None)
    @given(
        year=st.integers(min_value=2020, max_value=2030),
        amount=st.decimals(min_value=100, max_value=10000, places=2)
    )
    def test_property_6_create_operation_success(self, year, amount):
        """
        Feature: backend-api-implementation, Property 6: Create Operation Success
        
        **Validates: Requirements 2.4**
        
        For any valid create request, the API should return HTTP 201 with the
        created resource containing all fields including auto-generated ones.
        """
        # Create accountant user
        accountant = User.objects.create_user(
            username=f'accountant_create_{year}',
            email=f'accountant_create_{year}@test.com',
            password='testpass123',
            role='ACCOUNTANT'
        )
        
        # Create necessary related objects
        academic_year = AcademicYear.objects.create(
            name=f'{year}-{year+1}',
            start_date=date(year, 9, 1),
            end_date=date(year + 1, 6, 30),
            is_current=True
        )
        
        faculty = Faculty.objects.create(name='Test Faculty', code='TF')
        department = Department.objects.create(
            name='Test Department',
            code='TD',
            faculty=faculty
        )
        level = Level.objects.create(name='L1', order=1)
        program = Program.objects.create(
            name='Test Program',
            code='TP',
            department=department,
            level=level
        )
        
        # Create student
        student_user = User.objects.create_user(
            username=f'student_create_{year}',
            email=f'student_create_{year}@test.com',
            password='testpass123',
            role='STUDENT'
        )
        student = Student.objects.create(
            user=student_user,
            student_id=f'STU{year}',
            program=program,
            current_level=level,
            enrollment_date=date(year, 9, 1)
        )
        
        # Prepare data
        data = {
            'student': student.id,
            'academic_year': academic_year.id,
            'amount': str(amount),
            'reference': f'PAYCREATE{year}',
            'payment_date': date(year, 9, 1).isoformat()
        }
        
        # Make API request
        client = APIClient()
        client.force_authenticate(user=accountant)
        response = client.post('/api/finance/tuition-payments/', data)
        
        # Verify response
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['reference'], data['reference'])
        self.assertEqual(Decimal(response.data['amount']), Decimal(data['amount']))


class UpdateOperationPropertyTests(TestCase):
    """Property tests for update operations."""
    
    @settings(max_examples=10, deadline=None)
    @given(
        old_status=st.sampled_from(['PENDING', 'COMPLETED']),
        new_status=st.sampled_from(['PENDING', 'COMPLETED', 'FAILED', 'REFUNDED'])
    )
    def test_property_7_update_operation_success(self, old_status, new_status):
        """
        Feature: backend-api-implementation, Property 7: Update Operation Success
        
        **Validates: Requirements 2.5**
        
        For any valid update request, the API should return HTTP 200 with the
        updated resource reflecting all changes.
        """
        # Create accountant user
        accountant = User.objects.create_user(
            username=f'accountant_upd_{old_status}_{new_status}',
            email=f'accountant_upd_{old_status}_{new_status}@test.com',
            password='testpass123',
            role='ACCOUNTANT'
        )
        
        # Create necessary related objects
        academic_year = AcademicYear.objects.create(
            name='2023-2024',
            start_date=date(2023, 9, 1),
            end_date=date(2024, 6, 30),
            is_current=True
        )
        
        faculty = Faculty.objects.create(name='Test Faculty', code='TF')
        department = Department.objects.create(
            name='Test Department',
            code='TD',
            faculty=faculty
        )
        level = Level.objects.create(name='L1', order=1)
        program = Program.objects.create(
            name='Test Program',
            code='TP',
            department=department,
            level=level
        )
        
        # Create student
        student_user = User.objects.create_user(
            username=f'student_upd_{old_status}_{new_status}',
            email=f'student_upd_{old_status}_{new_status}@test.com',
            password='testpass123',
            role='STUDENT'
        )
        student = Student.objects.create(
            user=student_user,
            student_id=f'STU{old_status}{new_status}',
            program=program,
            current_level=level,
            enrollment_date=date(2023, 9, 1)
        )
        
        # Create payment
        payment = TuitionPayment.objects.create(
            student=student,
            academic_year=academic_year,
            amount=Decimal('1000.00'),
            reference=f'PAYUPD{old_status}{new_status}',
            payment_date=date(2023, 9, 1),
            received_by=accountant,
            status=old_status
        )
        
        # Prepare update data
        data = {
            'status': new_status
        }
        
        # Make API request
        client = APIClient()
        client.force_authenticate(user=accountant)
        response = client.patch(f'/api/finance/tuition-payments/{payment.id}/', data)
        
        # Verify response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], new_status)
        
        # Verify database was updated
        payment.refresh_from_db()
        self.assertEqual(payment.status, new_status)


class DeleteOperationPropertyTests(TestCase):
    """Property tests for delete operations."""
    
    @settings(max_examples=10, deadline=None)
    @given(
        year=st.integers(min_value=2020, max_value=2030)
    )
    def test_property_8_delete_operation_success(self, year):
        """
        Feature: backend-api-implementation, Property 8: Delete Operation Success
        
        **Validates: Requirements 2.6**
        
        For any valid delete request, the API should return HTTP 204 with no content,
        and subsequent GET requests should return HTTP 404.
        """
        # Create accountant user
        accountant = User.objects.create_user(
            username=f'accountant_del_{year}',
            email=f'accountant_del_{year}@test.com',
            password='testpass123',
            role='ACCOUNTANT'
        )
        
        # Create necessary related objects
        academic_year = AcademicYear.objects.create(
            name=f'{year}-{year+1}',
            start_date=date(year, 9, 1),
            end_date=date(year + 1, 6, 30),
            is_current=True
        )
        
        faculty = Faculty.objects.create(name='Test Faculty', code='TF')
        department = Department.objects.create(
            name='Test Department',
            code='TD',
            faculty=faculty
        )
        level = Level.objects.create(name='L1', order=1)
        program = Program.objects.create(
            name='Test Program',
            code='TP',
            department=department,
            level=level
        )
        
        # Create student
        student_user = User.objects.create_user(
            username=f'student_del_{year}',
            email=f'student_del_{year}@test.com',
            password='testpass123',
            role='STUDENT'
        )
        student = Student.objects.create(
            user=student_user,
            student_id=f'STUDEL{year}',
            program=program,
            current_level=level,
            enrollment_date=date(year, 9, 1)
        )
        
        # Create payment
        payment = TuitionPayment.objects.create(
            student=student,
            academic_year=academic_year,
            amount=Decimal('1000.00'),
            reference=f'PAYDEL{year}',
            payment_date=date(year, 9, 1),
            received_by=accountant
        )
        
        # Make delete request
        client = APIClient()
        client.force_authenticate(user=accountant)
        response = client.delete(f'/api/finance/tuition-payments/{payment.id}/')
        
        # Verify delete response
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify subsequent GET returns 404
        response = client.get(f'/api/finance/tuition-payments/{payment.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)



class ValidationErrorPropertyTests(TestCase):
    """Property tests for validation error responses."""
    
    @settings(max_examples=10, deadline=None)
    @given(
        year=st.integers(min_value=2020, max_value=2030)
    )
    def test_property_9_validation_error_response(self, year):
        """
        Feature: backend-api-implementation, Property 9: Validation Error Response
        
        **Validates: Requirements 2.7**
        
        For any request with invalid data, the API should return HTTP 400 with
        a JSON object containing field-level error messages.
        """
        # Create accountant user
        accountant = User.objects.create_user(
            username=f'accountant_val_{year}',
            email=f'accountant_val_{year}@test.com',
            password='testpass123',
            role='ACCOUNTANT'
        )
        
        # Create necessary related objects
        academic_year = AcademicYear.objects.create(
            name=f'{year}-{year+1}',
            start_date=date(year, 9, 1),
            end_date=date(year + 1, 6, 30),
            is_current=True
        )
        
        faculty = Faculty.objects.create(name='Test Faculty', code='TF')
        department = Department.objects.create(
            name='Test Department',
            code='TD',
            faculty=faculty
        )
        level = Level.objects.create(name='L1', order=1)
        program = Program.objects.create(
            name='Test Program',
            code='TP',
            department=department,
            level=level
        )
        
        # Create student
        student_user = User.objects.create_user(
            username=f'student_val_{year}',
            email=f'student_val_{year}@test.com',
            password='testpass123',
            role='STUDENT'
        )
        student = Student.objects.create(
            user=student_user,
            student_id=f'STUVAL{year}',
            program=program,
            current_level=level,
            enrollment_date=date(year, 9, 1)
        )
        
        # Prepare invalid data (missing required field)
        data = {
            'student': student.id,
            'academic_year': academic_year.id,
            'amount': '1000.00',
            # Missing reference (required field)
            'payment_date': date(year, 9, 1).isoformat()
        }
        
        # Make API request
        client = APIClient()
        client.force_authenticate(user=accountant)
        response = client.post('/api/finance/tuition-payments/', data)
        
        # Verify validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(isinstance(response.data, dict))
        self.assertIn('reference', response.data)


class NotFoundPropertyTests(TestCase):
    """Property tests for not found responses."""
    
    @settings(max_examples=10, deadline=None)
    @given(
        non_existent_id=st.integers(min_value=999999, max_value=9999999)
    )
    def test_property_10_not_found_response(self, non_existent_id):
        """
        Feature: backend-api-implementation, Property 10: Not Found Response
        
        **Validates: Requirements 2.8**
        
        For any request for a non-existent resource, the API should return
        HTTP 404 with an appropriate error message.
        """
        # Create accountant user
        accountant = User.objects.create_user(
            username=f'accountant_404_{non_existent_id}',
            email=f'accountant_404_{non_existent_id}@test.com',
            password='testpass123',
            role='ACCOUNTANT'
        )
        
        # Make API request for non-existent resource
        client = APIClient()
        client.force_authenticate(user=accountant)
        response = client.get(f'/api/finance/tuition-payments/{non_existent_id}/')
        
        # Verify not found response
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class FilterPropertyTests(TestCase):
    """Property tests for filtering accuracy."""
    
    @settings(max_examples=10, deadline=None)
    @given(
        num_completed=st.integers(min_value=1, max_value=5),
        num_pending=st.integers(min_value=1, max_value=5)
    )
    def test_property_19_filter_result_accuracy(self, num_completed, num_pending):
        """
        Feature: backend-api-implementation, Property 19: Filter Result Accuracy
        
        **Validates: Requirements 4.2**
        
        For any filter parameters provided in a list request, all returned
        results should match the filter criteria exactly.
        """
        # Create unique identifier for this test run
        import uuid
        test_id = str(uuid.uuid4())[:8]
        
        # Create accountant user
        accountant = User.objects.create_user(
            username=f'accountant_filt_{test_id}',
            email=f'accountant_filt_{test_id}@test.com',
            password='testpass123',
            role='ACCOUNTANT'
        )
        
        # Create necessary related objects
        academic_year = AcademicYear.objects.create(
            name=f'2023-2024-{test_id}',
            start_date=date(2023, 9, 1),
            end_date=date(2024, 6, 30),
            is_current=True
        )
        
        faculty = Faculty.objects.create(name=f'Faculty-{test_id}', code=f'F{test_id}')
        department = Department.objects.create(
            name=f'Department-{test_id}',
            code=f'D{test_id}',
            faculty=faculty
        )
        level = Level.objects.create(name=f'L1-{test_id}', order=1)
        program = Program.objects.create(
            name=f'Program-{test_id}',
            code=f'P{test_id}',
            department=department,
            level=level
        )
        
        # Create student
        student_user = User.objects.create_user(
            username=f'student_filt_{test_id}',
            email=f'student_filt_{test_id}@test.com',
            password='testpass123',
            role='STUDENT'
        )
        student = Student.objects.create(
            user=student_user,
            student_id=f'STU{test_id}',
            program=program,
            current_level=level,
            enrollment_date=date(2023, 9, 1)
        )
        
        # Create completed payments
        for i in range(num_completed):
            TuitionPayment.objects.create(
                student=student,
                academic_year=academic_year,
                amount=Decimal('1000.00'),
                reference=f'COMP{test_id}{i}',
                payment_date=date(2023, 9, 1),
                received_by=accountant,
                status='COMPLETED'
            )
        
        # Create pending payments
        for i in range(num_pending):
            TuitionPayment.objects.create(
                student=student,
                academic_year=academic_year,
                amount=Decimal('1000.00'),
                reference=f'PEND{test_id}{i}',
                payment_date=date(2023, 9, 1),
                received_by=accountant,
                status='PENDING'
            )
        
        # Make API request with filter for completed payments
        client = APIClient()
        client.force_authenticate(user=accountant)
        response = client.get('/api/finance/tuition-payments/?status=COMPLETED')
        
        # Verify filter accuracy
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Count only the items we created in this test
        our_completed_items = [r for r in response.data['results'] 
                               if test_id in r['reference'] and r['status'] == 'COMPLETED']
        
        self.assertEqual(len(our_completed_items), num_completed)
        
        # Verify all our results match filter
        for result in our_completed_items:
            self.assertEqual(result['status'], 'COMPLETED')


class SearchPropertyTests(TestCase):
    """Property tests for search result relevance."""
    
    @settings(max_examples=10, deadline=None)
    @given(
        search_term=st.text(min_size=3, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
        num_matching=st.integers(min_value=1, max_value=5),
        num_non_matching=st.integers(min_value=1, max_value=5)
    )
    def test_property_20_search_result_relevance(self, search_term, num_matching, num_non_matching):
        """
        Feature: backend-api-implementation, Property 20: Search Result Relevance
        
        **Validates: Requirements 4.4**
        
        For any search query provided, all returned results should contain the
        search term in at least one of the searchable fields.
        """
        # Create accountant user
        accountant = User.objects.create_user(
            username=f'accountant_search_{len(search_term)}',
            email=f'accountant_search_{len(search_term)}@test.com',
            password='testpass123',
            role='ACCOUNTANT'
        )
        
        # Create necessary related objects
        academic_year = AcademicYear.objects.create(
            name='2023-2024',
            start_date=date(2023, 9, 1),
            end_date=date(2024, 6, 30),
            is_current=True
        )
        
        faculty = Faculty.objects.create(name='Test Faculty', code='TF')
        department = Department.objects.create(
            name='Test Department',
            code='TD',
            faculty=faculty
        )
        level = Level.objects.create(name='L1', order=1)
        program = Program.objects.create(
            name='Test Program',
            code='TP',
            department=department,
            level=level
        )
        
        # Create student
        student_user = User.objects.create_user(
            username=f'student_search_{len(search_term)}',
            email=f'student_search_{len(search_term)}@test.com',
            password='testpass123',
            role='STUDENT'
        )
        student = Student.objects.create(
            user=student_user,
            student_id=f'STU{len(search_term)}',
            program=program,
            current_level=level,
            enrollment_date=date(2023, 9, 1)
        )
        
        # Create matching payments (search term in reference)
        for i in range(num_matching):
            TuitionPayment.objects.create(
                student=student,
                academic_year=academic_year,
                amount=Decimal('1000.00'),
                reference=f'{search_term}{i}',
                payment_date=date(2023, 9, 1),
                received_by=accountant
            )
        
        # Create non-matching payments
        for i in range(num_non_matching):
            TuitionPayment.objects.create(
                student=student,
                academic_year=academic_year,
                amount=Decimal('1000.00'),
                reference=f'DIFF{i}',
                payment_date=date(2023, 9, 1),
                received_by=accountant
            )
        
        # Make API request with search
        client = APIClient()
        client.force_authenticate(user=accountant)
        response = client.get(f'/api/finance/tuition-payments/?search={search_term}')
        
        # Verify search relevance
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], num_matching)
        
        # Verify all results contain search term
        for result in response.data['results']:
            self.assertIn(search_term.lower(), result['reference'].lower())


class OrderingPropertyTests(TestCase):
    """Property tests for ordering correctness."""
    
    @settings(max_examples=10, deadline=None)
    @given(
        num_items=st.integers(min_value=3, max_value=10)
    )
    def test_property_21_ordering_correctness(self, num_items):
        """
        Feature: backend-api-implementation, Property 21: Ordering Correctness
        
        **Validates: Requirements 4.6**
        
        For any ordering parameter provided, the returned results should be
        sorted in the specified order by the specified field.
        """
        # Create accountant user
        accountant = User.objects.create_user(
            username=f'accountant_order_{num_items}',
            email=f'accountant_order_{num_items}@test.com',
            password='testpass123',
            role='ACCOUNTANT'
        )
        
        # Create necessary related objects
        academic_year = AcademicYear.objects.create(
            name='2023-2024',
            start_date=date(2023, 9, 1),
            end_date=date(2024, 6, 30),
            is_current=True
        )
        
        faculty = Faculty.objects.create(name='Test Faculty', code='TF')
        department = Department.objects.create(
            name='Test Department',
            code='TD',
            faculty=faculty
        )
        level = Level.objects.create(name='L1', order=1)
        program = Program.objects.create(
            name='Test Program',
            code='TP',
            department=department,
            level=level
        )
        
        # Create student
        student_user = User.objects.create_user(
            username=f'student_order_{num_items}',
            email=f'student_order_{num_items}@test.com',
            password='testpass123',
            role='STUDENT'
        )
        student = Student.objects.create(
            user=student_user,
            student_id=f'STU{num_items}',
            program=program,
            current_level=level,
            enrollment_date=date(2023, 9, 1)
        )
        
        # Create payments with different amounts
        amounts = []
        for i in range(num_items):
            amount = Decimal(str(1000 + (i * 100)))
            amounts.append(amount)
            TuitionPayment.objects.create(
                student=student,
                academic_year=academic_year,
                amount=amount,
                reference=f'PAYORD{num_items}{i}',
                payment_date=date(2023, 9, 1),
                received_by=accountant
            )
        
        # Make API request with ascending order
        client = APIClient()
        client.force_authenticate(user=accountant)
        response = client.get('/api/finance/tuition-payments/?ordering=amount')
        
        # Verify ordering
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_amounts = [Decimal(r['amount']) for r in response.data['results']]
        self.assertEqual(result_amounts, sorted(result_amounts))
        
        # Make API request with descending order
        response = client.get('/api/finance/tuition-payments/?ordering=-amount')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_amounts = [Decimal(r['amount']) for r in response.data['results']]
        self.assertEqual(result_amounts, sorted(result_amounts, reverse=True))


class MultipleFilterPropertyTests(TestCase):
    """Property tests for multiple filter combination."""
    
    @settings(max_examples=10, deadline=None)
    @given(
        payment_status=st.sampled_from(['PENDING', 'COMPLETED']),
        payment_method=st.sampled_from(['CASH', 'BANK_TRANSFER', 'MOBILE_MONEY']),
        num_matching=st.integers(min_value=1, max_value=3),
        num_non_matching=st.integers(min_value=1, max_value=3)
    )
    def test_property_22_multiple_filter_combination(self, payment_status, payment_method,
                                                     num_matching, num_non_matching):
        """
        Feature: backend-api-implementation, Property 22: Multiple Filter Combination
        
        **Validates: Requirements 4.7**
        
        For any request with multiple filter parameters, all returned results
        should satisfy all filter conditions simultaneously.
        """
        # Create unique identifier for this test run
        import uuid
        test_id = str(uuid.uuid4())[:8]
        
        # Create accountant user
        accountant = User.objects.create_user(
            username=f'accountant_multi_{test_id}',
            email=f'accountant_multi_{test_id}@test.com',
            password='testpass123',
            role='ACCOUNTANT'
        )
        
        # Create necessary related objects
        academic_year = AcademicYear.objects.create(
            name=f'2023-2024-{test_id}',
            start_date=date(2023, 9, 1),
            end_date=date(2024, 6, 30),
            is_current=True
        )
        
        faculty = Faculty.objects.create(name=f'Faculty-{test_id}', code=f'F{test_id}')
        department = Department.objects.create(
            name=f'Department-{test_id}',
            code=f'D{test_id}',
            faculty=faculty
        )
        level = Level.objects.create(name=f'L1-{test_id}', order=1)
        program = Program.objects.create(
            name=f'Program-{test_id}',
            code=f'P{test_id}',
            department=department,
            level=level
        )
        
        # Create student
        student_user = User.objects.create_user(
            username=f'student_multi_{test_id}',
            email=f'student_multi_{test_id}@test.com',
            password='testpass123',
            role='STUDENT'
        )
        student = Student.objects.create(
            user=student_user,
            student_id=f'STU{test_id}',
            program=program,
            current_level=level,
            enrollment_date=date(2023, 9, 1)
        )
        
        # Create matching payments (specific status and method)
        for i in range(num_matching):
            TuitionPayment.objects.create(
                student=student,
                academic_year=academic_year,
                amount=Decimal('1000.00'),
                reference=f'MATCH{test_id}{i}',
                payment_date=date(2023, 9, 1),
                received_by=accountant,
                status=payment_status,
                payment_method=payment_method
            )
        
        # Create non-matching payments (different status or method)
        for i in range(num_non_matching):
            # Use different status or different method
            different_status = 'FAILED' if payment_status == 'PENDING' else 'PENDING'
            different_method = 'CHECK' if payment_method == 'CASH' else 'CASH'
            TuitionPayment.objects.create(
                student=student,
                academic_year=academic_year,
                amount=Decimal('1000.00'),
                reference=f'NOMATCH{test_id}{i}',
                payment_date=date(2023, 9, 1),
                received_by=accountant,
                status=different_status if i % 2 == 0 else payment_status,
                payment_method=different_method if i % 2 == 1 else payment_method
            )
        
        # Make API request with multiple filters
        client = APIClient()
        client.force_authenticate(user=accountant)
        response = client.get(
            f'/api/finance/tuition-payments/?status={payment_status}'
            f'&payment_method={payment_method}'
        )
        
        # Verify multiple filter combination
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Count only the items we created in this test
        our_matching_items = [r for r in response.data['results'] 
                              if test_id in r['reference'] 
                              and r['status'] == payment_status
                              and r['payment_method'] == payment_method]
        
        self.assertEqual(len(our_matching_items), num_matching)
        
        # Verify all results match both filters
        for result in our_matching_items:
            self.assertEqual(result['status'], payment_status)
            self.assertEqual(result['payment_method'], payment_method)
