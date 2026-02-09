"""
Property-based tests for academics serializers.

These tests verify universal properties that should hold for all valid inputs.
"""

from hypothesis import given, strategies as st, settings
from hypothesis.extra.django import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta, time
from decimal import Decimal
import uuid
from apps.academics.serializers import (
    CourseListSerializer,
    CourseDetailSerializer,
    CourseCreateSerializer,
    ExamListSerializer,
    ExamDetailSerializer,
    ExamCreateSerializer,
    GradeListSerializer,
    GradeDetailSerializer,
    GradeCreateSerializer,
    CourseGradeListSerializer,
    CourseGradeDetailSerializer,
    CourseGradeCreateSerializer,
    ReportCardListSerializer,
    ReportCardDetailSerializer,
)
from apps.academics.models import Course, Exam, Grade, CourseGrade, ReportCard
from apps.university.models import (
    AcademicYear, Semester, Faculty, Department, Level, Program, Classroom
)
from apps.students.models import Student

User = get_user_model()


class CourseSerializerPropertyTests(TestCase):
    """Property tests for Course serializers."""
    
    def setUp(self):
        """Set up test data."""
        # Create users with unique usernames
        unique_id = str(uuid.uuid4())[:8]
        self.dean = User.objects.create_user(
            username=f'dean_course_{unique_id}',
            email=f'dean_course_{unique_id}@test.com',
            password='testpass123',
            role=User.Role.ADMIN,
            first_name='Dean',
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
        
        # Create level and program
        self.level, _ = Level.objects.get_or_create(name='L1', defaults={'order': 1})
        self.program = Program.objects.create(
            name='Test Program',
            code=f'TP{unique_id}',
            department=self.department,
            level=self.level,
            duration_years=3
        )
        
        # Create academic year and semester
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

    
    @settings(max_examples=10)
    @given(
        course_name=st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Zs'))),
        course_code=st.text(min_size=2, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Nd'))),
        credits=st.integers(min_value=1, max_value=10),
        course_type=st.sampled_from([choice[0] for choice in Course.CourseType.choices]),
    )
    def test_property_1_foreign_key_representation(self, course_name, course_code, credits, course_type):
        """
        Feature: backend-api-implementation, Property 1: Foreign Key Representation
        
        **Validates: Requirements 1.8**
        
        For any model instance with foreign key relationships, when serialized,
        the output should include readable representations (names, codes, or display values)
        of the related objects, not just IDs.
        """
        # Create course
        course = Course.objects.create(
            name=course_name[:200],
            code=course_code[:20],
            program=self.program,
            course_type=course_type,
            credits=credits,
            semester=self.semester
        )
        
        # Test list serializer
        list_serializer = CourseListSerializer(course)
        list_data = list_serializer.data
        
        # Verify readable representations are included
        self.assertIn('program_name', list_data)
        self.assertIn('program_code', list_data)
        self.assertIn('course_type_display', list_data)
        self.assertIn('semester_name', list_data)
        
        # Verify values are correct
        self.assertEqual(list_data['program_name'], self.program.name)
        self.assertEqual(list_data['program_code'], self.program.code)
        self.assertEqual(list_data['course_type_display'], course.get_course_type_display())
        
        # Test detail serializer
        detail_serializer = CourseDetailSerializer(course)
        detail_data = detail_serializer.data
        
        # Verify additional readable representations in detail view
        self.assertIn('department_name', detail_data)
        self.assertIn('faculty_name', detail_data)
        self.assertIn('academic_year', detail_data)

    
    @settings(max_examples=10)
    @given(
        course_code=st.text(min_size=2, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Nd'))),
    )
    def test_property_2_validation_enforcement_duplicate_code(self, course_code):
        """
        Feature: backend-api-implementation, Property 2: Validation Enforcement
        
        **Validates: Requirements 1.9**
        
        For any invalid input data that violates model constraints or business rules,
        the serializer should reject it and return detailed validation errors.
        
        Test case: Duplicate course code should be rejected.
        """
        # Create a course with the code
        Course.objects.create(
            name='Test Course',
            code=course_code[:20],
            program=self.program,
            credits=3
        )
        
        # Try to create another course with the same code
        data = {
            'name': 'Another Course',
            'code': course_code[:20],
            'program': self.program.id,
            'credits': 3
        }
        
        serializer = CourseCreateSerializer(data=data)
        
        # Should be invalid due to duplicate code
        is_valid = serializer.is_valid()
        self.assertFalse(is_valid)
        
        # Should have code error
        self.assertIn('code', serializer.errors)

    
    @settings(max_examples=10)
    @given(
        course_name=st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Zs'))),
        course_code=st.text(min_size=2, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Nd'))),
        credits=st.integers(min_value=1, max_value=10),
    )
    def test_property_3_computed_properties_inclusion(self, course_name, course_code, credits):
        """
        Feature: backend-api-implementation, Property 3: Computed Properties Inclusion
        
        **Validates: Requirements 1.10**
        
        For any model with computed properties (methods decorated with @property),
        the serializer should include those properties as read-only fields in the output.
        """
        # Create course
        course = Course.objects.create(
            name=course_name[:200],
            code=course_code[:20],
            program=self.program,
            credits=credits,
            hours_lecture=30,
            hours_practical=15,
            hours_tutorial=10
        )
        
        # Serialize with detail serializer
        serializer = CourseDetailSerializer(course)
        data = serializer.data
        
        # Verify computed properties are included
        self.assertIn('total_hours', data)
        self.assertIn('exams_count', data)
        self.assertIn('students_count', data)
        self.assertIn('prerequisites_count', data)
        
        # Verify computed values are correct
        self.assertEqual(data['total_hours'], course.total_hours)
        self.assertEqual(data['exams_count'], course.exams.count())
        self.assertEqual(data['prerequisites_count'], course.prerequisites.count())


class ExamSerializerPropertyTests(TestCase):
    """Property tests for Exam serializers."""
    
    def setUp(self):
        """Set up test data."""
        # Create users with unique usernames
        unique_id = str(uuid.uuid4())[:8]
        self.dean = User.objects.create_user(
            username=f'dean_exam_{unique_id}',
            email=f'dean_exam_{unique_id}@test.com',
            password='testpass123',
            role=User.Role.ADMIN,
            first_name='Dean',
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
        
        # Create level and program
        self.level, _ = Level.objects.get_or_create(name='L1', defaults={'order': 1})
        self.program = Program.objects.create(
            name='Test Program',
            code=f'TP{unique_id}',
            department=self.department,
            level=self.level,
            duration_years=3
        )
        
        # Create academic year and semester
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
        
        # Create course
        self.course = Course.objects.create(
            name='Test Course',
            code=f'TC{unique_id}',
            program=self.program,
            credits=3
        )
        
        # Create classroom
        self.classroom = Classroom.objects.create(
            name='Room 101',
            code=f'R101{unique_id}',
            capacity=50
        )

    
    @settings(max_examples=10)
    @given(
        exam_type=st.sampled_from([choice[0] for choice in Exam.ExamType.choices]),
        max_score=st.decimals(min_value=10, max_value=100, places=2),
        weight=st.decimals(min_value=Decimal('0.1'), max_value=Decimal('1.0'), places=2),
    )
    def test_property_1_foreign_key_representation(self, exam_type, max_score, weight):
        """
        Feature: backend-api-implementation, Property 1: Foreign Key Representation
        
        **Validates: Requirements 1.8**
        
        For any model instance with foreign key relationships, when serialized,
        the output should include readable representations of the related objects.
        """
        # Create exam
        exam = Exam.objects.create(
            course=self.course,
            exam_type=exam_type,
            semester=self.semester,
            date=date(2023, 10, 15),
            start_time=time(9, 0),
            end_time=time(11, 0),
            classroom=self.classroom,
            max_score=max_score,
            weight=weight
        )
        
        # Test list serializer
        list_serializer = ExamListSerializer(exam)
        list_data = list_serializer.data
        
        # Verify readable representations are included
        self.assertIn('course_name', list_data)
        self.assertIn('course_code', list_data)
        self.assertIn('exam_type_display', list_data)
        self.assertIn('semester_name', list_data)
        self.assertIn('classroom_name', list_data)
        
        # Verify values are correct
        self.assertEqual(list_data['course_name'], self.course.name)
        self.assertEqual(list_data['course_code'], self.course.code)
        self.assertEqual(list_data['exam_type_display'], exam.get_exam_type_display())
        self.assertEqual(list_data['classroom_name'], self.classroom.name)
        
        # Test detail serializer
        detail_serializer = ExamDetailSerializer(exam)
        detail_data = detail_serializer.data
        
        # Verify additional readable representations in detail view
        self.assertIn('program_name', detail_data)
        self.assertIn('academic_year', detail_data)
        self.assertIn('classroom_capacity', detail_data)
        self.assertIn('grades_count', detail_data)

    
    @settings(max_examples=10)
    @given(
        days_offset=st.integers(min_value=1, max_value=30)
    )
    def test_property_2_validation_enforcement_invalid_time_range(self, days_offset):
        """
        Feature: backend-api-implementation, Property 2: Validation Enforcement
        
        **Validates: Requirements 1.9**
        
        For any invalid input data that violates model constraints or business rules,
        the serializer should reject it and return detailed validation errors.
        
        Test case: End time must be after start time.
        """
        # Try to create exam with invalid time range (end before start)
        data = {
            'course': self.course.id,
            'exam_type': 'MIDTERM',
            'semester': self.semester.id,
            'date': (date(2023, 9, 1) + timedelta(days=days_offset)).isoformat(),
            'start_time': '11:00:00',
            'end_time': '09:00:00',  # Before start time
            'max_score': '20.00',
            'weight': '1.00'
        }
        
        serializer = ExamCreateSerializer(data=data)
        
        # Should be invalid due to invalid time range
        is_valid = serializer.is_valid()
        self.assertFalse(is_valid)
        
        # Should have end_time error
        self.assertIn('end_time', serializer.errors)
    
    @settings(max_examples=10)
    def test_property_2_validation_enforcement_date_outside_semester(self):
        """
        Feature: backend-api-implementation, Property 2: Validation Enforcement
        
        **Validates: Requirements 1.9**
        
        Test case: Exam date must be within semester dates.
        """
        # Try to create exam with date outside semester
        data = {
            'course': self.course.id,
            'exam_type': 'FINAL',
            'semester': self.semester.id,
            'date': '2024-06-01',  # Outside semester range
            'start_time': '09:00:00',
            'end_time': '11:00:00',
            'max_score': '20.00',
            'weight': '1.00'
        }
        
        serializer = ExamCreateSerializer(data=data)
        
        # Should be invalid due to date outside semester
        is_valid = serializer.is_valid()
        self.assertFalse(is_valid)
        
        # Should have date error
        self.assertIn('date', serializer.errors)
    
    @settings(max_examples=10)
    @given(
        exam_type=st.sampled_from([choice[0] for choice in Exam.ExamType.choices]),
    )
    def test_property_3_computed_properties_inclusion(self, exam_type):
        """
        Feature: backend-api-implementation, Property 3: Computed Properties Inclusion
        
        **Validates: Requirements 1.10**
        
        For any model with computed properties, the serializer should include
        those properties as read-only fields in the output.
        """
        # Create exam
        exam = Exam.objects.create(
            course=self.course,
            exam_type=exam_type,
            semester=self.semester,
            date=date(2023, 10, 15),
            start_time=time(9, 0),
            end_time=time(11, 0),
            classroom=self.classroom,
            max_score=Decimal('20.00'),
            weight=Decimal('1.00')
        )
        
        # Serialize with detail serializer
        serializer = ExamDetailSerializer(exam)
        data = serializer.data
        
        # Verify computed properties are included
        self.assertIn('grades_count', data)
        
        # Verify computed values are correct
        self.assertEqual(data['grades_count'], exam.grades.count())



class GradeSerializerPropertyTests(TestCase):
    """Property tests for Grade serializers."""
    
    def setUp(self):
        """Set up test data."""
        # Create users with unique usernames
        unique_id = str(uuid.uuid4())[:8]
        self.dean = User.objects.create_user(
            username=f'dean_grade_{unique_id}',
            email=f'dean_grade_{unique_id}@test.com',
            password='testpass123',
            role=User.Role.ADMIN,
            first_name='Dean',
            last_name='Test'
        )
        
        self.teacher_user = User.objects.create_user(
            username=f'teacher_grade_{unique_id}',
            email=f'teacher_grade_{unique_id}@test.com',
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
        
        # Create level and program
        self.level, _ = Level.objects.get_or_create(name='L1', defaults={'order': 1})
        self.program = Program.objects.create(
            name='Test Program',
            code=f'TP{unique_id}',
            department=self.department,
            level=self.level,
            duration_years=3
        )
        
        # Create academic year and semester
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
        
        # Create course
        self.course = Course.objects.create(
            name='Test Course',
            code=f'TC{unique_id}',
            program=self.program,
            credits=3
        )
        
        # Create exam
        self.exam = Exam.objects.create(
            course=self.course,
            exam_type='MIDTERM',
            semester=self.semester,
            date=date(2023, 10, 15),
            start_time=time(9, 0),
            end_time=time(11, 0),
            max_score=Decimal('20.00'),
            weight=Decimal('0.40')
        )
        
        # Create student
        self.student_user = User.objects.create_user(
            username=f'student_grade_{unique_id}',
            email=f'student_grade_{unique_id}@test.com',
            password='testpass123',
            role=User.Role.STUDENT,
            first_name='Student',
            last_name='Test'
        )
        self.student = Student.objects.create(
            user=self.student_user,
            student_id=f'STU{unique_id}',
            program=self.program,
            current_level=self.level,
            enrollment_date=date.today()
        )

    
    @settings(max_examples=10)
    @given(
        score=st.decimals(min_value=0, max_value=20, places=2),
        is_absent=st.booleans(),
    )
    def test_property_1_foreign_key_representation(self, score, is_absent):
        """
        Feature: backend-api-implementation, Property 1: Foreign Key Representation
        
        **Validates: Requirements 1.8**
        
        For any model instance with foreign key relationships, when serialized,
        the output should include readable representations of the related objects.
        """
        # Create grade
        grade = Grade.objects.create(
            student=self.student,
            exam=self.exam,
            score=score if not is_absent else Decimal('0.00'),
            is_absent=is_absent,
            graded_by=self.teacher_user
        )
        
        # Test list serializer
        list_serializer = GradeListSerializer(grade)
        list_data = list_serializer.data
        
        # Verify readable representations are included
        self.assertIn('student_name', list_data)
        self.assertIn('student_matricule', list_data)
        self.assertIn('course_name', list_data)
        self.assertIn('course_code', list_data)
        self.assertIn('exam_type_display', list_data)
        self.assertIn('graded_by_name', list_data)
        
        # Verify values are correct
        self.assertEqual(list_data['student_name'], self.student.user.get_full_name())
        self.assertEqual(list_data['student_matricule'], self.student.student_id)
        self.assertEqual(list_data['course_name'], self.course.name)
        self.assertEqual(list_data['graded_by_name'], self.teacher_user.get_full_name())
        
        # Test detail serializer
        detail_serializer = GradeDetailSerializer(grade)
        detail_data = detail_serializer.data
        
        # Verify additional readable representations in detail view
        self.assertIn('student_program', detail_data)
        self.assertIn('exam_date', detail_data)
        self.assertIn('exam_max_score', detail_data)
        self.assertIn('exam_weight', detail_data)

    
    @settings(max_examples=10)
    @given(
        score=st.decimals(min_value=20.01, max_value=30, places=2),
    )
    def test_property_2_validation_enforcement_score_exceeds_max(self, score):
        """
        Feature: backend-api-implementation, Property 2: Validation Enforcement
        
        **Validates: Requirements 1.9**
        
        For any invalid input data that violates model constraints or business rules,
        the serializer should reject it and return detailed validation errors.
        
        Test case: Score cannot exceed exam's max_score.
        """
        # Try to create grade with score exceeding max_score
        data = {
            'student': self.student.id,
            'exam': self.exam.id,
            'score': str(score),
            'graded_by': self.teacher_user.id
        }
        
        serializer = GradeCreateSerializer(data=data)
        
        # Should be invalid due to score exceeding max_score
        is_valid = serializer.is_valid()
        self.assertFalse(is_valid)
        
        # Should have score error
        self.assertIn('score', serializer.errors)
    
    @settings(max_examples=10)
    @given(
        score=st.decimals(min_value=0, max_value=20, places=2),
    )
    def test_property_2_validation_enforcement_duplicate_grade(self, score):
        """
        Feature: backend-api-implementation, Property 2: Validation Enforcement
        
        **Validates: Requirements 1.9**
        
        Test case: Duplicate grade for same student and exam should be rejected.
        """
        # Create a grade
        Grade.objects.create(
            student=self.student,
            exam=self.exam,
            score=score,
            graded_by=self.teacher_user
        )
        
        # Try to create another grade for the same student and exam
        data = {
            'student': self.student.id,
            'exam': self.exam.id,
            'score': str(score),
            'graded_by': self.teacher_user.id
        }
        
        serializer = GradeCreateSerializer(data=data)
        
        # Should be invalid due to duplicate grade
        is_valid = serializer.is_valid()
        self.assertFalse(is_valid)
        
        # Should have student error
        self.assertIn('student', serializer.errors)
    
    @settings(max_examples=10)
    @given(
        score=st.decimals(min_value=0, max_value=20, places=2),
    )
    def test_property_3_computed_properties_inclusion(self, score):
        """
        Feature: backend-api-implementation, Property 3: Computed Properties Inclusion
        
        **Validates: Requirements 1.10**
        
        For any model with computed properties, the serializer should include
        those properties as read-only fields in the output.
        """
        # Create grade
        grade = Grade.objects.create(
            student=self.student,
            exam=self.exam,
            score=score,
            graded_by=self.teacher_user
        )
        
        # Serialize with detail serializer
        serializer = GradeDetailSerializer(grade)
        data = serializer.data
        
        # Verify computed properties are included
        self.assertIn('percentage', data)
        
        # Verify computed values are correct
        expected_percentage = (score / self.exam.max_score) * 100
        self.assertAlmostEqual(float(data['percentage']), float(expected_percentage), places=2)



class CourseGradeSerializerPropertyTests(TestCase):
    """Property tests for CourseGrade serializers."""
    
    def setUp(self):
        """Set up test data."""
        # Create users with unique usernames
        unique_id = str(uuid.uuid4())[:8]
        self.dean = User.objects.create_user(
            username=f'dean_cgrade_{unique_id}',
            email=f'dean_cgrade_{unique_id}@test.com',
            password='testpass123',
            role=User.Role.ADMIN,
            first_name='Dean',
            last_name='Test'
        )
        
        self.teacher_user = User.objects.create_user(
            username=f'teacher_cgrade_{unique_id}',
            email=f'teacher_cgrade_{unique_id}@test.com',
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
        
        # Create level and program
        self.level, _ = Level.objects.get_or_create(name='L1', defaults={'order': 1})
        self.program = Program.objects.create(
            name='Test Program',
            code=f'TP{unique_id}',
            department=self.department,
            level=self.level,
            duration_years=3
        )
        
        # Create academic year and semester
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
        
        # Create course
        self.course = Course.objects.create(
            name='Test Course',
            code=f'TC{unique_id}',
            program=self.program,
            credits=3
        )
        
        # Create student
        self.student_user = User.objects.create_user(
            username=f'student_cgrade_{unique_id}',
            email=f'student_cgrade_{unique_id}@test.com',
            password='testpass123',
            role=User.Role.STUDENT,
            first_name='Student',
            last_name='Test'
        )
        self.student = Student.objects.create(
            user=self.student_user,
            student_id=f'STU{unique_id}',
            program=self.program,
            current_level=self.level,
            enrollment_date=date.today()
        )

    
    @settings(max_examples=10)
    @given(
        final_score=st.decimals(min_value=0, max_value=20, places=2),
        is_validated=st.booleans(),
    )
    def test_property_1_foreign_key_representation(self, final_score, is_validated):
        """
        Feature: backend-api-implementation, Property 1: Foreign Key Representation
        
        **Validates: Requirements 1.8**
        
        For any model instance with foreign key relationships, when serialized,
        the output should include readable representations of the related objects.
        """
        # Create course grade
        course_grade = CourseGrade.objects.create(
            student=self.student,
            course=self.course,
            semester=self.semester,
            final_score=final_score,
            is_validated=is_validated,
            validated_by=self.teacher_user if is_validated else None
        )
        
        # Test list serializer
        list_serializer = CourseGradeListSerializer(course_grade)
        list_data = list_serializer.data
        
        # Verify readable representations are included
        self.assertIn('student_name', list_data)
        self.assertIn('student_matricule', list_data)
        self.assertIn('course_name', list_data)
        self.assertIn('course_code', list_data)
        self.assertIn('semester_name', list_data)
        
        # Verify values are correct
        self.assertEqual(list_data['student_name'], self.student.user.get_full_name())
        self.assertEqual(list_data['student_matricule'], self.student.student_id)
        self.assertEqual(list_data['course_name'], self.course.name)
        self.assertEqual(list_data['course_code'], self.course.code)
        
        # Test detail serializer
        detail_serializer = CourseGradeDetailSerializer(course_grade)
        detail_data = detail_serializer.data
        
        # Verify additional readable representations in detail view
        self.assertIn('student_program', detail_data)
        self.assertIn('course_credits', detail_data)
        self.assertIn('course_coefficient', detail_data)
        self.assertIn('academic_year', detail_data)
    
    @settings(max_examples=10)
    @given(
        final_score=st.decimals(min_value=0, max_value=20, places=2),
    )
    def test_property_2_validation_enforcement_duplicate_course_grade(self, final_score):
        """
        Feature: backend-api-implementation, Property 2: Validation Enforcement
        
        **Validates: Requirements 1.9**
        
        For any invalid input data that violates model constraints or business rules,
        the serializer should reject it and return detailed validation errors.
        
        Test case: Duplicate course grade for same student, course, and semester should be rejected.
        """
        # Create a course grade
        CourseGrade.objects.create(
            student=self.student,
            course=self.course,
            semester=self.semester,
            final_score=final_score
        )
        
        # Try to create another course grade for the same student, course, and semester
        data = {
            'student': self.student.id,
            'course': self.course.id,
            'semester': self.semester.id,
            'final_score': str(final_score)
        }
        
        serializer = CourseGradeCreateSerializer(data=data)
        
        # Should be invalid due to duplicate course grade
        is_valid = serializer.is_valid()
        self.assertFalse(is_valid)
        
        # Should have student error
        self.assertIn('student', serializer.errors)
    
    @settings(max_examples=10)
    @given(
        final_score=st.decimals(min_value=0, max_value=20, places=2),
    )
    def test_property_3_computed_properties_inclusion(self, final_score):
        """
        Feature: backend-api-implementation, Property 3: Computed Properties Inclusion
        
        **Validates: Requirements 1.10**
        
        For any model with computed properties, the serializer should include
        those properties as read-only fields in the output.
        """
        # Create course grade
        course_grade = CourseGrade.objects.create(
            student=self.student,
            course=self.course,
            semester=self.semester,
            final_score=final_score
        )
        
        # Serialize with detail serializer
        serializer = CourseGradeDetailSerializer(course_grade)
        data = serializer.data
        
        # Verify grade_letter is included (automatically calculated on save)
        self.assertIn('grade_letter', data)
        
        # Verify grade_letter is correct based on final_score
        if final_score >= 16:
            self.assertEqual(data['grade_letter'], 'A')
        elif final_score >= 14:
            self.assertEqual(data['grade_letter'], 'B')
        elif final_score >= 12:
            self.assertEqual(data['grade_letter'], 'C')
        elif final_score >= 10:
            self.assertEqual(data['grade_letter'], 'D')
        else:
            self.assertEqual(data['grade_letter'], 'F')



class ReportCardSerializerPropertyTests(TestCase):
    """Property tests for ReportCard serializers."""
    
    def setUp(self):
        """Set up test data."""
        # Create users with unique usernames
        unique_id = str(uuid.uuid4())[:8]
        self.dean = User.objects.create_user(
            username=f'dean_report_{unique_id}',
            email=f'dean_report_{unique_id}@test.com',
            password='testpass123',
            role=User.Role.ADMIN,
            first_name='Dean',
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
        
        # Create level and program
        self.level, _ = Level.objects.get_or_create(name='L1', defaults={'order': 1})
        self.program = Program.objects.create(
            name='Test Program',
            code=f'TP{unique_id}',
            department=self.department,
            level=self.level,
            duration_years=3
        )
        
        # Create academic year and semester
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
        
        # Create student
        self.student_user = User.objects.create_user(
            username=f'student_report_{unique_id}',
            email=f'student_report_{unique_id}@test.com',
            password='testpass123',
            role=User.Role.STUDENT,
            first_name='Student',
            last_name='Test'
        )
        self.student = Student.objects.create(
            user=self.student_user,
            student_id=f'STU{unique_id}',
            program=self.program,
            current_level=self.level,
            enrollment_date=date.today()
        )
    
    @settings(max_examples=10)
    @given(
        gpa=st.decimals(min_value=0, max_value=20, places=2),
        total_credits=st.integers(min_value=0, max_value=60),
        credits_earned=st.integers(min_value=0, max_value=60),
        is_published=st.booleans(),
    )
    def test_property_1_foreign_key_representation(self, gpa, total_credits, credits_earned, is_published):
        """
        Feature: backend-api-implementation, Property 1: Foreign Key Representation
        
        **Validates: Requirements 1.8**
        
        For any model instance with foreign key relationships, when serialized,
        the output should include readable representations of the related objects.
        """
        # Ensure credits_earned doesn't exceed total_credits
        if credits_earned > total_credits:
            credits_earned = total_credits
        
        # Create report card
        report_card = ReportCard.objects.create(
            student=self.student,
            semester=self.semester,
            gpa=gpa,
            total_credits=total_credits,
            credits_earned=credits_earned,
            is_published=is_published,
            generated_by=self.dean
        )
        
        # Test list serializer
        list_serializer = ReportCardListSerializer(report_card)
        list_data = list_serializer.data
        
        # Verify readable representations are included
        self.assertIn('student_name', list_data)
        self.assertIn('student_matricule', list_data)
        self.assertIn('program_name', list_data)
        self.assertIn('semester_name', list_data)
        self.assertIn('academic_year', list_data)
        self.assertIn('generated_by_name', list_data)
        
        # Verify values are correct
        self.assertEqual(list_data['student_name'], self.student.user.get_full_name())
        self.assertEqual(list_data['student_matricule'], self.student.student_id)
        self.assertEqual(list_data['program_name'], self.program.name)
        self.assertEqual(list_data['generated_by_name'], self.dean.get_full_name())
        
        # Test detail serializer
        detail_serializer = ReportCardDetailSerializer(report_card)
        detail_data = detail_serializer.data
        
        # Verify additional readable representations in detail view
        self.assertIn('student_email', detail_data)
        self.assertIn('student_program', detail_data)
        self.assertIn('program_code', detail_data)
        self.assertIn('student_level', detail_data)
        self.assertIn('course_grades_count', detail_data)
    
    @settings(max_examples=10)
    @given(
        gpa=st.decimals(min_value=0, max_value=20, places=2),
    )
    def test_property_3_computed_properties_inclusion(self, gpa):
        """
        Feature: backend-api-implementation, Property 3: Computed Properties Inclusion
        
        **Validates: Requirements 1.10**
        
        For any model with computed properties, the serializer should include
        those properties as read-only fields in the output.
        """
        # Create report card
        report_card = ReportCard.objects.create(
            student=self.student,
            semester=self.semester,
            gpa=gpa,
            total_credits=30,
            credits_earned=24,
            generated_by=self.dean
        )
        
        # Serialize with detail serializer
        serializer = ReportCardDetailSerializer(report_card)
        data = serializer.data
        
        # Verify computed properties are included
        self.assertIn('course_grades_count', data)
        
        # Verify computed values are correct
        expected_count = CourseGrade.objects.filter(
            student=self.student,
            semester=self.semester,
            is_validated=True
        ).count()
        self.assertEqual(data['course_grades_count'], expected_count)
