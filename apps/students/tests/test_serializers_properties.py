"""
Property-based tests for students serializers.

These tests verify universal properties that should hold for all valid inputs.
"""

from hypothesis import given, strategies as st, settings, assume
from hypothesis.extra.django import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta
import uuid
from apps.students.serializers import (
    StudentListSerializer,
    StudentDetailSerializer,
    StudentCreateSerializer,
    EnrollmentListSerializer,
    EnrollmentDetailSerializer,
    EnrollmentCreateSerializer,
    AttendanceListSerializer,
    AttendanceDetailSerializer,
    AttendanceCreateSerializer,
)
from apps.students.models import Student, Enrollment, Attendance
from apps.university.models import (
    AcademicYear, Semester, Faculty, Department, Level, Program
)
from apps.scheduling.models import TimeSlot, Schedule, CourseSession
from apps.academics.models import Course

User = get_user_model()


class StudentSerializerPropertyTests(TestCase):
    """Property tests for Student serializers."""
    
    def setUp(self):
        """Set up test data."""
        # Create faculty with unique username
        unique_id = str(uuid.uuid4())[:8]
        self.dean = User.objects.create_user(
            username=f'dean_student_{unique_id}',
            email=f'dean_student_{unique_id}@test.com',
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
        
        # Create or get level
        self.level, _ = Level.objects.get_or_create(
            name='L1',
            defaults={'order': 1}
        )
        
        # Create program
        self.program = Program.objects.create(
            name='Test Program',
            code=f'TP{unique_id}',
            department=self.department,
            level=self.level,
            duration_years=3
        )
    
    @settings(max_examples=10)
    @given(
        first_name=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
        last_name=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
        student_id=st.text(min_size=5, max_size=15, alphabet=st.characters(whitelist_categories=('Nd', 'Lu'))),
    )
    def test_property_1_foreign_key_representation(self, first_name, last_name, student_id):
        """
        Feature: backend-api-implementation, Property 1: Foreign Key Representation
        
        **Validates: Requirements 1.8**
        
        For any model instance with foreign key relationships, when serialized,
        the output should include readable representations (names, codes, or display values)
        of the related objects, not just IDs.
        """
        # Create user
        user = User.objects.create_user(
            username=f"student_{student_id}".lower()[:30],
            email=f"{student_id.lower()}@test.com",
            first_name=first_name,
            last_name=last_name,
            role=User.Role.STUDENT,
            password="testpass123"
        )
        
        # Create student
        student = Student.objects.create(
            user=user,
            student_id=student_id,
            program=self.program,
            current_level=self.level,
            enrollment_date=date.today()
        )
        
        # Test list serializer
        list_serializer = StudentListSerializer(student)
        list_data = list_serializer.data
        
        # Verify readable representations are included
        self.assertIn('user_name', list_data)
        self.assertIn('program_name', list_data)
        self.assertIn('level_display', list_data)
        
        # Verify values are correct
        self.assertEqual(list_data['user_name'], user.get_full_name())
        self.assertEqual(list_data['program_name'], self.program.name)
        self.assertEqual(list_data['level_display'], self.level.get_name_display())
        
        # Test detail serializer
        detail_serializer = StudentDetailSerializer(student)
        detail_data = detail_serializer.data
        
        # Verify additional readable representations in detail view
        self.assertIn('user_name', detail_data)
        self.assertIn('user_email', detail_data)
        self.assertIn('program_name', detail_data)
        self.assertIn('program_code', detail_data)
        self.assertIn('department_name', detail_data)
        self.assertIn('faculty_name', detail_data)
    
    @settings(max_examples=10)
    @given(
        student_id=st.text(min_size=5, max_size=15, alphabet=st.characters(whitelist_categories=('Nd', 'Lu'))),
    )
    def test_property_2_validation_enforcement_duplicate_student_id(self, student_id):
        """
        Feature: backend-api-implementation, Property 2: Validation Enforcement
        
        **Validates: Requirements 1.9**
        
        For any invalid input data that violates model constraints or business rules,
        the serializer should reject it and return detailed validation errors.
        
        Test case: Duplicate student_id should be rejected.
        """
        # Create user and student with the student_id
        user1 = User.objects.create_user(
            username=f"user1_{student_id}".lower()[:30],
            email=f"user1_{student_id.lower()}@test.com",
            role=User.Role.STUDENT,
            password="testpass123"
        )
        
        Student.objects.create(
            user=user1,
            student_id=student_id,
            program=self.program,
            current_level=self.level,
            enrollment_date=date.today()
        )
        
        # Try to create another student with the same student_id
        user2 = User.objects.create_user(
            username=f"user2_{student_id}".lower()[:30],
            email=f"user2_{student_id.lower()}@test.com",
            role=User.Role.STUDENT,
            password="testpass123"
        )
        
        data = {
            'user': user2.id,
            'student_id': student_id,
            'program': self.program.id,
            'current_level': self.level.id,
            'enrollment_date': date.today().isoformat()
        }
        
        serializer = StudentCreateSerializer(data=data)
        
        # Should be invalid due to duplicate student_id
        is_valid = serializer.is_valid()
        self.assertFalse(is_valid)
        
        # Should have student_id error
        self.assertIn('student_id', serializer.errors)
    
    @settings(max_examples=10)
    @given(
        student_id=st.text(min_size=5, max_size=15, alphabet=st.characters(whitelist_categories=('Nd', 'Lu'))),
    )
    def test_property_2_validation_enforcement_program_level_mismatch(self, student_id):
        """
        Feature: backend-api-implementation, Property 2: Validation Enforcement
        
        **Validates: Requirements 1.9**
        
        For any invalid input data that violates model constraints or business rules,
        the serializer should reject it and return detailed validation errors.
        
        Test case: Program and level must be compatible.
        """
        # Create or get a different level
        different_level, _ = Level.objects.get_or_create(
            name='L2',
            defaults={'order': 2}
        )
        
        # Create user
        user = User.objects.create_user(
            username=f"student_{student_id}".lower()[:30],
            email=f"{student_id.lower()}@test.com",
            role=User.Role.STUDENT,
            password="testpass123"
        )
        
        # Try to create student with mismatched program and level
        data = {
            'user': user.id,
            'student_id': student_id,
            'program': self.program.id,  # Program is for L1
            'current_level': different_level.id,  # But level is L2
            'enrollment_date': date.today().isoformat()
        }
        
        serializer = StudentCreateSerializer(data=data)
        
        # Should be invalid due to program/level mismatch
        is_valid = serializer.is_valid()
        self.assertFalse(is_valid)
        
        # Should have current_level error
        self.assertIn('current_level', serializer.errors)
    
    @settings(max_examples=10)
    @given(
        first_name=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
        last_name=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
        student_id=st.text(min_size=5, max_size=15, alphabet=st.characters(whitelist_categories=('Nd', 'Lu'))),
    )
    def test_property_3_computed_properties_inclusion(self, first_name, last_name, student_id):
        """
        Feature: backend-api-implementation, Property 3: Computed Properties Inclusion
        
        **Validates: Requirements 1.10**
        
        For any model with computed properties (methods decorated with @property),
        the serializer should include those properties as read-only fields in the output.
        """
        # Create user
        user = User.objects.create_user(
            username=f"student_{student_id}".lower()[:30],
            email=f"{student_id.lower()}@test.com",
            first_name=first_name,
            last_name=last_name,
            role=User.Role.STUDENT,
            password="testpass123"
        )
        
        # Create student
        student = Student.objects.create(
            user=user,
            student_id=student_id,
            program=self.program,
            current_level=self.level,
            enrollment_date=date.today()
        )
        
        # Serialize with detail serializer
        serializer = StudentDetailSerializer(student)
        data = serializer.data
        
        # Verify computed properties are included
        self.assertIn('enrollments_count', data)
        self.assertIn('status_display', data)
        
        # Verify computed values are correct
        self.assertEqual(data['enrollments_count'], student.enrollments.count())
        self.assertEqual(data['status_display'], student.get_status_display())


class EnrollmentSerializerPropertyTests(TestCase):
    """Property tests for Enrollment serializers."""
    
    def setUp(self):
        """Set up test data."""
        # Create faculty with unique username
        unique_id = str(uuid.uuid4())[:8]
        self.dean = User.objects.create_user(
            username=f'dean_enroll_{unique_id}',
            email=f'dean_enroll_{unique_id}@test.com',
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
        
        # Create or get level
        self.level, _ = Level.objects.get_or_create(
            name='L1',
            defaults={'order': 1}
        )
        
        # Create program
        self.program = Program.objects.create(
            name='Test Program',
            code=f'TP{unique_id}',
            department=self.department,
            level=self.level,
            duration_years=3
        )
        
        # Create academic year
        self.academic_year = AcademicYear.objects.create(
            name=f'2023-2024-{unique_id}',
            start_date=date(2023, 9, 1),
            end_date=date(2024, 6, 30),
            is_current=True
        )
        
        # Create student
        self.user = User.objects.create_user(
            username=f'student_enroll_{unique_id}',
            email=f'student_enroll_{unique_id}@test.com',
            password='testpass123',
            role=User.Role.STUDENT,
            first_name='Student',
            last_name='Test'
        )
        self.student = Student.objects.create(
            user=self.user,
            student_id=f'STU{unique_id}',
            program=self.program,
            current_level=self.level,
            enrollment_date=date.today()
        )
    
    @settings(max_examples=10)
    @given(
        status=st.sampled_from([choice[0] for choice in Enrollment.EnrollmentStatus.choices])
    )
    def test_property_1_foreign_key_representation(self, status):
        """
        Feature: backend-api-implementation, Property 1: Foreign Key Representation
        
        **Validates: Requirements 1.8**
        
        For any model instance with foreign key relationships, when serialized,
        the output should include readable representations of the related objects.
        """
        # Create enrollment
        enrollment = Enrollment.objects.create(
            student=self.student,
            academic_year=self.academic_year,
            program=self.program,
            level=self.level,
            status=status
        )
        
        # Test list serializer
        list_serializer = EnrollmentListSerializer(enrollment)
        list_data = list_serializer.data
        
        # Verify readable representations are included
        self.assertIn('student_name', list_data)
        self.assertIn('student_matricule', list_data)
        self.assertIn('academic_year_name', list_data)
        self.assertIn('program_name', list_data)
        self.assertIn('level_display', list_data)
        self.assertIn('status_display', list_data)
        
        # Verify values are correct
        self.assertEqual(list_data['student_name'], self.student.user.get_full_name())
        self.assertEqual(list_data['student_matricule'], self.student.student_id)
        self.assertEqual(list_data['academic_year_name'], self.academic_year.name)
        self.assertEqual(list_data['program_name'], self.program.name)
    
    @settings(max_examples=10)
    def test_property_2_validation_enforcement_program_level_mismatch(self):
        """
        Feature: backend-api-implementation, Property 2: Validation Enforcement
        
        **Validates: Requirements 1.9**
        
        For any invalid input data that violates model constraints or business rules,
        the serializer should reject it and return detailed validation errors.
        
        Test case: Program and level must be compatible.
        """
        # Create or get a different level
        different_level, _ = Level.objects.get_or_create(
            name='L2',
            defaults={'order': 2}
        )
        
        # Try to create enrollment with mismatched program and level
        data = {
            'student': self.student.id,
            'academic_year': self.academic_year.id,
            'program': self.program.id,  # Program is for L1
            'level': different_level.id,  # But level is L2
            'status': 'ENROLLED'
        }
        
        serializer = EnrollmentCreateSerializer(data=data)
        
        # Should be invalid due to program/level mismatch
        is_valid = serializer.is_valid()
        self.assertFalse(is_valid)
        
        # Should have level error
        self.assertIn('level', serializer.errors)
    
    @settings(max_examples=10)
    def test_property_2_validation_enforcement_duplicate_active_enrollment(self):
        """
        Feature: backend-api-implementation, Property 2: Validation Enforcement
        
        **Validates: Requirements 1.9**
        
        For any invalid input data that violates model constraints or business rules,
        the serializer should reject it and return detailed validation errors.
        
        Test case: Only one active enrollment per academic year.
        """
        # Create an active enrollment
        Enrollment.objects.create(
            student=self.student,
            academic_year=self.academic_year,
            program=self.program,
            level=self.level,
            status='ENROLLED',
            is_active=True
        )
        
        # Try to create another active enrollment for the same academic year
        data = {
            'student': self.student.id,
            'academic_year': self.academic_year.id,
            'program': self.program.id,
            'level': self.level.id,
            'status': 'ENROLLED',
            'is_active': True
        }
        
        serializer = EnrollmentCreateSerializer(data=data)
        
        # Should be invalid due to duplicate active enrollment
        is_valid = serializer.is_valid()
        self.assertFalse(is_valid)
        
        # Should have error (either in student field or non_field_errors for unique constraint)
        self.assertTrue('student' in serializer.errors or 'non_field_errors' in serializer.errors)


class AttendanceSerializerPropertyTests(TestCase):
    """Property tests for Attendance serializers."""
    
    def setUp(self):
        """Set up test data."""
        # Create users with unique usernames
        unique_id = str(uuid.uuid4())[:8]
        self.dean = User.objects.create_user(
            username=f'dean_attend_{unique_id}',
            email=f'dean_attend_{unique_id}@test.com',
            password='testpass123',
            role=User.Role.ADMIN,
            first_name='Dean',
            last_name='Test'
        )
        
        self.teacher_user = User.objects.create_user(
            username=f'teacher_attend_{unique_id}',
            email=f'teacher_attend_{unique_id}@test.com',
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
        self.level, _ = Level.objects.get_or_create(
            name='L1',
            defaults={'order': 1}
        )
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
            is_current=True
        )
        self.semester = Semester.objects.create(
            academic_year=self.academic_year,
            semester_type='FALL',
            start_date=date(2023, 9, 1),
            end_date=date(2024, 1, 31),
            is_current=True
        )
        
        # Create course
        self.course = Course.objects.create(
            name='Test Course',
            code=f'TC{unique_id}',
            program=self.program,
            credits=3
        )
        
        # Create time slot (use integer for day) - use get_or_create for unique constraint
        self.time_slot, _ = TimeSlot.objects.get_or_create(
            day=0,  # Monday (IntegerField)
            start_time='08:00:00',
            end_time='10:00:00'
        )
        
        # Create teacher
        from apps.teachers.models import Teacher
        self.teacher = Teacher.objects.create(
            user=self.teacher_user,
            employee_id=f'EMP{unique_id}',
            department=self.department,
            hire_date=date.today()
        )
        
        # Create schedule
        self.schedule = Schedule.objects.create(
            course=self.course,
            teacher=self.teacher,
            semester=self.semester,
            time_slot=self.time_slot
        )
        
        # Create course session
        self.course_session = CourseSession.objects.create(
            schedule=self.schedule,
            date=date.today(),
            session_type='LECTURE'
        )
        
        # Create student
        self.student_user = User.objects.create_user(
            username=f'student_attend_{unique_id}',
            email=f'student_attend_{unique_id}@test.com',
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
        status=st.sampled_from([choice[0] for choice in Attendance.AttendanceStatus.choices])
    )
    def test_property_1_foreign_key_representation(self, status):
        """
        Feature: backend-api-implementation, Property 1: Foreign Key Representation
        
        **Validates: Requirements 1.8**
        
        For any model instance with foreign key relationships, when serialized,
        the output should include readable representations of the related objects.
        """
        # Create attendance
        attendance = Attendance.objects.create(
            student=self.student,
            course_session=self.course_session,
            status=status,
            recorded_by=self.teacher_user
        )
        
        # Test list serializer
        list_serializer = AttendanceListSerializer(attendance)
        list_data = list_serializer.data
        
        # Verify readable representations are included
        self.assertIn('student_name', list_data)
        self.assertIn('student_matricule', list_data)
        self.assertIn('course_name', list_data)
        self.assertIn('session_date', list_data)
        self.assertIn('status_display', list_data)
        
        # Verify values are correct
        self.assertEqual(list_data['student_name'], self.student.user.get_full_name())
        self.assertEqual(list_data['student_matricule'], self.student.student_id)
        self.assertEqual(list_data['course_name'], self.course.name)
        
        # Test detail serializer
        detail_serializer = AttendanceDetailSerializer(attendance)
        detail_data = detail_serializer.data
        
        # Verify additional readable representations in detail view
        self.assertIn('teacher_name', detail_data)
        self.assertIn('recorded_by_name', detail_data)
    
    @settings(max_examples=10)
    def test_property_2_validation_enforcement_duplicate_attendance(self):
        """
        Feature: backend-api-implementation, Property 2: Validation Enforcement
        
        **Validates: Requirements 1.9**
        
        For any invalid input data that violates model constraints or business rules,
        the serializer should reject it and return detailed validation errors.
        
        Test case: Duplicate attendance for same student and session should be rejected.
        """
        # Create an attendance record
        Attendance.objects.create(
            student=self.student,
            course_session=self.course_session,
            status='PRESENT',
            recorded_by=self.teacher_user
        )
        
        # Try to create another attendance for the same student and session
        data = {
            'student': self.student.id,
            'course_session': self.course_session.id,
            'status': 'ABSENT',
            'recorded_by': self.teacher_user.id
        }
        
        serializer = AttendanceCreateSerializer(data=data)
        
        # Should be invalid due to duplicate attendance
        is_valid = serializer.is_valid()
        self.assertFalse(is_valid)
        
        # Should have error (either in student field or non_field_errors for unique constraint)
        self.assertTrue('student' in serializer.errors or 'non_field_errors' in serializer.errors)
