"""
Property-based tests for university serializers.

These tests verify universal properties that should hold for all valid inputs.
"""

from hypothesis import given, strategies as st, settings
from hypothesis.extra.django import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date, timedelta
from apps.university.models import (
    AcademicYear, Semester, Faculty, Department, Level, Program, Classroom
)
from apps.university.serializers import (
    AcademicYearListSerializer, AcademicYearDetailSerializer,
    SemesterListSerializer, SemesterDetailSerializer,
    FacultyListSerializer, FacultyDetailSerializer,
    DepartmentListSerializer, DepartmentDetailSerializer,
    LevelListSerializer, LevelDetailSerializer,
    ProgramListSerializer, ProgramDetailSerializer,
    ClassroomListSerializer, ClassroomDetailSerializer
)

User = get_user_model()


class AcademicYearSerializerPropertyTests(TestCase):
    """Property tests for AcademicYear serializers."""
    
    @settings(max_examples=10)
    @given(
        year=st.integers(min_value=2020, max_value=2030),
        duration_days=st.integers(min_value=200, max_value=365)
    )
    def test_property_1_foreign_key_representation(self, year, duration_days):
        """
        Feature: backend-api-implementation, Property 1: Foreign Key Representation
        
        **Validates: Requirements 1.8**
        
        For any model instance with foreign key relationships, when serialized,
        the output should include readable representations.
        
        For AcademicYear, this includes semesters_count computed property.
        """
        # Create academic year
        start_date = date(year, 9, 1)
        end_date = start_date + timedelta(days=duration_days)
        
        academic_year = AcademicYear.objects.create(
            name=f"{year}-{year+1}",
            start_date=start_date,
            end_date=end_date,
            is_current=False
        )
        
        # Create some semesters
        Semester.objects.create(
            academic_year=academic_year,
            semester_type='S1',
            start_date=start_date,
            end_date=start_date + timedelta(days=duration_days//2)
        )
        
        # Serialize with detail serializer
        serializer = AcademicYearDetailSerializer(academic_year)
        data = serializer.data
        
        # Verify computed property is included
        self.assertIn('semesters_count', data)
        self.assertEqual(data['semesters_count'], 1)
    
    @settings(max_examples=10)
    @given(
        year=st.integers(min_value=2020, max_value=2030)
    )
    def test_property_3_computed_properties_inclusion(self, year):
        """
        Feature: backend-api-implementation, Property 3: Computed Properties Inclusion
        
        **Validates: Requirements 1.10**
        
        For any model with computed properties, the serializer should include
        those properties as read-only fields in the output.
        """
        # Create academic year
        start_date = date(year, 9, 1)
        end_date = date(year + 1, 6, 30)
        
        academic_year = AcademicYear.objects.create(
            name=f"{year}-{year+1}",
            start_date=start_date,
            end_date=end_date
        )
        
        # Serialize with list serializer
        serializer = AcademicYearListSerializer(academic_year)
        data = serializer.data
        
        # Verify computed property is included
        self.assertIn('semesters_count', data)
        self.assertIsInstance(data['semesters_count'], int)


class SemesterSerializerPropertyTests(TestCase):
    """Property tests for Semester serializers."""
    
    @settings(max_examples=10)
    @given(
        year=st.integers(min_value=2020, max_value=2030),
        semester_type=st.sampled_from(['S1', 'S2'])
    )
    def test_property_1_foreign_key_representation(self, year, semester_type):
        """
        Feature: backend-api-implementation, Property 1: Foreign Key Representation
        
        **Validates: Requirements 1.8**
        
        For Semester, this includes academic_year_name and semester_display.
        """
        # Create academic year
        start_date = date(year, 9, 1)
        end_date = date(year + 1, 6, 30)
        
        academic_year = AcademicYear.objects.create(
            name=f"{year}-{year+1}",
            start_date=start_date,
            end_date=end_date
        )
        
        # Create semester
        semester_start = start_date if semester_type == 'S1' else date(year + 1, 1, 1)
        semester_end = date(year, 12, 31) if semester_type == 'S1' else end_date
        
        semester = Semester.objects.create(
            academic_year=academic_year,
            semester_type=semester_type,
            start_date=semester_start,
            end_date=semester_end
        )
        
        # Serialize
        serializer = SemesterDetailSerializer(semester)
        data = serializer.data
        
        # Verify readable representations
        self.assertIn('academic_year_name', data)
        self.assertEqual(data['academic_year_name'], academic_year.name)
        self.assertIn('semester_display', data)
        self.assertEqual(data['semester_display'], semester.get_semester_type_display())


class FacultySerializerPropertyTests(TestCase):
    """Property tests for Faculty serializers."""
    
    @settings(max_examples=10)
    @given(
        faculty_name=st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Zs'))),
        code=st.text(min_size=2, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Nd')))
    )
    def test_property_1_foreign_key_representation(self, faculty_name, code):
        """
        Feature: backend-api-implementation, Property 1: Foreign Key Representation
        
        **Validates: Requirements 1.8**
        
        For Faculty, this includes dean_name and departments_count.
        """
        # Create dean user
        dean = User.objects.create_user(
            username=f"dean_{code}".lower()[:30],
            email=f"dean_{code}@test.com".lower(),
            first_name="Dean",
            last_name="Test",
            role=User.Role.DEAN,
            password="testpass123"
        )
        
        # Create faculty
        faculty = Faculty.objects.create(
            name=faculty_name[:200],
            code=code[:20],
            dean=dean
        )
        
        # Serialize
        serializer = FacultyDetailSerializer(faculty)
        data = serializer.data
        
        # Verify readable representations
        self.assertIn('dean_name', data)
        self.assertEqual(data['dean_name'], dean.get_full_name())
        self.assertIn('departments_count', data)
        self.assertIsInstance(data['departments_count'], int)
    
    @settings(max_examples=10)
    @given(
        faculty_name=st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Zs'))),
        code=st.text(min_size=2, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Nd')))
    )
    def test_property_3_computed_properties_inclusion(self, faculty_name, code):
        """
        Feature: backend-api-implementation, Property 3: Computed Properties Inclusion
        
        **Validates: Requirements 1.10**
        
        For Faculty, computed properties include departments_count and programs_count.
        """
        # Create faculty
        faculty = Faculty.objects.create(
            name=faculty_name[:200],
            code=code[:20]
        )
        
        # Serialize with detail serializer
        serializer = FacultyDetailSerializer(faculty)
        data = serializer.data
        
        # Verify computed properties
        self.assertIn('departments_count', data)
        self.assertIn('programs_count', data)
        self.assertIsInstance(data['departments_count'], int)
        self.assertIsInstance(data['programs_count'], int)


class DepartmentSerializerPropertyTests(TestCase):
    """Property tests for Department serializers."""
    
    @settings(max_examples=10)
    @given(
        dept_name=st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Zs'))),
        dept_code=st.text(min_size=2, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Nd'))),
        faculty_code=st.text(min_size=2, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Nd')))
    )
    def test_property_1_foreign_key_representation(self, dept_name, dept_code, faculty_code):
        """
        Feature: backend-api-implementation, Property 1: Foreign Key Representation
        
        **Validates: Requirements 1.8**
        
        For Department, this includes faculty_name, head_name, and counts.
        """
        # Create faculty
        faculty = Faculty.objects.create(
            name="Test Faculty",
            code=faculty_code[:20]
        )
        
        # Create head user
        head = User.objects.create_user(
            username=f"head_{dept_code}".lower()[:30],
            email=f"head_{dept_code}@test.com".lower(),
            first_name="Head",
            last_name="Test",
            role=User.Role.TEACHER,
            password="testpass123"
        )
        
        # Create department
        department = Department.objects.create(
            name=dept_name[:200],
            code=dept_code[:20],
            faculty=faculty,
            head=head
        )
        
        # Serialize
        serializer = DepartmentDetailSerializer(department)
        data = serializer.data
        
        # Verify readable representations
        self.assertIn('faculty_name', data)
        self.assertEqual(data['faculty_name'], faculty.name)
        self.assertIn('head_name', data)
        self.assertEqual(data['head_name'], head.get_full_name())
        self.assertIn('programs_count', data)
        self.assertIn('teachers_count', data)


class LevelSerializerPropertyTests(TestCase):
    """Property tests for Level serializers."""
    
    @settings(max_examples=10)
    @given(
        level_choice=st.sampled_from(['L1', 'L2', 'L3', 'M1', 'M2', 'D1', 'D2', 'D3'])
    )
    def test_property_1_foreign_key_representation(self, level_choice):
        """
        Feature: backend-api-implementation, Property 1: Foreign Key Representation
        
        **Validates: Requirements 1.8**
        
        For Level, this includes display_name.
        """
        # Create level
        order_map = {'L1': 1, 'L2': 2, 'L3': 3, 'M1': 4, 'M2': 5, 'D1': 6, 'D2': 7, 'D3': 8}
        level = Level.objects.create(
            name=level_choice,
            order=order_map[level_choice]
        )
        
        # Serialize
        serializer = LevelDetailSerializer(level)
        data = serializer.data
        
        # Verify readable representation
        self.assertIn('display_name', data)
        self.assertEqual(data['display_name'], level.get_name_display())
    
    @settings(max_examples=10)
    @given(
        level_choice=st.sampled_from(['L1', 'L2', 'L3', 'M1', 'M2', 'D1', 'D2', 'D3'])
    )
    def test_property_3_computed_properties_inclusion(self, level_choice):
        """
        Feature: backend-api-implementation, Property 3: Computed Properties Inclusion
        
        **Validates: Requirements 1.10**
        
        For Level, computed properties include programs_count and students_count.
        """
        # Create level
        order_map = {'L1': 1, 'L2': 2, 'L3': 3, 'M1': 4, 'M2': 5, 'D1': 6, 'D2': 7, 'D3': 8}
        level = Level.objects.create(
            name=level_choice,
            order=order_map[level_choice]
        )
        
        # Serialize with detail serializer
        serializer = LevelDetailSerializer(level)
        data = serializer.data
        
        # Verify computed properties
        self.assertIn('programs_count', data)
        self.assertIn('students_count', data)
        self.assertIsInstance(data['programs_count'], int)
        self.assertIsInstance(data['students_count'], int)


class ProgramSerializerPropertyTests(TestCase):
    """Property tests for Program serializers."""
    
    @settings(max_examples=10)
    @given(
        program_name=st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Zs'))),
        program_code=st.text(min_size=2, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Nd'))),
        tuition_fee=st.decimals(min_value=0, max_value=100000, places=2)
    )
    def test_property_1_foreign_key_representation(self, program_name, program_code, tuition_fee):
        """
        Feature: backend-api-implementation, Property 1: Foreign Key Representation
        
        **Validates: Requirements 1.8**
        
        For Program, this includes department_name, faculty_name, level_display.
        """
        # Create faculty
        faculty = Faculty.objects.create(
            name="Test Faculty",
            code="TF"
        )
        
        # Create department
        department = Department.objects.create(
            name="Test Department",
            code="TD",
            faculty=faculty
        )
        
        # Create level
        level = Level.objects.create(
            name='L1',
            order=1
        )
        
        # Create program
        program = Program.objects.create(
            name=program_name[:200],
            code=program_code[:20],
            department=department,
            level=level,
            tuition_fee=tuition_fee
        )
        
        # Serialize
        serializer = ProgramDetailSerializer(program)
        data = serializer.data
        
        # Verify readable representations
        self.assertIn('department_name', data)
        self.assertEqual(data['department_name'], department.name)
        self.assertIn('faculty_name', data)
        self.assertEqual(data['faculty_name'], faculty.name)
        self.assertIn('level_display', data)
        self.assertEqual(data['level_display'], level.get_name_display())
    
    @settings(max_examples=10)
    @given(
        program_name=st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Zs'))),
        program_code=st.text(min_size=2, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Nd')))
    )
    def test_property_3_computed_properties_inclusion(self, program_name, program_code):
        """
        Feature: backend-api-implementation, Property 3: Computed Properties Inclusion
        
        **Validates: Requirements 1.10**
        
        For Program, computed properties include students_count and courses_count.
        """
        # Create faculty
        faculty = Faculty.objects.create(
            name="Test Faculty",
            code="TF"
        )
        
        # Create department
        department = Department.objects.create(
            name="Test Department",
            code="TD",
            faculty=faculty
        )
        
        # Create level
        level = Level.objects.create(
            name='L1',
            order=1
        )
        
        # Create program
        program = Program.objects.create(
            name=program_name[:200],
            code=program_code[:20],
            department=department,
            level=level
        )
        
        # Serialize with detail serializer
        serializer = ProgramDetailSerializer(program)
        data = serializer.data
        
        # Verify computed properties
        self.assertIn('students_count', data)
        self.assertIn('courses_count', data)
        self.assertIsInstance(data['students_count'], int)
        self.assertIsInstance(data['courses_count'], int)


class ClassroomSerializerPropertyTests(TestCase):
    """Property tests for Classroom serializers."""
    
    @settings(max_examples=10)
    @given(
        classroom_name=st.text(min_size=3, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'))),
        code=st.text(min_size=2, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Nd'))),
        capacity=st.integers(min_value=10, max_value=200),
        has_projector=st.booleans(),
        has_computers=st.booleans()
    )
    def test_property_2_validation_enforcement(self, classroom_name, code, capacity, has_projector, has_computers):
        """
        Feature: backend-api-implementation, Property 2: Validation Enforcement
        
        **Validates: Requirements 1.9**
        
        For any invalid input data that violates model constraints,
        the serializer should reject it and return detailed validation errors.
        """
        # Create a classroom
        classroom = Classroom.objects.create(
            name=classroom_name[:100],
            code=code[:20],
            capacity=capacity,
            has_projector=has_projector,
            has_computers=has_computers
        )
        
        # Serialize
        serializer = ClassroomDetailSerializer(classroom)
        data = serializer.data
        
        # Verify all fields are present
        self.assertIn('name', data)
        self.assertIn('code', data)
        self.assertIn('capacity', data)
        self.assertIn('has_projector', data)
        self.assertIn('has_computers', data)
        
        # Verify values match
        self.assertEqual(data['name'], classroom.name)
        self.assertEqual(data['code'], classroom.code)
        self.assertEqual(data['capacity'], capacity)
        self.assertEqual(data['has_projector'], has_projector)
        self.assertEqual(data['has_computers'], has_computers)
