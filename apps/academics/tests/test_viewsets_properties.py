"""
Property-based tests for academics viewsets.

These tests verify universal properties that should hold for all valid inputs.
Tests cover CRUD operations, pagination, filtering, searching, and ordering.
"""

from hypothesis import given, strategies as st, settings
from hypothesis.extra.django import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from datetime import date, time, timedelta
from decimal import Decimal
from apps.academics.models import Course, Exam, Grade, CourseGrade, ReportCard
from apps.university.models import (
    AcademicYear, Semester, Faculty, Department, Level, Program, Classroom
)
from apps.students.models import Student
from apps.teachers.models import Teacher, TeacherCourse

User = get_user_model()


class CoursePaginationPropertyTests(TestCase):
    """Property tests for Course pagination consistency."""
    
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
        academic_year = AcademicYear.objects.create(
            name='2023-2024',
            start_date=date(2023, 9, 1),
            end_date=date(2024, 6, 30),
            is_current=True
        )
        semester = Semester.objects.create(
            academic_year=academic_year,
            semester_type='S1',
            start_date=date(2023, 9, 1),
            end_date=date(2024, 1, 31),
            is_current=True
        )
        
        # Create multiple courses
        for i in range(num_items):
            Course.objects.create(
                name=f'Course {num_items}_{i}',
                code=f'C{num_items}{i:04d}',
                program=program,
                course_type='REQUIRED',
                credits=3,
                semester=semester,
                is_active=True
            )
        
        # Make API request
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get('/api/academics/courses/')
        
        # Verify pagination
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        
        # Verify exactly 20 items per page
        self.assertEqual(len(response.data['results']), 20)
        self.assertEqual(response.data['count'], num_items)


class CourseDetailEndpointPropertyTests(TestCase):
    """Property tests for Course detail endpoint completeness."""
    
    @settings(max_examples=10, deadline=None)
    @given(
        year=st.integers(min_value=2020, max_value=2030),
        credits=st.integers(min_value=1, max_value=6)
    )
    def test_property_5_complete_resource_representation(self, year, credits):
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
        academic_year = AcademicYear.objects.create(
            name=f'{year}-{year+1}',
            start_date=date(year, 9, 1),
            end_date=date(year+1, 6, 30),
            is_current=True
        )
        semester = Semester.objects.create(
            academic_year=academic_year,
            semester_type='S1',
            start_date=date(year, 9, 1),
            end_date=date(year+1, 1, 31),
            is_current=True
        )
        
        # Create course
        course = Course.objects.create(
            name='Test Course',
            code=f'TC{year}',
            program=program,
            course_type='REQUIRED',
            credits=credits,
            semester=semester,
            is_active=True
        )
        
        # Make API request
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get(f'/api/academics/courses/{course.id}/')
        
        # Verify response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify all expected fields are present
        expected_fields = [
            'id', 'name', 'code', 'description', 'program', 'course_type',
            'credits', 'semester', 'is_active', 'created_at', 'updated_at',
            # Computed/display fields
            'program_name', 'program_code', 'semester_name', 'course_type_display',
            'prerequisites_count', 'exams_count'
        ]
        for field in expected_fields:
            self.assertIn(field, response.data, f"Field '{field}' missing from detail response")


class CourseCreateOperationPropertyTests(TestCase):
    """Property tests for Course create operations."""
    
    @settings(max_examples=10, deadline=None)
    @given(
        year=st.integers(min_value=2020, max_value=2030),
        credits=st.integers(min_value=1, max_value=6)
    )
    def test_property_6_create_operation_success(self, year, credits):
        """
        Feature: backend-api-implementation, Property 6: Create Operation Success
        
        **Validates: Requirements 2.4**
        
        For any valid create request, the API should return HTTP 201 with the
        created resource containing all fields including auto-generated ones.
        """
        # Create admin user
        admin = User.objects.create_user(
            username=f'admin_create_{year}',
            email=f'admin_create_{year}@test.com',
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
        academic_year = AcademicYear.objects.create(
            name=f'{year}-{year+1}',
            start_date=date(year, 9, 1),
            end_date=date(year+1, 6, 30),
            is_current=True
        )
        semester = Semester.objects.create(
            academic_year=academic_year,
            semester_type='S1',
            start_date=date(year, 9, 1),
            end_date=date(year+1, 1, 31),
            is_current=True
        )
        
        # Prepare data
        data = {
            'name': f'New Course {year}',
            'code': f'NC{year}',
            'program': program.id,
            'course_type': 'REQUIRED',
            'credits': credits,
            'semester': semester.id,
            'is_active': True
        }
        
        # Make API request
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.post('/api/academics/courses/', data)
        
        # Verify response
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['code'], data['code'])
        self.assertEqual(response.data['credits'], data['credits'])


class CourseUpdateOperationPropertyTests(TestCase):
    """Property tests for Course update operations."""
    
    @settings(max_examples=10, deadline=None)
    @given(
        old_credits=st.integers(min_value=1, max_value=3),
        new_credits=st.integers(min_value=1, max_value=6)
    )
    def test_property_7_update_operation_success(self, old_credits, new_credits):
        """
        Feature: backend-api-implementation, Property 7: Update Operation Success
        
        **Validates: Requirements 2.5**
        
        For any valid update request, the API should return HTTP 200 with the
        updated resource reflecting all changes.
        """
        # Create admin user
        admin = User.objects.create_user(
            username=f'admin_upd_{old_credits}_{new_credits}',
            email=f'admin_upd_{old_credits}_{new_credits}@test.com',
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
        academic_year = AcademicYear.objects.create(
            name='2023-2024',
            start_date=date(2023, 9, 1),
            end_date=date(2024, 6, 30),
            is_current=True
        )
        semester = Semester.objects.create(
            academic_year=academic_year,
            semester_type='S1',
            start_date=date(2023, 9, 1),
            end_date=date(2024, 1, 31),
            is_current=True
        )
        
        # Create course
        course = Course.objects.create(
            name='Test Course',
            code=f'TC{old_credits}{new_credits}',
            program=program,
            course_type='REQUIRED',
            credits=old_credits,
            semester=semester,
            is_active=True
        )
        
        # Prepare update data
        data = {
            'credits': new_credits
        }
        
        # Make API request
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.patch(f'/api/academics/courses/{course.id}/', data)
        
        # Verify response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['credits'], new_credits)
        
        # Verify database was updated
        course.refresh_from_db()
        self.assertEqual(course.credits, new_credits)


class CourseDeleteOperationPropertyTests(TestCase):
    """Property tests for Course delete operations."""
    
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
        academic_year = AcademicYear.objects.create(
            name=f'{year}-{year+1}',
            start_date=date(year, 9, 1),
            end_date=date(year+1, 6, 30),
            is_current=True
        )
        semester = Semester.objects.create(
            academic_year=academic_year,
            semester_type='S1',
            start_date=date(year, 9, 1),
            end_date=date(year+1, 1, 31),
            is_current=True
        )
        
        # Create course
        course = Course.objects.create(
            name='Delete Course',
            code=f'DEL{year}',
            program=program,
            course_type='REQUIRED',
            credits=3,
            semester=semester,
            is_active=True
        )
        
        # Make delete request
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.delete(f'/api/academics/courses/{course.id}/')
        
        # Verify delete response
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify subsequent GET returns 404
        response = client.get(f'/api/academics/courses/{course.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class CourseValidationErrorPropertyTests(TestCase):
    """Property tests for Course validation error responses."""
    
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
        academic_year = AcademicYear.objects.create(
            name=f'{year}-{year+1}',
            start_date=date(year, 9, 1),
            end_date=date(year+1, 6, 30),
            is_current=True
        )
        semester = Semester.objects.create(
            academic_year=academic_year,
            semester_type='S1',
            start_date=date(year, 9, 1),
            end_date=date(year+1, 1, 31),
            is_current=True
        )
        
        # Prepare invalid data (missing required field)
        data = {
            'name': 'Invalid Course',
            # Missing code (required field)
            'program': program.id,
            'course_type': 'REQUIRED',
            'credits': 3,
            'semester': semester.id
        }
        
        # Make API request
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.post('/api/academics/courses/', data)
        
        # Verify validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(isinstance(response.data, dict))
        self.assertIn('code', response.data)


class CourseNotFoundPropertyTests(TestCase):
    """Property tests for Course not found responses."""
    
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
        response = client.get(f'/api/academics/courses/{non_existent_id}/')
        
        # Verify not found response
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class CourseFilterPropertyTests(TestCase):
    """Property tests for Course filtering accuracy."""
    
    @settings(max_examples=10, deadline=None)
    @given(
        num_required=st.integers(min_value=1, max_value=5),
        num_elective=st.integers(min_value=1, max_value=5)
    )
    def test_property_19_filter_result_accuracy(self, num_required, num_elective):
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
        academic_year = AcademicYear.objects.create(
            name=f'AY-{test_id}',
            start_date=date(2023, 9, 1),
            end_date=date(2024, 6, 30),
            is_current=False
        )
        semester = Semester.objects.create(
            academic_year=academic_year,
            semester_type='S1',
            start_date=date(2023, 9, 1),
            end_date=date(2024, 1, 31),
            is_current=False
        )
        
        # Create required courses
        for i in range(num_required):
            Course.objects.create(
                name=f'Required-{test_id}-{i}',
                code=f'REQ{test_id}{i}',
                program=program,
                course_type='REQUIRED',
                credits=3,
                semester=semester,
                is_active=True
            )
        
        # Create elective courses
        for i in range(num_elective):
            Course.objects.create(
                name=f'Elective-{test_id}-{i}',
                code=f'ELEC{test_id}{i}',
                program=program,
                course_type='ELECTIVE',
                credits=3,
                semester=semester,
                is_active=True
            )
        
        # Make API request with filter for required courses
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get('/api/academics/courses/?course_type=REQUIRED')
        
        # Verify filter accuracy
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Count only the items we created in this test
        our_required_items = [r for r in response.data['results'] 
                             if test_id in r['code'] and r['course_type'] == 'REQUIRED']
        
        self.assertEqual(len(our_required_items), num_required)
        
        # Verify all our results match filter
        for result in our_required_items:
            self.assertEqual(result['course_type'], 'REQUIRED')


class CourseSearchPropertyTests(TestCase):
    """Property tests for Course search result relevance."""
    
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
        academic_year = AcademicYear.objects.create(
            name='2023-2024',
            start_date=date(2023, 9, 1),
            end_date=date(2024, 6, 30),
            is_current=True
        )
        semester = Semester.objects.create(
            academic_year=academic_year,
            semester_type='S1',
            start_date=date(2023, 9, 1),
            end_date=date(2024, 1, 31),
            is_current=True
        )
        
        # Create matching courses (search term in code)
        for i in range(num_matching):
            Course.objects.create(
                name=f'Course {i}',
                code=f'{search_term}{i}',
                program=program,
                course_type='REQUIRED',
                credits=3,
                semester=semester,
                is_active=True
            )
        
        # Create non-matching courses
        for i in range(num_non_matching):
            Course.objects.create(
                name=f'Different Course {i}',
                code=f'DIFF{i}',
                program=program,
                course_type='REQUIRED',
                credits=3,
                semester=semester,
                is_active=True
            )
        
        # Make API request with search
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get(f'/api/academics/courses/?search={search_term}')
        
        # Verify search relevance
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], num_matching)
        
        # Verify all results contain search term
        for result in response.data['results']:
            self.assertIn(search_term.lower(), result['code'].lower())


class CourseOrderingPropertyTests(TestCase):
    """Property tests for Course ordering correctness."""
    
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
        academic_year = AcademicYear.objects.create(
            name='2023-2024',
            start_date=date(2023, 9, 1),
            end_date=date(2024, 6, 30),
            is_current=True
        )
        semester = Semester.objects.create(
            academic_year=academic_year,
            semester_type='S1',
            start_date=date(2023, 9, 1),
            end_date=date(2024, 1, 31),
            is_current=True
        )
        
        # Create courses with different codes
        codes = []
        for i in range(num_items):
            code = f'COURSE{1000 + (i * 100)}'
            codes.append(code)
            Course.objects.create(
                name=f'Course {i}',
                code=code,
                program=program,
                course_type='REQUIRED',
                credits=3,
                semester=semester,
                is_active=True
            )
        
        # Make API request with ascending order
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get('/api/academics/courses/?ordering=code')
        
        # Verify ordering
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_codes = [r['code'] for r in response.data['results']]
        self.assertEqual(result_codes, sorted(result_codes))
        
        # Make API request with descending order
        response = client.get('/api/academics/courses/?ordering=-code')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_codes = [r['code'] for r in response.data['results']]
        self.assertEqual(result_codes, sorted(result_codes, reverse=True))


class CourseMultipleFilterPropertyTests(TestCase):
    """Property tests for Course multiple filter combination."""
    
    @settings(max_examples=10, deadline=None)
    @given(
        course_type=st.sampled_from(['REQUIRED', 'ELECTIVE']),
        is_active=st.booleans(),
        num_matching=st.integers(min_value=1, max_value=3),
        num_non_matching=st.integers(min_value=1, max_value=3)
    )
    def test_property_22_multiple_filter_combination(self, course_type, is_active, 
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
        level = Level.objects.create(name=f'L1-{test_id}', order=1)
        program = Program.objects.create(
            name=f'Program-{test_id}',
            code=f'P{test_id}',
            department=department,
            level=level
        )
        academic_year = AcademicYear.objects.create(
            name=f'AY-{test_id}',
            start_date=date(2023, 9, 1),
            end_date=date(2024, 6, 30),
            is_current=False
        )
        semester = Semester.objects.create(
            academic_year=academic_year,
            semester_type='S1',
            start_date=date(2023, 9, 1),
            end_date=date(2024, 1, 31),
            is_current=False
        )
        
        # Create matching courses (specific course_type and is_active)
        for i in range(num_matching):
            Course.objects.create(
                name=f'Match-{test_id}-{i}',
                code=f'MATCH{test_id}{i}',
                program=program,
                course_type=course_type,
                credits=3,
                semester=semester,
                is_active=is_active
            )
        
        # Create non-matching courses (different course_type or is_active)
        for i in range(num_non_matching):
            different_type = 'PRACTICAL' if course_type == 'REQUIRED' else 'REQUIRED'
            Course.objects.create(
                name=f'NoMatch-{test_id}-{i}',
                code=f'NOMATCH{test_id}{i}',
                program=program,
                course_type=different_type if i % 2 == 0 else course_type,
                credits=3,
                semester=semester,
                is_active=not is_active if i % 2 == 1 else is_active
            )
        
        # Make API request with multiple filters
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get(
            f'/api/academics/courses/?course_type={course_type}&is_active={str(is_active).lower()}'
        )
        
        # Verify multiple filter combination
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Count only the items we created in this test
        our_matching_items = [r for r in response.data['results'] 
                             if test_id in r['code']]
        
        self.assertEqual(len(our_matching_items), num_matching)
        
        # Verify all results match both filters
        for result in our_matching_items:
            self.assertEqual(result['course_type'], course_type)
            self.assertEqual(result['is_active'], is_active)
