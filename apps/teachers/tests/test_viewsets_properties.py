"""
Property-based tests for teachers viewsets.

These tests verify universal properties that should hold for all valid inputs.
Tests cover CRUD operations, pagination, filtering, searching, and ordering.
"""

from hypothesis import given, strategies as st, settings
from hypothesis.extra.django import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from datetime import date, timedelta
from decimal import Decimal
from apps.teachers.models import Teacher, TeacherCourse, TeacherContract
from apps.university.models import (
    AcademicYear, Semester, Faculty, Department, Level, Program
)
from apps.academics.models import Course

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
        # Create admin user
        admin = User.objects.create_user(
            username=f'admin_pag_{num_items}',
            email=f'admin_pag_{num_items}@test.com',
            password='testpass123',
            role='ADMIN'
        )
        
        # Create necessary related objects
        faculty = Faculty.objects.create(name='Test Faculty', code='TF')
        department = Department.objects.create(
            name='Test Department',
            code='TD',
            faculty=faculty
        )
        
        # Create multiple teachers
        for i in range(num_items):
            user = User.objects.create_user(
                username=f'teacher_{num_items}_{i}',
                email=f'teacher_{num_items}_{i}@test.com',
                password='testpass123',
                role='TEACHER'
            )
            Teacher.objects.create(
                user=user,
                employee_id=f'TEACH{num_items}{i:04d}',
                department=department,
                rank='ASSISTANT',
                contract_type='PERMANENT',
                hire_date=date(2023, 9, 1)
            )
        
        # Make API request
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get('/api/teachers/teachers/')
        
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
        teacher_name=st.text(min_size=3, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll')))
    )
    def test_property_5_complete_resource_representation(self, year, teacher_name):
        """
        Feature: backend-api-implementation, Property 5: Complete Resource Representation
        
        **Validates: Requirements 2.3**
        
        For any detail endpoint request, the response should include all fields
        defined in the detail serializer for that resource.
        """
        # Create admin user
        admin = User.objects.create_user(
            username=f'admin_det_{year}',
            email=f'admin_det_{year}@test.com',
            password='testpass123',
            role='ADMIN'
        )
        
        # Create necessary related objects
        faculty = Faculty.objects.create(name='Test Faculty', code='TF')
        department = Department.objects.create(
            name='Test Department',
            code='TD',
            faculty=faculty
        )
        
        # Create teacher
        user = User.objects.create_user(
            username=f'teacher_det_{year}',
            email=f'teacher_det_{year}@test.com',
            password='testpass123',
            role='TEACHER',
            first_name=teacher_name[:100],
            last_name='Test'
        )
        teacher = Teacher.objects.create(
            user=user,
            employee_id=f'TEACH{year}',
            department=department,
            rank='ASSISTANT',
            contract_type='PERMANENT',
            hire_date=date(year, 9, 1)
        )
        
        # Make API request
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get(f'/api/teachers/teachers/{teacher.id}/')
        
        # Verify response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify all expected fields are present (based on TeacherDetailSerializer)
        expected_fields = [
            'id', 'user', 'employee_id', 'department', 'rank', 'contract_type',
            'hire_date', 'specialization', 'office_location', 'is_active',
            'created_at', 'updated_at',
            # Computed/display fields
            'user_name', 'user_email', 'user_phone', 'department_name',
            'department_code', 'faculty_name', 'rank_display',
            'contract_type_display', 'courses_count', 'active_contracts_count'
        ]
        for field in expected_fields:
            self.assertIn(field, response.data, f"Field '{field}' missing from detail response")



class CreateOperationPropertyTests(TestCase):
    """Property tests for create operations."""
    
    @settings(max_examples=10, deadline=None)
    @given(
        year=st.integers(min_value=2020, max_value=2030),
        teacher_num=st.integers(min_value=1, max_value=9999)
    )
    def test_property_6_create_operation_success(self, year, teacher_num):
        """
        Feature: backend-api-implementation, Property 6: Create Operation Success
        
        **Validates: Requirements 2.4**
        
        For any valid create request, the API should return HTTP 201 with the
        created resource containing all fields including auto-generated ones.
        """
        # Create admin user
        admin = User.objects.create_user(
            username=f'admin_create_{year}_{teacher_num}',
            email=f'admin_create_{year}_{teacher_num}@test.com',
            password='testpass123',
            role='ADMIN'
        )
        
        # Create necessary related objects
        faculty = Faculty.objects.create(name='Test Faculty', code='TF')
        department = Department.objects.create(
            name='Test Department',
            code='TD',
            faculty=faculty
        )
        
        # Create user for teacher
        user = User.objects.create_user(
            username=f'teacher_create_{year}_{teacher_num}',
            email=f'teacher_create_{year}_{teacher_num}@test.com',
            password='testpass123',
            role='TEACHER'
        )
        
        # Prepare data
        data = {
            'user': user.id,
            'employee_id': f'TEACH{year}{teacher_num:04d}',
            'department': department.id,
            'rank': 'ASSISTANT',
            'contract_type': 'PERMANENT',
            'hire_date': date(year, 9, 1).isoformat()
        }
        
        # Make API request
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.post('/api/teachers/teachers/', data)
        
        # Verify response
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['employee_id'], data['employee_id'])
        self.assertEqual(response.data['user'], data['user'])
        self.assertEqual(response.data['department'], data['department'])


class UpdateOperationPropertyTests(TestCase):
    """Property tests for update operations."""
    
    @settings(max_examples=10, deadline=None)
    @given(
        old_rank=st.sampled_from(['ASSISTANT', 'LECTURER']),
        new_rank=st.sampled_from(['ASSISTANT', 'LECTURER', 'SENIOR_LECTURER', 'ASSOCIATE_PROFESSOR', 'PROFESSOR'])
    )
    def test_property_7_update_operation_success(self, old_rank, new_rank):
        """
        Feature: backend-api-implementation, Property 7: Update Operation Success
        
        **Validates: Requirements 2.5**
        
        For any valid update request, the API should return HTTP 200 with the
        updated resource reflecting all changes.
        """
        # Create admin user
        admin = User.objects.create_user(
            username=f'admin_upd_{old_rank}_{new_rank}',
            email=f'admin_upd_{old_rank}_{new_rank}@test.com',
            password='testpass123',
            role='ADMIN'
        )
        
        # Create necessary related objects
        faculty = Faculty.objects.create(name='Test Faculty', code='TF')
        department = Department.objects.create(
            name='Test Department',
            code='TD',
            faculty=faculty
        )
        
        # Create teacher
        user = User.objects.create_user(
            username=f'teacher_upd_{old_rank}_{new_rank}',
            email=f'teacher_upd_{old_rank}_{new_rank}@test.com',
            password='testpass123',
            role='TEACHER'
        )
        teacher = Teacher.objects.create(
            user=user,
            employee_id=f'TEACH{old_rank}{new_rank}',
            department=department,
            rank=old_rank,
            contract_type='PERMANENT',
            hire_date=date(2023, 9, 1)
        )
        
        # Prepare update data
        data = {
            'rank': new_rank
        }
        
        # Make API request
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.patch(f'/api/teachers/teachers/{teacher.id}/', data)
        
        # Verify response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['rank'], new_rank)
        
        # Verify database was updated
        teacher.refresh_from_db()
        self.assertEqual(teacher.rank, new_rank)



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
        # Create admin user
        admin = User.objects.create_user(
            username=f'admin_del_{year}',
            email=f'admin_del_{year}@test.com',
            password='testpass123',
            role='ADMIN'
        )
        
        # Create necessary related objects
        faculty = Faculty.objects.create(name='Test Faculty', code='TF')
        department = Department.objects.create(
            name='Test Department',
            code='TD',
            faculty=faculty
        )
        
        # Create teacher
        user = User.objects.create_user(
            username=f'teacher_del_{year}',
            email=f'teacher_del_{year}@test.com',
            password='testpass123',
            role='TEACHER'
        )
        teacher = Teacher.objects.create(
            user=user,
            employee_id=f'TEACHDEL{year}',
            department=department,
            rank='ASSISTANT',
            contract_type='PERMANENT',
            hire_date=date(year, 9, 1)
        )
        
        # Make delete request
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.delete(f'/api/teachers/teachers/{teacher.id}/')
        
        # Verify delete response
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify subsequent GET returns 404
        response = client.get(f'/api/teachers/teachers/{teacher.id}/')
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
        # Create admin user
        admin = User.objects.create_user(
            username=f'admin_val_{year}',
            email=f'admin_val_{year}@test.com',
            password='testpass123',
            role='ADMIN'
        )
        
        # Create necessary related objects
        faculty = Faculty.objects.create(name='Test Faculty', code='TF')
        department = Department.objects.create(
            name='Test Department',
            code='TD',
            faculty=faculty
        )
        
        # Create user for teacher
        user = User.objects.create_user(
            username=f'teacher_val_{year}',
            email=f'teacher_val_{year}@test.com',
            password='testpass123',
            role='TEACHER'
        )
        
        # Prepare invalid data (missing required field)
        data = {
            'user': user.id,
            # Missing employee_id (required field)
            'department': department.id,
            'rank': 'ASSISTANT',
            'contract_type': 'PERMANENT',
            'hire_date': date(year, 9, 1).isoformat()
        }
        
        # Make API request
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.post('/api/teachers/teachers/', data)
        
        # Verify validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(isinstance(response.data, dict))
        self.assertIn('employee_id', response.data)


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
        # Create admin user
        admin = User.objects.create_user(
            username=f'admin_404_{non_existent_id}',
            email=f'admin_404_{non_existent_id}@test.com',
            password='testpass123',
            role='ADMIN'
        )
        
        # Make API request for non-existent resource
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get(f'/api/teachers/teachers/{non_existent_id}/')
        
        # Verify not found response
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)



class FilterPropertyTests(TestCase):
    """Property tests for filtering accuracy."""
    
    @settings(max_examples=10, deadline=None)
    @given(
        num_active=st.integers(min_value=1, max_value=5),
        num_inactive=st.integers(min_value=1, max_value=5)
    )
    def test_property_19_filter_result_accuracy(self, num_active, num_inactive):
        """
        Feature: backend-api-implementation, Property 19: Filter Result Accuracy
        
        **Validates: Requirements 4.2**
        
        For any filter parameters provided in a list request, all returned
        results should match the filter criteria exactly.
        """
        # Create unique identifier for this test run
        import uuid
        test_id = str(uuid.uuid4())[:8]
        
        # Create admin user
        admin = User.objects.create_user(
            username=f'admin_filt_{test_id}',
            email=f'admin_filt_{test_id}@test.com',
            password='testpass123',
            role='ADMIN'
        )
        
        # Create necessary related objects
        faculty = Faculty.objects.create(name=f'Faculty-{test_id}', code=f'F{test_id}')
        department = Department.objects.create(
            name=f'Department-{test_id}',
            code=f'D{test_id}',
            faculty=faculty
        )
        
        # Create active teachers
        for i in range(num_active):
            user = User.objects.create_user(
                username=f'active_{test_id}_{i}',
                email=f'active_{test_id}_{i}@test.com',
                password='testpass123',
                role='TEACHER'
            )
            Teacher.objects.create(
                user=user,
                employee_id=f'ACTIVE{test_id}{i}',
                department=department,
                rank='ASSISTANT',
                contract_type='PERMANENT',
                hire_date=date(2023, 9, 1),
                is_active=True
            )
        
        # Create inactive teachers
        for i in range(num_inactive):
            user = User.objects.create_user(
                username=f'inactive_{test_id}_{i}',
                email=f'inactive_{test_id}_{i}@test.com',
                password='testpass123',
                role='TEACHER'
            )
            Teacher.objects.create(
                user=user,
                employee_id=f'INACT{test_id}{i}',
                department=department,
                rank='ASSISTANT',
                contract_type='PERMANENT',
                hire_date=date(2023, 9, 1),
                is_active=False
            )
        
        # Make API request with filter for active teachers
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get('/api/teachers/teachers/?is_active=true')
        
        # Verify filter accuracy
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Count only the items we created in this test
        our_active_items = [r for r in response.data['results'] 
                           if test_id in r['employee_id'] and r['is_active']]
        
        self.assertEqual(len(our_active_items), num_active)
        
        # Verify all our results match filter
        for result in our_active_items:
            self.assertTrue(result['is_active'])


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
        # Create admin user
        admin = User.objects.create_user(
            username=f'admin_search_{len(search_term)}',
            email=f'admin_search_{len(search_term)}@test.com',
            password='testpass123',
            role='ADMIN'
        )
        
        # Create necessary related objects
        faculty = Faculty.objects.create(name='Test Faculty', code='TF')
        department = Department.objects.create(
            name='Test Department',
            code='TD',
            faculty=faculty
        )
        
        # Create matching teachers (search term in employee_id)
        for i in range(num_matching):
            user = User.objects.create_user(
                username=f'match_{search_term}_{i}',
                email=f'match_{search_term}_{i}@test.com',
                password='testpass123',
                role='TEACHER'
            )
            Teacher.objects.create(
                user=user,
                employee_id=f'{search_term}{i}',
                department=department,
                rank='ASSISTANT',
                contract_type='PERMANENT',
                hire_date=date(2023, 9, 1)
            )
        
        # Create non-matching teachers
        for i in range(num_non_matching):
            user = User.objects.create_user(
                username=f'nomatch_{i}',
                email=f'nomatch_{i}@test.com',
                password='testpass123',
                role='TEACHER'
            )
            Teacher.objects.create(
                user=user,
                employee_id=f'DIFF{i}',
                department=department,
                rank='ASSISTANT',
                contract_type='PERMANENT',
                hire_date=date(2023, 9, 1)
            )
        
        # Make API request with search
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get(f'/api/teachers/teachers/?search={search_term}')
        
        # Verify search relevance
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], num_matching)
        
        # Verify all results contain search term
        for result in response.data['results']:
            self.assertIn(search_term.lower(), result['employee_id'].lower())



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
        # Create admin user
        admin = User.objects.create_user(
            username=f'admin_order_{num_items}',
            email=f'admin_order_{num_items}@test.com',
            password='testpass123',
            role='ADMIN'
        )
        
        # Create necessary related objects
        faculty = Faculty.objects.create(name='Test Faculty', code='TF')
        department = Department.objects.create(
            name='Test Department',
            code='TD',
            faculty=faculty
        )
        
        # Create teachers with different employee IDs
        employee_ids = []
        for i in range(num_items):
            employee_id = f'TEACH{1000 + (i * 100)}'
            employee_ids.append(employee_id)
            user = User.objects.create_user(
                username=f'teacher_order_{num_items}_{i}',
                email=f'teacher_order_{num_items}_{i}@test.com',
                password='testpass123',
                role='TEACHER'
            )
            Teacher.objects.create(
                user=user,
                employee_id=employee_id,
                department=department,
                rank='ASSISTANT',
                contract_type='PERMANENT',
                hire_date=date(2023, 9, 1)
            )
        
        # Make API request with ascending order
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get('/api/teachers/teachers/?ordering=employee_id')
        
        # Verify ordering
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_ids = [r['employee_id'] for r in response.data['results']]
        self.assertEqual(result_ids, sorted(result_ids))
        
        # Make API request with descending order
        response = client.get('/api/teachers/teachers/?ordering=-employee_id')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_ids = [r['employee_id'] for r in response.data['results']]
        self.assertEqual(result_ids, sorted(result_ids, reverse=True))


class MultipleFilterPropertyTests(TestCase):
    """Property tests for multiple filter combination."""
    
    @settings(max_examples=10, deadline=None)
    @given(
        rank=st.sampled_from(['ASSISTANT', 'LECTURER', 'SENIOR_LECTURER']),
        contract_type=st.sampled_from(['PERMANENT', 'CONTRACT', 'VISITING']),
        num_matching=st.integers(min_value=1, max_value=3),
        num_non_matching=st.integers(min_value=1, max_value=3)
    )
    def test_property_22_multiple_filter_combination(self, rank, contract_type, 
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
        
        # Create admin user
        admin = User.objects.create_user(
            username=f'admin_multi_{test_id}',
            email=f'admin_multi_{test_id}@test.com',
            password='testpass123',
            role='ADMIN'
        )
        
        # Create necessary related objects
        faculty = Faculty.objects.create(name=f'Faculty-{test_id}', code=f'F{test_id}')
        department = Department.objects.create(
            name=f'Department-{test_id}',
            code=f'D{test_id}',
            faculty=faculty
        )
        
        # Create matching teachers (specific rank and contract_type)
        for i in range(num_matching):
            user = User.objects.create_user(
                username=f'match_{test_id}_{i}',
                email=f'match_{test_id}_{i}@test.com',
                password='testpass123',
                role='TEACHER'
            )
            Teacher.objects.create(
                user=user,
                employee_id=f'MATCH{test_id}{i}',
                department=department,
                rank=rank,
                contract_type=contract_type,
                hire_date=date(2023, 9, 1)
            )
        
        # Create non-matching teachers (different rank or contract_type)
        for i in range(num_non_matching):
            user = User.objects.create_user(
                username=f'nomatch_{test_id}_{i}',
                email=f'nomatch_{test_id}_{i}@test.com',
                password='testpass123',
                role='TEACHER'
            )
            # Use different rank or different contract_type
            different_rank = 'PROFESSOR' if rank == 'ASSISTANT' else 'ASSISTANT'
            different_contract = 'PART_TIME' if contract_type == 'PERMANENT' else 'PERMANENT'
            Teacher.objects.create(
                user=user,
                employee_id=f'NOMATCH{test_id}{i}',
                department=department,
                rank=different_rank if i % 2 == 0 else rank,
                contract_type=different_contract if i % 2 == 1 else contract_type,
                hire_date=date(2023, 9, 1)
            )
        
        # Make API request with multiple filters
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get(
            f'/api/teachers/teachers/?rank={rank}&contract_type={contract_type}'
        )
        
        # Verify multiple filter combination
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Count only the items we created in this test
        our_matching_items = [r for r in response.data['results'] 
                             if test_id in r['employee_id']]
        
        self.assertEqual(len(our_matching_items), num_matching)
        
        # Verify all results match both filters
        for result in our_matching_items:
            self.assertEqual(result['rank'], rank)
            self.assertEqual(result['contract_type'], contract_type)



# TeacherCourse ViewSet Property Tests

class TeacherCoursePaginationPropertyTests(TestCase):
    """Property tests for TeacherCourse pagination consistency."""
    
    @settings(max_examples=10, deadline=None)
    @given(
        num_items=st.integers(min_value=21, max_value=100)
    )
    def test_property_4_teacher_course_pagination_consistency(self, num_items):
        """
        Feature: backend-api-implementation, Property 4: Pagination Consistency
        
        **Validates: Requirements 2.2**
        
        For any list endpoint with more than 20 items, the response should return
        exactly 20 items per page with pagination metadata.
        """
        # Create admin user
        admin = User.objects.create_user(
            username=f'admin_tc_pag_{num_items}',
            email=f'admin_tc_pag_{num_items}@test.com',
            password='testpass123',
            role='ADMIN'
        )
        
        # Create necessary related objects
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
        
        # Create academic year and semester
        academic_year = AcademicYear.objects.create(
            name='2023-2024',
            start_date=date(2023, 9, 1),
            end_date=date(2024, 6, 30)
        )
        semester = Semester.objects.create(
            academic_year=academic_year,
            semester_type='FALL',
            start_date=date(2023, 9, 1),
            end_date=date(2024, 1, 31)
        )
        
        # Create teacher
        teacher_user = User.objects.create_user(
            username=f'teacher_tc_{num_items}',
            email=f'teacher_tc_{num_items}@test.com',
            password='testpass123',
            role='TEACHER'
        )
        teacher = Teacher.objects.create(
            user=teacher_user,
            employee_id=f'TEACHTC{num_items}',
            department=department,
            rank='ASSISTANT',
            contract_type='PERMANENT',
            hire_date=date(2023, 9, 1)
        )
        
        # Create multiple teacher course assignments
        for i in range(num_items):
            course = Course.objects.create(
                name=f'Course {i}',
                code=f'C{num_items}{i:04d}',
                program=program,
                credits=3
            )
            TeacherCourse.objects.create(
                teacher=teacher,
                course=course,
                semester=semester,
                is_primary=True
            )
        
        # Make API request
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get('/api/teachers/assignments/')
        
        # Verify pagination
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        
        # Verify exactly 20 items per page
        self.assertEqual(len(response.data['results']), 20)
        self.assertEqual(response.data['count'], num_items)


class TeacherCourseCreatePropertyTests(TestCase):
    """Property tests for TeacherCourse create operations."""
    
    @settings(max_examples=10, deadline=None)
    @given(
        year=st.integers(min_value=2020, max_value=2030),
        is_primary=st.booleans()
    )
    def test_property_6_teacher_course_create_operation_success(self, year, is_primary):
        """
        Feature: backend-api-implementation, Property 6: Create Operation Success
        
        **Validates: Requirements 2.4**
        
        For any valid create request, the API should return HTTP 201 with the
        created resource containing all fields including auto-generated ones.
        """
        # Create admin user
        admin = User.objects.create_user(
            username=f'admin_tc_create_{year}',
            email=f'admin_tc_create_{year}@test.com',
            password='testpass123',
            role='ADMIN'
        )
        
        # Create necessary related objects
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
        
        # Create academic year and semester
        academic_year = AcademicYear.objects.create(
            name=f'{year}-{year+1}',
            start_date=date(year, 9, 1),
            end_date=date(year + 1, 6, 30)
        )
        semester = Semester.objects.create(
            academic_year=academic_year,
            semester_type='FALL',
            start_date=date(year, 9, 1),
            end_date=date(year + 1, 1, 31)
        )
        
        # Create teacher
        teacher_user = User.objects.create_user(
            username=f'teacher_tc_create_{year}',
            email=f'teacher_tc_create_{year}@test.com',
            password='testpass123',
            role='TEACHER'
        )
        teacher = Teacher.objects.create(
            user=teacher_user,
            employee_id=f'TEACHTC{year}',
            department=department,
            rank='ASSISTANT',
            contract_type='PERMANENT',
            hire_date=date(year, 9, 1)
        )
        
        # Create course
        course = Course.objects.create(
            name=f'Course {year}',
            code=f'C{year}',
            program=program,
            credits=3
        )
        
        # Prepare data
        data = {
            'teacher': teacher.id,
            'course': course.id,
            'semester': semester.id,
            'is_primary': is_primary
        }
        
        # Make API request
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.post('/api/teachers/assignments/', data)
        
        # Verify response
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['teacher'], data['teacher'])
        self.assertEqual(response.data['course'], data['course'])
        self.assertEqual(response.data['semester'], data['semester'])
        self.assertEqual(response.data['is_primary'], is_primary)



# TeacherContract ViewSet Property Tests

class TeacherContractPaginationPropertyTests(TestCase):
    """Property tests for TeacherContract pagination consistency."""
    
    @settings(max_examples=10, deadline=None)
    @given(
        num_items=st.integers(min_value=21, max_value=100)
    )
    def test_property_4_teacher_contract_pagination_consistency(self, num_items):
        """
        Feature: backend-api-implementation, Property 4: Pagination Consistency
        
        **Validates: Requirements 2.2**
        
        For any list endpoint with more than 20 items, the response should return
        exactly 20 items per page with pagination metadata.
        """
        # Create admin user
        admin = User.objects.create_user(
            username=f'admin_tcon_pag_{num_items}',
            email=f'admin_tcon_pag_{num_items}@test.com',
            password='testpass123',
            role='ADMIN'
        )
        
        # Create necessary related objects
        faculty = Faculty.objects.create(name='Test Faculty', code='TF')
        department = Department.objects.create(
            name='Test Department',
            code='TD',
            faculty=faculty
        )
        
        # Create teacher
        teacher_user = User.objects.create_user(
            username=f'teacher_tcon_{num_items}',
            email=f'teacher_tcon_{num_items}@test.com',
            password='testpass123',
            role='TEACHER'
        )
        teacher = Teacher.objects.create(
            user=teacher_user,
            employee_id=f'TEACHTCON{num_items}',
            department=department,
            rank='ASSISTANT',
            contract_type='PERMANENT',
            hire_date=date(2023, 9, 1)
        )
        
        # Create multiple teacher contracts
        for i in range(num_items):
            TeacherContract.objects.create(
                teacher=teacher,
                contract_number=f'CON{num_items}{i:04d}',
                start_date=date(2023, 9, 1),
                end_date=date(2024, 6, 30),
                base_salary=Decimal('50000.00'),
                status='ACTIVE'
            )
        
        # Make API request
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get('/api/teachers/contracts/')
        
        # Verify pagination
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        
        # Verify exactly 20 items per page
        self.assertEqual(len(response.data['results']), 20)
        self.assertEqual(response.data['count'], num_items)


class TeacherContractCreatePropertyTests(TestCase):
    """Property tests for TeacherContract create operations."""
    
    @settings(max_examples=10, deadline=None)
    @given(
        year=st.integers(min_value=2020, max_value=2030),
        salary=st.decimals(min_value=30000, max_value=200000, places=2)
    )
    def test_property_6_teacher_contract_create_operation_success(self, year, salary):
        """
        Feature: backend-api-implementation, Property 6: Create Operation Success
        
        **Validates: Requirements 2.4**
        
        For any valid create request, the API should return HTTP 201 with the
        created resource containing all fields including auto-generated ones.
        """
        # Create admin user
        admin = User.objects.create_user(
            username=f'admin_tcon_create_{year}',
            email=f'admin_tcon_create_{year}@test.com',
            password='testpass123',
            role='ADMIN'
        )
        
        # Create necessary related objects
        faculty = Faculty.objects.create(name='Test Faculty', code='TF')
        department = Department.objects.create(
            name='Test Department',
            code='TD',
            faculty=faculty
        )
        
        # Create teacher
        teacher_user = User.objects.create_user(
            username=f'teacher_tcon_create_{year}',
            email=f'teacher_tcon_create_{year}@test.com',
            password='testpass123',
            role='TEACHER'
        )
        teacher = Teacher.objects.create(
            user=teacher_user,
            employee_id=f'TEACHTCON{year}',
            department=department,
            rank='ASSISTANT',
            contract_type='PERMANENT',
            hire_date=date(year, 9, 1)
        )
        
        # Prepare data
        data = {
            'teacher': teacher.id,
            'contract_number': f'CON{year}',
            'start_date': date(year, 9, 1).isoformat(),
            'end_date': date(year + 1, 6, 30).isoformat(),
            'base_salary': str(salary),
            'status': 'ACTIVE'
        }
        
        # Make API request
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.post('/api/teachers/contracts/', data)
        
        # Verify response
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['teacher'], data['teacher'])
        self.assertEqual(response.data['contract_number'], data['contract_number'])
        self.assertEqual(Decimal(response.data['base_salary']), Decimal(data['base_salary']))


class TeacherContractValidationPropertyTests(TestCase):
    """Property tests for TeacherContract validation."""
    
    @settings(max_examples=10, deadline=None)
    @given(
        year=st.integers(min_value=2020, max_value=2030)
    )
    def test_property_9_teacher_contract_validation_error_response(self, year):
        """
        Feature: backend-api-implementation, Property 9: Validation Error Response
        
        **Validates: Requirements 2.7**
        
        For any request with invalid data, the API should return HTTP 400 with
        a JSON object containing field-level error messages.
        """
        # Create admin user
        admin = User.objects.create_user(
            username=f'admin_tcon_val_{year}',
            email=f'admin_tcon_val_{year}@test.com',
            password='testpass123',
            role='ADMIN'
        )
        
        # Create necessary related objects
        faculty = Faculty.objects.create(name='Test Faculty', code='TF')
        department = Department.objects.create(
            name='Test Department',
            code='TD',
            faculty=faculty
        )
        
        # Create teacher
        teacher_user = User.objects.create_user(
            username=f'teacher_tcon_val_{year}',
            email=f'teacher_tcon_val_{year}@test.com',
            password='testpass123',
            role='TEACHER'
        )
        teacher = Teacher.objects.create(
            user=teacher_user,
            employee_id=f'TEACHTCON{year}',
            department=department,
            rank='ASSISTANT',
            contract_type='PERMANENT',
            hire_date=date(year, 9, 1)
        )
        
        # Prepare invalid data (end_date before start_date)
        data = {
            'teacher': teacher.id,
            'contract_number': f'CONVAL{year}',
            'start_date': date(year, 9, 1).isoformat(),
            'end_date': date(year, 6, 30).isoformat(),  # Invalid: before start_date
            'base_salary': '50000.00',
            'status': 'ACTIVE'
        }
        
        # Make API request
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.post('/api/teachers/contracts/', data)
        
        # Verify validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(isinstance(response.data, dict))
        self.assertIn('end_date', response.data)


class TeacherContractFilterPropertyTests(TestCase):
    """Property tests for TeacherContract filtering accuracy."""
    
    @settings(max_examples=10, deadline=None)
    @given(
        num_active=st.integers(min_value=1, max_value=5),
        num_expired=st.integers(min_value=1, max_value=5)
    )
    def test_property_19_teacher_contract_filter_result_accuracy(self, num_active, num_expired):
        """
        Feature: backend-api-implementation, Property 19: Filter Result Accuracy
        
        **Validates: Requirements 4.2**
        
        For any filter parameters provided in a list request, all returned
        results should match the filter criteria exactly.
        """
        # Create unique identifier for this test run
        import uuid
        test_id = str(uuid.uuid4())[:8]
        
        # Create admin user
        admin = User.objects.create_user(
            username=f'admin_tcon_filt_{test_id}',
            email=f'admin_tcon_filt_{test_id}@test.com',
            password='testpass123',
            role='ADMIN'
        )
        
        # Create necessary related objects
        faculty = Faculty.objects.create(name=f'Faculty-{test_id}', code=f'F{test_id}')
        department = Department.objects.create(
            name=f'Department-{test_id}',
            code=f'D{test_id}',
            faculty=faculty
        )
        
        # Create teacher
        teacher_user = User.objects.create_user(
            username=f'teacher_tcon_filt_{test_id}',
            email=f'teacher_tcon_filt_{test_id}@test.com',
            password='testpass123',
            role='TEACHER'
        )
        teacher = Teacher.objects.create(
            user=teacher_user,
            employee_id=f'TEACHTCON{test_id}',
            department=department,
            rank='ASSISTANT',
            contract_type='PERMANENT',
            hire_date=date(2023, 9, 1)
        )
        
        # Create active contracts
        for i in range(num_active):
            TeacherContract.objects.create(
                teacher=teacher,
                contract_number=f'ACTIVE{test_id}{i}',
                start_date=date(2023, 9, 1),
                end_date=date(2024, 6, 30),
                base_salary=Decimal('50000.00'),
                status='ACTIVE'
            )
        
        # Create expired contracts
        for i in range(num_expired):
            TeacherContract.objects.create(
                teacher=teacher,
                contract_number=f'EXPIRED{test_id}{i}',
                start_date=date(2022, 9, 1),
                end_date=date(2023, 6, 30),
                base_salary=Decimal('50000.00'),
                status='EXPIRED'
            )
        
        # Make API request with filter for active contracts
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get('/api/teachers/contracts/?status=ACTIVE')
        
        # Verify filter accuracy
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Count only the items we created in this test
        our_active_items = [r for r in response.data['results'] 
                           if test_id in r['contract_number'] and r['status'] == 'ACTIVE']
        
        self.assertEqual(len(our_active_items), num_active)
        
        # Verify all our results match filter
        for result in our_active_items:
            self.assertEqual(result['status'], 'ACTIVE')
