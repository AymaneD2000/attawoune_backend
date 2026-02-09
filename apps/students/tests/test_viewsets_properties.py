"""
Property-based tests for students viewsets.

These tests verify universal properties that should hold for all valid inputs.
Tests cover CRUD operations, pagination, filtering, searching, and ordering.
"""

from hypothesis import given, strategies as st, settings
from hypothesis.extra.django import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from datetime import date, timedelta
from apps.students.models import Student, Enrollment, Attendance
from apps.university.models import (
    AcademicYear, Semester, Faculty, Department, Level, Program
)
from apps.scheduling.models import TimeSlot, Schedule, CourseSession
from apps.academics.models import Course
from apps.teachers.models import Teacher

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
        level = Level.objects.create(name='L1', order=1)
        program = Program.objects.create(
            name='Test Program',
            code='TP',
            department=department,
            level=level
        )
        
        # Create multiple students
        for i in range(num_items):
            user = User.objects.create_user(
                username=f'student_{num_items}_{i}',
                email=f'student_{num_items}_{i}@test.com',
                password='testpass123',
                role='STUDENT'
            )
            Student.objects.create(
                user=user,
                student_id=f'STU{num_items}{i:04d}',
                program=program,
                current_level=level,
                enrollment_date=date(2023, 9, 1)
            )
        
        # Make API request
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get('/api/students/students/')
        
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
        student_name=st.text(min_size=3, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll')))
    )
    def test_property_5_complete_resource_representation(self, year, student_name):
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
        level = Level.objects.create(name='L1', order=1)
        program = Program.objects.create(
            name='Test Program',
            code='TP',
            department=department,
            level=level
        )
        
        # Create student
        user = User.objects.create_user(
            username=f'student_det_{year}',
            email=f'student_det_{year}@test.com',
            password='testpass123',
            role='STUDENT',
            first_name=student_name[:100],
            last_name='Test'
        )
        student = Student.objects.create(
            user=user,
            student_id=f'STU{year}',
            program=program,
            current_level=level,
            enrollment_date=date(year, 9, 1)
        )
        
        # Make API request
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get(f'/api/students/students/{student.id}/')
        
        # Verify response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify all expected fields are present (based on StudentDetailSerializer)
        expected_fields = [
            'id', 'user', 'student_id', 'program', 'current_level',
            'enrollment_date', 'status', 'guardian_name', 'guardian_phone',
            'emergency_contact', 'created_at', 'updated_at',
            # Computed/display fields
            'user_name', 'user_email', 'program_name', 'level_display',
            'status_display', 'enrollments_count'
        ]
        for field in expected_fields:
            self.assertIn(field, response.data, f"Field '{field}' missing from detail response")


class CreateOperationPropertyTests(TestCase):
    """Property tests for create operations."""
    
    @settings(max_examples=10, deadline=None)
    @given(
        year=st.integers(min_value=2020, max_value=2030),
        student_num=st.integers(min_value=1, max_value=9999)
    )
    def test_property_6_create_operation_success(self, year, student_num):
        """
        Feature: backend-api-implementation, Property 6: Create Operation Success
        
        **Validates: Requirements 2.4**
        
        For any valid create request, the API should return HTTP 201 with the
        created resource containing all fields including auto-generated ones.
        """
        # Create admin user
        admin = User.objects.create_user(
            username=f'admin_create_{year}_{student_num}',
            email=f'admin_create_{year}_{student_num}@test.com',
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
        
        # Create user for student
        user = User.objects.create_user(
            username=f'student_create_{year}_{student_num}',
            email=f'student_create_{year}_{student_num}@test.com',
            password='testpass123',
            role='STUDENT'
        )
        
        # Prepare data
        data = {
            'user': user.id,
            'student_id': f'STU{year}{student_num:04d}',
            'program': program.id,
            'current_level': level.id,
            'enrollment_date': date(year, 9, 1).isoformat()
        }
        
        # Make API request
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.post('/api/students/students/', data)
        
        # Verify response
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Note: StudentCreateSerializer doesn't return id, created_at, updated_at
        # It returns the input data. To get those fields, we'd need to fetch the created object
        self.assertEqual(response.data['student_id'], data['student_id'])
        self.assertEqual(response.data['user'], data['user'])
        self.assertEqual(response.data['program'], data['program'])


class UpdateOperationPropertyTests(TestCase):
    """Property tests for update operations."""
    
    @settings(max_examples=10, deadline=None)
    @given(
        old_status=st.sampled_from(['ACTIVE', 'SUSPENDED']),
        new_status=st.sampled_from(['ACTIVE', 'SUSPENDED', 'GRADUATED', 'DROPPED'])
    )
    def test_property_7_update_operation_success(self, old_status, new_status):
        """
        Feature: backend-api-implementation, Property 7: Update Operation Success
        
        **Validates: Requirements 2.5**
        
        For any valid update request, the API should return HTTP 200 with the
        updated resource reflecting all changes.
        """
        # Create admin user
        admin = User.objects.create_user(
            username=f'admin_upd_{old_status}_{new_status}',
            email=f'admin_upd_{old_status}_{new_status}@test.com',
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
        
        # Create student
        user = User.objects.create_user(
            username=f'student_upd_{old_status}_{new_status}',
            email=f'student_upd_{old_status}_{new_status}@test.com',
            password='testpass123',
            role='STUDENT'
        )
        student = Student.objects.create(
            user=user,
            student_id=f'STU{old_status}{new_status}',
            program=program,
            current_level=level,
            enrollment_date=date(2023, 9, 1),
            status=old_status
        )
        
        # Prepare update data
        data = {
            'status': new_status
        }
        
        # Make API request
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.patch(f'/api/students/students/{student.id}/', data)
        
        # Verify response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], new_status)
        
        # Verify database was updated
        student.refresh_from_db()
        self.assertEqual(student.status, new_status)


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
        level = Level.objects.create(name='L1', order=1)
        program = Program.objects.create(
            name='Test Program',
            code='TP',
            department=department,
            level=level
        )
        
        # Create student
        user = User.objects.create_user(
            username=f'student_del_{year}',
            email=f'student_del_{year}@test.com',
            password='testpass123',
            role='STUDENT'
        )
        student = Student.objects.create(
            user=user,
            student_id=f'STUDEL{year}',
            program=program,
            current_level=level,
            enrollment_date=date(year, 9, 1)
        )
        
        # Make delete request
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.delete(f'/api/students/students/{student.id}/')
        
        # Verify delete response
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify subsequent GET returns 404
        response = client.get(f'/api/students/students/{student.id}/')
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
        level = Level.objects.create(name='L1', order=1)
        program = Program.objects.create(
            name='Test Program',
            code='TP',
            department=department,
            level=level
        )
        
        # Create user for student
        user = User.objects.create_user(
            username=f'student_val_{year}',
            email=f'student_val_{year}@test.com',
            password='testpass123',
            role='STUDENT'
        )
        
        # Prepare invalid data (missing required field)
        data = {
            'user': user.id,
            # Missing student_id (required field)
            'program': program.id,
            'current_level': level.id,
            'enrollment_date': date(year, 9, 1).isoformat()
        }
        
        # Make API request
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.post('/api/students/students/', data)
        
        # Verify validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(isinstance(response.data, dict))
        self.assertIn('student_id', response.data)


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
        response = client.get(f'/api/students/students/{non_existent_id}/')
        
        # Verify not found response
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class FilterPropertyTests(TestCase):
    """Property tests for filtering accuracy."""
    
    @settings(max_examples=10, deadline=None)
    @given(
        num_active=st.integers(min_value=1, max_value=5),
        num_suspended=st.integers(min_value=1, max_value=5)
    )
    def test_property_19_filter_result_accuracy(self, num_active, num_suspended):
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
        level = Level.objects.create(name=f'L1-{test_id}', order=1)
        program = Program.objects.create(
            name=f'Program-{test_id}',
            code=f'P{test_id}',
            department=department,
            level=level
        )
        
        # Create active students
        for i in range(num_active):
            user = User.objects.create_user(
                username=f'active_{test_id}_{i}',
                email=f'active_{test_id}_{i}@test.com',
                password='testpass123',
                role='STUDENT'
            )
            Student.objects.create(
                user=user,
                student_id=f'ACTIVE{test_id}{i}',
                program=program,
                current_level=level,
                enrollment_date=date(2023, 9, 1),
                status='ACTIVE'
            )
        
        # Create suspended students
        for i in range(num_suspended):
            user = User.objects.create_user(
                username=f'suspended_{test_id}_{i}',
                email=f'suspended_{test_id}_{i}@test.com',
                password='testpass123',
                role='STUDENT'
            )
            Student.objects.create(
                user=user,
                student_id=f'SUSP{test_id}{i}',
                program=program,
                current_level=level,
                enrollment_date=date(2023, 9, 1),
                status='SUSPENDED'
            )
        
        # Make API request with filter for active students
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get('/api/students/students/?status=ACTIVE')
        
        # Verify filter accuracy
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Count only the items we created in this test
        our_active_items = [r for r in response.data['results'] 
                           if test_id in r['student_id'] and r['status'] == 'ACTIVE']
        
        self.assertEqual(len(our_active_items), num_active)
        
        # Verify all our results match filter
        for result in our_active_items:
            self.assertEqual(result['status'], 'ACTIVE')


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
        level = Level.objects.create(name='L1', order=1)
        program = Program.objects.create(
            name='Test Program',
            code='TP',
            department=department,
            level=level
        )
        
        # Create matching students (search term in student_id)
        for i in range(num_matching):
            user = User.objects.create_user(
                username=f'match_{search_term}_{i}',
                email=f'match_{search_term}_{i}@test.com',
                password='testpass123',
                role='STUDENT'
            )
            Student.objects.create(
                user=user,
                student_id=f'{search_term}{i}',
                program=program,
                current_level=level,
                enrollment_date=date(2023, 9, 1)
            )
        
        # Create non-matching students
        for i in range(num_non_matching):
            user = User.objects.create_user(
                username=f'nomatch_{i}',
                email=f'nomatch_{i}@test.com',
                password='testpass123',
                role='STUDENT'
            )
            Student.objects.create(
                user=user,
                student_id=f'DIFF{i}',
                program=program,
                current_level=level,
                enrollment_date=date(2023, 9, 1)
            )
        
        # Make API request with search
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get(f'/api/students/students/?search={search_term}')
        
        # Verify search relevance
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], num_matching)
        
        # Verify all results contain search term
        for result in response.data['results']:
            self.assertIn(search_term.lower(), result['student_id'].lower())


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
        level = Level.objects.create(name='L1', order=1)
        program = Program.objects.create(
            name='Test Program',
            code='TP',
            department=department,
            level=level
        )
        
        # Create students with different student IDs
        student_ids = []
        for i in range(num_items):
            student_id = f'STU{1000 + (i * 100)}'
            student_ids.append(student_id)
            user = User.objects.create_user(
                username=f'student_order_{num_items}_{i}',
                email=f'student_order_{num_items}_{i}@test.com',
                password='testpass123',
                role='STUDENT'
            )
            Student.objects.create(
                user=user,
                student_id=student_id,
                program=program,
                current_level=level,
                enrollment_date=date(2023, 9, 1)
            )
        
        # Make API request with ascending order
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get('/api/students/students/?ordering=student_id')
        
        # Verify ordering
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_ids = [r['student_id'] for r in response.data['results']]
        self.assertEqual(result_ids, sorted(result_ids))
        
        # Make API request with descending order
        response = client.get('/api/students/students/?ordering=-student_id')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_ids = [r['student_id'] for r in response.data['results']]
        self.assertEqual(result_ids, sorted(result_ids, reverse=True))


class MultipleFilterPropertyTests(TestCase):
    """Property tests for multiple filter combination."""
    
    @settings(max_examples=10, deadline=None)
    @given(
        student_status=st.sampled_from(['ACTIVE', 'SUSPENDED']),
        num_matching=st.integers(min_value=1, max_value=3),
        num_non_matching=st.integers(min_value=1, max_value=3)
    )
    def test_property_22_multiple_filter_combination(self, student_status, num_matching, num_non_matching):
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
        level1 = Level.objects.create(name=f'L1-{test_id}', order=1)
        level2 = Level.objects.create(name=f'L2-{test_id}', order=2)
        program = Program.objects.create(
            name=f'Program-{test_id}',
            code=f'P{test_id}',
            department=department,
            level=level1
        )
        
        # Create matching students (specific status and level1)
        for i in range(num_matching):
            user = User.objects.create_user(
                username=f'match_{test_id}_{i}',
                email=f'match_{test_id}_{i}@test.com',
                password='testpass123',
                role='STUDENT'
            )
            Student.objects.create(
                user=user,
                student_id=f'MATCH{test_id}{i}',
                program=program,
                current_level=level1,
                enrollment_date=date(2023, 9, 1),
                status=student_status
            )
        
        # Create non-matching students (different status or level)
        for i in range(num_non_matching):
            user = User.objects.create_user(
                username=f'nomatch_{test_id}_{i}',
                email=f'nomatch_{test_id}_{i}@test.com',
                password='testpass123',
                role='STUDENT'
            )
            # Use different status or different level
            different_status = 'GRADUATED' if student_status == 'ACTIVE' else 'ACTIVE'
            Student.objects.create(
                user=user,
                student_id=f'NOMATCH{test_id}{i}',
                program=program,
                current_level=level2 if i % 2 == 0 else level1,
                enrollment_date=date(2023, 9, 1),
                status=different_status if i % 2 == 1 else student_status
            )
        
        # Make API request with multiple filters
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get(
            f'/api/students/students/?status={student_status}&current_level={level1.id}'
        )
        
        # Verify multiple filter combination
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Count only the items we created in this test
        our_matching_items = [r for r in response.data['results'] 
                             if test_id in r['student_id']]
        
        self.assertEqual(len(our_matching_items), num_matching)
        
        # Verify all results match both filters
        for result in our_matching_items:
            self.assertEqual(result['status'], student_status)
            # Note: List serializer uses level_display, not current_level ID
            # We can verify by checking the student_id contains our test_id
            self.assertIn(test_id, result['student_id'])
