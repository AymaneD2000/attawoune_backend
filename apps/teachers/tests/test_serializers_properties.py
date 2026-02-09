"""
Property-based tests for teachers serializers.

These tests verify universal properties that should hold for all valid inputs.
"""

from hypothesis import given, strategies as st, settings
from hypothesis.extra.django import TestCase
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from decimal import Decimal
import uuid
from apps.teachers.serializers import (
    TeacherListSerializer,
    TeacherDetailSerializer,
    TeacherCreateSerializer,
    TeacherCourseListSerializer,
    TeacherCourseDetailSerializer,
    TeacherCourseCreateSerializer,
    TeacherContractListSerializer,
    TeacherContractDetailSerializer,
    TeacherContractCreateSerializer,
)
from apps.teachers.models import Teacher, TeacherCourse, TeacherContract
from apps.university.models import (
    AcademicYear, Semester, Faculty, Department, Level, Program
)
from apps.academics.models import Course

User = get_user_model()


class TeacherSerializerPropertyTests(TestCase):
    """Property tests for Teacher serializers."""
    
    def setUp(self):
        """Set up test data."""
        # Create faculty with unique username
        unique_id = str(uuid.uuid4())[:8]
        self.dean = User.objects.create_user(
            username=f'dean_teacher_{unique_id}',
            email=f'dean_teacher_{unique_id}@test.com',
            password='testpass123',
            role=User.Role.ADMIN,
            first_name='Dean',
            last_name='Test'
        )
        self.faculty = Faculty.objects.create(
            name='Test Faculty',
            code=f'TF{unique_id}',
            dean=self.dean
        )
        
        # Create department
        self.department = Department.objects.create(
            name='Test Department',
            code=f'TD{unique_id}',
            faculty=self.faculty,
            head=self.dean
        )
    
    @settings(max_examples=10)
    @given(
        first_name=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
        last_name=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
        employee_id=st.text(min_size=5, max_size=15, alphabet=st.characters(whitelist_categories=('Nd', 'Lu'))),
        rank=st.sampled_from([choice[0] for choice in Teacher.Rank.choices]),
        contract_type=st.sampled_from([choice[0] for choice in Teacher.ContractType.choices]),
    )
    def test_property_1_foreign_key_representation(self, first_name, last_name, employee_id, rank, contract_type):
        """
        Feature: backend-api-implementation, Property 1: Foreign Key Representation
        
        **Validates: Requirements 1.8**
        
        For any model instance with foreign key relationships, when serialized,
        the output should include readable representations (names, codes, or display values)
        of the related objects, not just IDs.
        """
        # Create user
        user = User.objects.create_user(
            username=f"teacher_{employee_id}".lower()[:30],
            email=f"{employee_id.lower()}@test.com",
            first_name=first_name,
            last_name=last_name,
            role=User.Role.TEACHER,
            password="testpass123"
        )
        
        # Create teacher
        teacher = Teacher.objects.create(
            user=user,
            employee_id=employee_id,
            department=self.department,
            rank=rank,
            contract_type=contract_type,
            hire_date=date.today()
        )
        
        # Test list serializer
        list_serializer = TeacherListSerializer(teacher)
        list_data = list_serializer.data
        
        # Verify readable representations are included
        self.assertIn('user_name', list_data)
        self.assertIn('department_name', list_data)
        self.assertIn('rank_display', list_data)
        self.assertIn('contract_type_display', list_data)
        
        # Verify values are correct
        self.assertEqual(list_data['user_name'], user.get_full_name())
        self.assertEqual(list_data['department_name'], self.department.name)
        self.assertEqual(list_data['rank_display'], teacher.get_rank_display())
        self.assertEqual(list_data['contract_type_display'], teacher.get_contract_type_display())
        
        # Test detail serializer
        detail_serializer = TeacherDetailSerializer(teacher)
        detail_data = detail_serializer.data
        
        # Verify additional readable representations in detail view
        self.assertIn('user_name', detail_data)
        self.assertIn('user_email', detail_data)
        self.assertIn('user_phone', detail_data)
        self.assertIn('department_name', detail_data)
        self.assertIn('department_code', detail_data)
        self.assertIn('faculty_name', detail_data)
    
    @settings(max_examples=10)
    @given(
        employee_id=st.text(min_size=5, max_size=15, alphabet=st.characters(whitelist_categories=('Nd', 'Lu'))),
    )
    def test_property_2_validation_enforcement_duplicate_employee_id(self, employee_id):
        """
        Feature: backend-api-implementation, Property 2: Validation Enforcement
        
        **Validates: Requirements 1.9**
        
        For any invalid input data that violates model constraints or business rules,
        the serializer should reject it and return detailed validation errors.
        
        Test case: Duplicate employee_id should be rejected.
        """
        # Create user and teacher with the employee_id
        user1 = User.objects.create_user(
            username=f"user1_{employee_id}".lower()[:30],
            email=f"user1_{employee_id.lower()}@test.com",
            role=User.Role.TEACHER,
            password="testpass123"
        )
        
        Teacher.objects.create(
            user=user1,
            employee_id=employee_id,
            department=self.department,
            hire_date=date.today()
        )
        
        # Try to create another teacher with the same employee_id
        user2 = User.objects.create_user(
            username=f"user2_{employee_id}".lower()[:30],
            email=f"user2_{employee_id.lower()}@test.com",
            role=User.Role.TEACHER,
            password="testpass123"
        )
        
        data = {
            'user': user2.id,
            'employee_id': employee_id,
            'department': self.department.id,
            'hire_date': date.today().isoformat()
        }
        
        serializer = TeacherCreateSerializer(data=data)
        
        # Should be invalid due to duplicate employee_id
        is_valid = serializer.is_valid()
        self.assertFalse(is_valid)
        
        # Should have employee_id error
        self.assertIn('employee_id', serializer.errors)
    
    @settings(max_examples=10)
    @given(
        first_name=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
        last_name=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
        employee_id=st.text(min_size=5, max_size=15, alphabet=st.characters(whitelist_categories=('Nd', 'Lu'))),
    )
    def test_property_3_computed_properties_inclusion(self, first_name, last_name, employee_id):
        """
        Feature: backend-api-implementation, Property 3: Computed Properties Inclusion
        
        **Validates: Requirements 1.10**
        
        For any model with computed properties (methods decorated with @property),
        the serializer should include those properties as read-only fields in the output.
        """
        # Create user
        user = User.objects.create_user(
            username=f"teacher_{employee_id}".lower()[:30],
            email=f"{employee_id.lower()}@test.com",
            first_name=first_name,
            last_name=last_name,
            role=User.Role.TEACHER,
            password="testpass123"
        )
        
        # Create teacher
        teacher = Teacher.objects.create(
            user=user,
            employee_id=employee_id,
            department=self.department,
            hire_date=date.today()
        )
        
        # Serialize with detail serializer
        serializer = TeacherDetailSerializer(teacher)
        data = serializer.data
        
        # Verify computed properties are included
        self.assertIn('courses_count', data)
        self.assertIn('active_contracts_count', data)
        self.assertIn('rank_display', data)
        self.assertIn('contract_type_display', data)
        
        # Verify computed values are correct
        self.assertEqual(data['courses_count'], teacher.course_assignments.count())
        self.assertEqual(data['active_contracts_count'], teacher.contracts.filter(status='ACTIVE').count())
        self.assertEqual(data['rank_display'], teacher.get_rank_display())
        self.assertEqual(data['contract_type_display'], teacher.get_contract_type_display())


class TeacherCourseSerializerPropertyTests(TestCase):
    """Property tests for TeacherCourse serializers."""
    
    def setUp(self):
        """Set up test data."""
        # Create users with unique usernames
        unique_id = str(uuid.uuid4())[:8]
        self.dean = User.objects.create_user(
            username=f'dean_tc_{unique_id}',
            email=f'dean_tc_{unique_id}@test.com',
            password='testpass123',
            role=User.Role.ADMIN,
            first_name='Dean',
            last_name='Test'
        )
        
        self.teacher_user = User.objects.create_user(
            username=f'teacher_tc_{unique_id}',
            email=f'teacher_tc_{unique_id}@test.com',
            password='testpass123',
            role=User.Role.TEACHER,
            first_name='Teacher',
            last_name='Test'
        )
        
        # Create faculty and department
        self.faculty = Faculty.objects.create(
            name='Test Faculty',
            code=f'TF{unique_id}',
            dean=self.dean
        )
        self.department = Department.objects.create(
            name='Test Department',
            code=f'TD{unique_id}',
            faculty=self.faculty,
            head=self.dean
        )
        
        # Create level and program with unique identifiers
        self.level = Level.objects.create(name=f'L1_{unique_id}', order=1)
        self.program = Program.objects.create(
            name='Test Program',
            code=f'TP{unique_id}',
            department=self.department,
            level=self.level,
            duration_years=3
        )
        
        # Create academic year and semester with unique identifiers
        self.academic_year = AcademicYear.objects.create(
            name=f'2023-2024-{unique_id}',
            start_date=date(2023, 9, 1),
            end_date=date(2024, 6, 30),
            is_current=False
        )
        self.semester = Semester.objects.create(
            academic_year=self.academic_year,
            semester_type='FALL',
            start_date=date(2023, 9, 1),
            end_date=date(2024, 1, 31),
            is_current=False
        )
        
        # Create course with unique code
        self.course = Course.objects.create(
            name='Test Course',
            code=f'TC{unique_id}',
            program=self.program,
            credits=3
        )
        
        # Create teacher with unique employee_id
        self.teacher = Teacher.objects.create(
            user=self.teacher_user,
            employee_id=f'EMP{unique_id}',
            department=self.department,
            hire_date=date.today()
        )
    
    @settings(max_examples=10)
    @given(
        is_primary=st.booleans()
    )
    def test_property_1_foreign_key_representation(self, is_primary):
        """
        Feature: backend-api-implementation, Property 1: Foreign Key Representation
        
        **Validates: Requirements 1.8**
        
        For any model instance with foreign key relationships, when serialized,
        the output should include readable representations of the related objects.
        """
        # Create teacher course assignment
        teacher_course = TeacherCourse.objects.create(
            teacher=self.teacher,
            course=self.course,
            semester=self.semester,
            is_primary=is_primary
        )
        
        # Test list serializer
        list_serializer = TeacherCourseListSerializer(teacher_course)
        list_data = list_serializer.data
        
        # Verify readable representations are included
        self.assertIn('teacher_name', list_data)
        self.assertIn('teacher_employee_id', list_data)
        self.assertIn('course_name', list_data)
        self.assertIn('course_code', list_data)
        self.assertIn('semester_display', list_data)
        
        # Verify values are correct
        self.assertEqual(list_data['teacher_name'], self.teacher.user.get_full_name())
        self.assertEqual(list_data['teacher_employee_id'], self.teacher.employee_id)
        self.assertEqual(list_data['course_name'], self.course.name)
        self.assertEqual(list_data['course_code'], self.course.code)
        
        # Test detail serializer
        detail_serializer = TeacherCourseDetailSerializer(teacher_course)
        detail_data = detail_serializer.data
        
        # Verify additional readable representations in detail view
        self.assertIn('teacher_department', detail_data)
        self.assertIn('course_credits', detail_data)
        self.assertIn('academic_year', detail_data)
    
    @settings(max_examples=10)
    def test_property_2_validation_enforcement_duplicate_assignment(self):
        """
        Feature: backend-api-implementation, Property 2: Validation Enforcement
        
        **Validates: Requirements 1.9**
        
        For any invalid input data that violates model constraints or business rules,
        the serializer should reject it and return detailed validation errors.
        
        Test case: Duplicate teacher course assignment should be rejected.
        """
        # Create a teacher course assignment
        TeacherCourse.objects.create(
            teacher=self.teacher,
            course=self.course,
            semester=self.semester,
            is_primary=True
        )
        
        # Try to create another assignment for the same teacher, course, and semester
        data = {
            'teacher': self.teacher.id,
            'course': self.course.id,
            'semester': self.semester.id,
            'is_primary': False
        }
        
        serializer = TeacherCourseCreateSerializer(data=data)
        
        # Should be invalid due to duplicate assignment
        is_valid = serializer.is_valid()
        self.assertFalse(is_valid)
        
        # Should have teacher error (custom validation in serializer)
        # Note: The error might be in 'teacher' field or 'non_field_errors' depending on validation
        self.assertTrue('teacher' in serializer.errors or 'non_field_errors' in serializer.errors)


class TeacherContractSerializerPropertyTests(TestCase):
    """Property tests for TeacherContract serializers."""
    
    def setUp(self):
        """Set up test data."""
        # Create users with unique usernames
        unique_id = str(uuid.uuid4())[:8]
        self.dean = User.objects.create_user(
            username=f'dean_contract_{unique_id}',
            email=f'dean_contract_{unique_id}@test.com',
            password='testpass123',
            role=User.Role.ADMIN,
            first_name='Dean',
            last_name='Test'
        )
        
        self.teacher_user = User.objects.create_user(
            username=f'teacher_contract_{unique_id}',
            email=f'teacher_contract_{unique_id}@test.com',
            password='testpass123',
            role=User.Role.TEACHER,
            first_name='Teacher',
            last_name='Test'
        )
        
        # Create faculty and department
        self.faculty = Faculty.objects.create(
            name='Test Faculty',
            code=f'TF{unique_id}',
            dean=self.dean
        )
        self.department = Department.objects.create(
            name='Test Department',
            code=f'TD{unique_id}',
            faculty=self.faculty,
            head=self.dean
        )
        
        # Create teacher with unique employee_id
        self.teacher = Teacher.objects.create(
            user=self.teacher_user,
            employee_id=f'EMP{unique_id}',
            department=self.department,
            hire_date=date.today()
        )
    
    @settings(max_examples=10)
    @given(
        contract_number=st.text(min_size=5, max_size=20, alphabet=st.characters(whitelist_categories=('Nd', 'Lu'))),
        base_salary=st.decimals(min_value=1000, max_value=100000, places=2),
        status=st.sampled_from([choice[0] for choice in TeacherContract.ContractStatus.choices]),
    )
    def test_property_1_foreign_key_representation(self, contract_number, base_salary, status):
        """
        Feature: backend-api-implementation, Property 1: Foreign Key Representation
        
        **Validates: Requirements 1.8**
        
        For any model instance with foreign key relationships, when serialized,
        the output should include readable representations of the related objects.
        """
        # Create teacher contract
        contract = TeacherContract.objects.create(
            teacher=self.teacher,
            contract_number=contract_number,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
            base_salary=base_salary,
            status=status
        )
        
        # Test list serializer
        list_serializer = TeacherContractListSerializer(contract)
        list_data = list_serializer.data
        
        # Verify readable representations are included
        self.assertIn('teacher_name', list_data)
        self.assertIn('teacher_employee_id', list_data)
        self.assertIn('status_display', list_data)
        
        # Verify values are correct
        self.assertEqual(list_data['teacher_name'], self.teacher.user.get_full_name())
        self.assertEqual(list_data['teacher_employee_id'], self.teacher.employee_id)
        self.assertEqual(list_data['status_display'], contract.get_status_display())
        
        # Test detail serializer
        detail_serializer = TeacherContractDetailSerializer(contract)
        detail_data = detail_serializer.data
        
        # Verify additional readable representations in detail view
        self.assertIn('teacher_department', detail_data)
    
    @settings(max_examples=10)
    @given(
        contract_number=st.text(min_size=5, max_size=20, alphabet=st.characters(whitelist_categories=('Nd', 'Lu'))),
    )
    def test_property_2_validation_enforcement_duplicate_contract_number(self, contract_number):
        """
        Feature: backend-api-implementation, Property 2: Validation Enforcement
        
        **Validates: Requirements 1.9**
        
        For any invalid input data that violates model constraints or business rules,
        the serializer should reject it and return detailed validation errors.
        
        Test case: Duplicate contract_number should be rejected.
        """
        # Create a contract with the contract_number
        TeacherContract.objects.create(
            teacher=self.teacher,
            contract_number=contract_number,
            start_date=date.today(),
            base_salary=Decimal('50000.00')
        )
        
        # Try to create another contract with the same contract_number
        data = {
            'teacher': self.teacher.id,
            'contract_number': contract_number,
            'start_date': date.today().isoformat(),
            'base_salary': '60000.00'
        }
        
        serializer = TeacherContractCreateSerializer(data=data)
        
        # Should be invalid due to duplicate contract_number
        is_valid = serializer.is_valid()
        self.assertFalse(is_valid)
        
        # Should have contract_number error
        self.assertIn('contract_number', serializer.errors)
    
    @settings(max_examples=10)
    @given(
        contract_number=st.text(min_size=5, max_size=20, alphabet=st.characters(whitelist_categories=('Nd', 'Lu'))),
        days_duration=st.integers(min_value=1, max_value=30)
    )
    def test_property_2_validation_enforcement_invalid_date_range(self, contract_number, days_duration):
        """
        Feature: backend-api-implementation, Property 2: Validation Enforcement
        
        **Validates: Requirements 1.9**
        
        For any invalid input data that violates model constraints or business rules,
        the serializer should reject it and return detailed validation errors.
        
        Test case: End date must be after start date.
        """
        start_date = date.today()
        # Create an invalid end date (before start date)
        end_date = start_date - timedelta(days=days_duration)
        
        # Try to create contract with invalid date range
        data = {
            'teacher': self.teacher.id,
            'contract_number': contract_number,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'base_salary': '50000.00'
        }
        
        serializer = TeacherContractCreateSerializer(data=data)
        
        # Should be invalid due to invalid date range
        is_valid = serializer.is_valid()
        self.assertFalse(is_valid)
        
        # Should have end_date error
        self.assertIn('end_date', serializer.errors)
    
    @settings(max_examples=10)
    @given(
        contract_number=st.text(min_size=5, max_size=20, alphabet=st.characters(whitelist_categories=('Nd', 'Lu'))),
        base_salary=st.decimals(min_value=1000, max_value=100000, places=2),
    )
    def test_property_3_computed_properties_inclusion(self, contract_number, base_salary):
        """
        Feature: backend-api-implementation, Property 3: Computed Properties Inclusion
        
        **Validates: Requirements 1.10**
        
        For any model with computed properties (methods decorated with @property),
        the serializer should include those properties as read-only fields in the output.
        """
        # Create teacher contract
        contract = TeacherContract.objects.create(
            teacher=self.teacher,
            contract_number=contract_number,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
            base_salary=base_salary,
            status='ACTIVE'
        )
        
        # Serialize with detail serializer
        serializer = TeacherContractDetailSerializer(contract)
        data = serializer.data
        
        # Verify computed properties are included
        self.assertIn('status_display', data)
        
        # Verify computed values are correct
        self.assertEqual(data['status_display'], contract.get_status_display())
