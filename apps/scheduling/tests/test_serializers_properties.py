"""
Property-based tests for scheduling serializers.

These tests verify universal properties that should hold for all valid inputs.
"""

from hypothesis import given, strategies as st, settings
from hypothesis.extra.django import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, time, timedelta
import uuid
from apps.scheduling.serializers import (
    TimeSlotListSerializer,
    TimeSlotDetailSerializer,
    TimeSlotCreateSerializer,
    ScheduleListSerializer,
    ScheduleDetailSerializer,
    ScheduleCreateSerializer,
    CourseSessionListSerializer,
    CourseSessionDetailSerializer,
    CourseSessionCreateSerializer,
    AnnouncementListSerializer,
    AnnouncementDetailSerializer,
    AnnouncementCreateSerializer,
)
from apps.scheduling.models import TimeSlot, Schedule, CourseSession, Announcement
from apps.university.models import (
    AcademicYear, Semester, Faculty, Department, Level, Program, Classroom
)
from apps.academics.models import Course
from apps.teachers.models import Teacher

User = get_user_model()


class TimeSlotSerializerPropertyTests(TestCase):
    """Property tests for TimeSlot serializers."""
    
    @settings(max_examples=10)
    @given(
        day=st.integers(min_value=0, max_value=6),
        start_hour=st.integers(min_value=8, max_value=16),
        duration_hours=st.integers(min_value=1, max_value=4)
    )
    def test_property_1_foreign_key_representation(self, day, start_hour, duration_hours):
        """
        Feature: backend-api-implementation, Property 1: Foreign Key Representation
        
        **Validates: Requirements 1.8**
        
        For any model instance with foreign key relationships, when serialized,
        the output should include readable representations of the related objects.
        
        Note: TimeSlot has no foreign keys, but we test display fields.
        """
        # Create time slot
        start_time = time(hour=start_hour, minute=0)
        end_hour = min(start_hour + duration_hours, 23)
        end_time = time(hour=end_hour, minute=0)
        
        time_slot = TimeSlot.objects.create(
            day=day,
            start_time=start_time,
            end_time=end_time
        )
        
        # Test list serializer
        list_serializer = TimeSlotListSerializer(time_slot)
        list_data = list_serializer.data
        
        # Verify display fields are included
        self.assertIn('day_display', list_data)
        self.assertEqual(list_data['day_display'], time_slot.get_day_display())
        
        # Test detail serializer
        detail_serializer = TimeSlotDetailSerializer(time_slot)
        detail_data = detail_serializer.data
        
        # Verify computed properties are included
        self.assertIn('schedules_count', detail_data)
    
    @settings(max_examples=10)
    @given(
        day=st.integers(min_value=0, max_value=6),
        start_hour=st.integers(min_value=8, max_value=18),
    )
    def test_property_2_validation_enforcement_time_order(self, day, start_hour):
        """
        Feature: backend-api-implementation, Property 2: Validation Enforcement
        
        **Validates: Requirements 1.9**
        
        For any invalid input data that violates model constraints or business rules,
        the serializer should reject it and return detailed validation errors.
        
        Test case: start_time must be before end_time.
        """
        # Create invalid time slot where start_time >= end_time
        start_time = time(hour=start_hour, minute=0)
        end_time = time(hour=start_hour, minute=0)  # Same as start
        
        data = {
            'day': day,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat()
        }
        
        serializer = TimeSlotCreateSerializer(data=data)
        
        # Should be invalid due to time order
        is_valid = serializer.is_valid()
        self.assertFalse(is_valid)
        
        # Should have end_time error
        self.assertIn('end_time', serializer.errors)
    
    @settings(max_examples=10)
    @given(
        day=st.integers(min_value=0, max_value=6),
        start_hour=st.integers(min_value=8, max_value=16),
        duration_hours=st.integers(min_value=1, max_value=4)
    )
    def test_property_2_validation_enforcement_duplicate_timeslot(self, day, start_hour, duration_hours):
        """
        Feature: backend-api-implementation, Property 2: Validation Enforcement
        
        **Validates: Requirements 1.9**
        
        For any invalid input data that violates model constraints or business rules,
        the serializer should reject it and return detailed validation errors.
        
        Test case: Duplicate time slots should be rejected.
        """
        # Create time slot
        start_time = time(hour=start_hour, minute=0)
        end_hour = min(start_hour + duration_hours, 23)
        end_time = time(hour=end_hour, minute=0)
        
        TimeSlot.objects.create(
            day=day,
            start_time=start_time,
            end_time=end_time
        )
        
        # Try to create duplicate
        data = {
            'day': day,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat()
        }
        
        serializer = TimeSlotCreateSerializer(data=data)
        
        # Should be invalid due to duplicate
        is_valid = serializer.is_valid()
        self.assertFalse(is_valid)
        
        # Should have non_field_errors (unique constraint error)
        self.assertTrue('non_field_errors' in serializer.errors or 'day' in serializer.errors)


class ScheduleSerializerPropertyTests(TestCase):
    """Property tests for Schedule serializers."""
    
    def setUp(self):
        """Set up test data."""
        # Create users with unique usernames
        unique_id = str(uuid.uuid4())[:8]
        self.dean = User.objects.create_user(
            username=f'dean_sched_{unique_id}',
            email=f'dean_sched_{unique_id}@test.com',
            password='testpass123',
            role=User.Role.ADMIN,
            first_name='Dean',
            last_name='Test'
        )
        
        self.teacher_user = User.objects.create_user(
            username=f'teacher_sched_{unique_id}',
            email=f'teacher_sched_{unique_id}@test.com',
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
        self.academic_year, _ = AcademicYear.objects.get_or_create(
            name='2023-2024',
            defaults={
                'start_date': date(2023, 9, 1),
                'end_date': date(2024, 6, 30),
            }
        )
        self.semester, _ = Semester.objects.get_or_create(
            academic_year=self.academic_year,
            semester_type='FALL',
            start_date=date(2023, 9, 1),
            end_date=date(2024, 1, 31)
        )
        
        # Create course
        self.course = Course.objects.create(
            name='Test Course',
            code=f'TC{unique_id}',
            program=self.program,
            credits=3
        )
        
        # Create time slot
        self.time_slot, _ = TimeSlot.objects.get_or_create(
            day=0,  # Monday
            start_time=time(8, 0),
            end_time=time(10, 0)
        )
        
        # Create teacher
        self.teacher = Teacher.objects.create(
            user=self.teacher_user,
            employee_id=f'EMP{unique_id}',
            department=self.department,
            hire_date=date.today()
        )
        
        # Create classroom
        self.classroom = Classroom.objects.create(
            name='Room 101',
            code=f'R{unique_id}',
            building='Building A',
            capacity=30
        )
    
    @settings(max_examples=10)
    @given(
        is_active=st.booleans()
    )
    def test_property_1_foreign_key_representation(self, is_active):
        """
        Feature: backend-api-implementation, Property 1: Foreign Key Representation
        
        **Validates: Requirements 1.8**
        
        For any model instance with foreign key relationships, when serialized,
        the output should include readable representations of the related objects.
        """
        # Create schedule
        schedule = Schedule.objects.create(
            course=self.course,
            teacher=self.teacher,
            semester=self.semester,
            time_slot=self.time_slot,
            classroom=self.classroom,
            is_active=is_active
        )
        
        # Test list serializer
        list_serializer = ScheduleListSerializer(schedule)
        list_data = list_serializer.data
        
        # Verify readable representations are included
        self.assertIn('course_name', list_data)
        self.assertIn('course_code', list_data)
        self.assertIn('teacher_name', list_data)
        self.assertIn('semester_name', list_data)
        self.assertIn('time_slot_display', list_data)
        self.assertIn('classroom_name', list_data)
        
        # Verify values are correct
        self.assertEqual(list_data['course_name'], self.course.name)
        self.assertEqual(list_data['course_code'], self.course.code)
        self.assertEqual(list_data['teacher_name'], self.teacher.user.get_full_name())
        
        # Test detail serializer
        detail_serializer = ScheduleDetailSerializer(schedule)
        detail_data = detail_serializer.data
        
        # Verify additional readable representations in detail view
        self.assertIn('program_name', detail_data)
        self.assertIn('academic_year', detail_data)
        self.assertIn('day_display', detail_data)
        self.assertIn('classroom_capacity', detail_data)
        self.assertIn('sessions_count', detail_data)
    
    @settings(max_examples=10)
    def test_property_2_validation_enforcement_teacher_conflict(self):
        """
        Feature: backend-api-implementation, Property 2: Validation Enforcement
        
        **Validates: Requirements 1.9**
        
        For any invalid input data that violates model constraints or business rules,
        the serializer should reject it and return detailed validation errors.
        
        Test case: Teacher conflict - same teacher, same time slot, same semester.
        """
        # Create a schedule
        Schedule.objects.create(
            course=self.course,
            teacher=self.teacher,
            semester=self.semester,
            time_slot=self.time_slot,
            classroom=self.classroom,
            is_active=True
        )
        
        # Create another course
        course2 = Course.objects.create(
            name='Test Course 2',
            code='TC102',
            program=self.program,
            credits=3
        )
        
        # Try to create another schedule with same teacher, time slot, and semester
        data = {
            'course': course2.id,
            'teacher': self.teacher.id,
            'semester': self.semester.id,
            'time_slot': self.time_slot.id,
            'is_active': True
        }
        
        serializer = ScheduleCreateSerializer(data=data)
        
        # Should be invalid due to teacher conflict
        is_valid = serializer.is_valid()
        self.assertFalse(is_valid)
        
        # Should have teacher error
        self.assertIn('teacher', serializer.errors)
    
    @settings(max_examples=10)
    def test_property_2_validation_enforcement_classroom_conflict(self):
        """
        Feature: backend-api-implementation, Property 2: Validation Enforcement
        
        **Validates: Requirements 1.9**
        
        For any invalid input data that violates model constraints or business rules,
        the serializer should reject it and return detailed validation errors.
        
        Test case: Classroom conflict - same classroom, same time slot, same semester.
        """
        # Create a schedule
        Schedule.objects.create(
            course=self.course,
            teacher=self.teacher,
            semester=self.semester,
            time_slot=self.time_slot,
            classroom=self.classroom,
            is_active=True
        )
        
        # Create another teacher
        teacher_user2 = User.objects.create_user(
            username=f'teacher2_{uuid.uuid4().hex[:8]}',
            email=f'teacher2_{uuid.uuid4().hex[:8]}@test.com',
            password='testpass123',
            role=User.Role.TEACHER,
            first_name='Teacher2',
            last_name='Test'
        )
        teacher2 = Teacher.objects.create(
            user=teacher_user2,
            employee_id='EMP002',
            department=self.department,
            hire_date=date.today()
        )
        
        # Create another course
        course2 = Course.objects.create(
            name='Test Course 2',
            code='TC102',
            program=self.program,
            credits=3
        )
        
        # Try to create another schedule with same classroom, time slot, and semester
        data = {
            'course': course2.id,
            'teacher': teacher2.id,
            'semester': self.semester.id,
            'time_slot': self.time_slot.id,
            'classroom': self.classroom.id,
            'is_active': True
        }
        
        serializer = ScheduleCreateSerializer(data=data)
        
        # Should be invalid due to classroom conflict
        is_valid = serializer.is_valid()
        self.assertFalse(is_valid)
        
        # Should have classroom error
        self.assertIn('classroom', serializer.errors)
    
    @settings(max_examples=10)
    def test_property_3_computed_properties_inclusion(self):
        """
        Feature: backend-api-implementation, Property 3: Computed Properties Inclusion
        
        **Validates: Requirements 1.10**
        
        For any model with computed properties, the serializer should include
        those properties as read-only fields in the output.
        """
        # Create schedule
        schedule = Schedule.objects.create(
            course=self.course,
            teacher=self.teacher,
            semester=self.semester,
            time_slot=self.time_slot,
            classroom=self.classroom,
            is_active=True
        )
        
        # Serialize with detail serializer
        serializer = ScheduleDetailSerializer(schedule)
        data = serializer.data
        
        # Verify computed properties are included
        self.assertIn('sessions_count', data)
        
        # Verify computed values are correct
        self.assertEqual(data['sessions_count'], schedule.sessions.count())


class CourseSessionSerializerPropertyTests(TestCase):
    """Property tests for CourseSession serializers."""
    
    def setUp(self):
        """Set up test data."""
        # Create users with unique usernames
        unique_id = str(uuid.uuid4())[:8]
        self.dean = User.objects.create_user(
            username=f'dean_session_{unique_id}',
            email=f'dean_session_{unique_id}@test.com',
            password='testpass123',
            role=User.Role.ADMIN,
            first_name='Dean',
            last_name='Test'
        )
        
        self.teacher_user = User.objects.create_user(
            username=f'teacher_session_{unique_id}',
            email=f'teacher_session_{unique_id}@test.com',
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
        self.academic_year, _ = AcademicYear.objects.get_or_create(
            name='2023-2024',
            defaults={
                'start_date': date(2023, 9, 1),
                'end_date': date(2024, 6, 30),
            }
        )
        self.semester, _ = Semester.objects.get_or_create(
            academic_year=self.academic_year,
            semester_type='FALL',
            start_date=date(2023, 9, 1),
            end_date=date(2024, 1, 31)
        )
        
        # Create course
        self.course = Course.objects.create(
            name='Test Course',
            code=f'TC{unique_id}',
            program=self.program,
            credits=3
        )
        
        # Create time slot
        self.time_slot, _ = TimeSlot.objects.get_or_create(
            day=0,  # Monday
            start_time=time(8, 0),
            end_time=time(10, 0)
        )
        
        # Create teacher
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
    
    @settings(max_examples=10)
    @given(
        session_type=st.sampled_from([choice[0] for choice in CourseSession.SessionType.choices]),
        is_cancelled=st.booleans()
    )
    def test_property_1_foreign_key_representation(self, session_type, is_cancelled):
        """
        Feature: backend-api-implementation, Property 1: Foreign Key Representation
        
        **Validates: Requirements 1.8**
        
        For any model instance with foreign key relationships, when serialized,
        the output should include readable representations of the related objects.
        """
        # Create course session
        session_date = date(2023, 9, 15)  # Within semester dates
        course_session = CourseSession.objects.create(
            schedule=self.schedule,
            date=session_date,
            session_type=session_type,
            is_cancelled=is_cancelled,
            cancellation_reason='Test reason' if is_cancelled else ''
        )
        
        # Test list serializer
        list_serializer = CourseSessionListSerializer(course_session)
        list_data = list_serializer.data
        
        # Verify readable representations are included
        self.assertIn('course_name', list_data)
        self.assertIn('course_code', list_data)
        self.assertIn('teacher_name', list_data)
        self.assertIn('time_slot_display', list_data)
        self.assertIn('session_type_display', list_data)
        
        # Verify values are correct
        self.assertEqual(list_data['course_name'], self.course.name)
        self.assertEqual(list_data['teacher_name'], self.teacher.user.get_full_name())
        
        # Test detail serializer
        detail_serializer = CourseSessionDetailSerializer(course_session)
        detail_data = detail_serializer.data
        
        # Verify additional readable representations in detail view
        self.assertIn('program_name', detail_data)
        self.assertIn('semester_name', detail_data)
        self.assertIn('academic_year', detail_data)
        self.assertIn('attendance_count', detail_data)
    
    @settings(max_examples=10)
    def test_property_2_validation_enforcement_duplicate_session(self):
        """
        Feature: backend-api-implementation, Property 2: Validation Enforcement
        
        **Validates: Requirements 1.9**
        
        For any invalid input data that violates model constraints or business rules,
        the serializer should reject it and return detailed validation errors.
        
        Test case: Duplicate session for same schedule and date should be rejected.
        """
        # Create a course session
        session_date = date(2023, 9, 15)
        CourseSession.objects.create(
            schedule=self.schedule,
            date=session_date,
            session_type='LECTURE'
        )
        
        # Try to create another session for the same schedule and date
        data = {
            'schedule': self.schedule.id,
            'date': session_date.isoformat(),
            'session_type': 'TUTORIAL'
        }
        
        serializer = CourseSessionCreateSerializer(data=data)
        
        # Should be invalid due to duplicate
        is_valid = serializer.is_valid()
        self.assertFalse(is_valid)
        
        # Should have error (either date or non_field_errors for unique constraint)
        self.assertTrue('date' in serializer.errors or 'non_field_errors' in serializer.errors)
    
    @settings(max_examples=10)
    def test_property_2_validation_enforcement_date_outside_semester(self):
        """
        Feature: backend-api-implementation, Property 2: Validation Enforcement
        
        **Validates: Requirements 1.9**
        
        For any invalid input data that violates model constraints or business rules,
        the serializer should reject it and return detailed validation errors.
        
        Test case: Session date must be within semester dates.
        """
        # Try to create session with date outside semester
        session_date = date(2024, 3, 1)  # After semester end date
        
        data = {
            'schedule': self.schedule.id,
            'date': session_date.isoformat(),
            'session_type': 'LECTURE'
        }
        
        serializer = CourseSessionCreateSerializer(data=data)
        
        # Should be invalid due to date outside semester
        is_valid = serializer.is_valid()
        self.assertFalse(is_valid)
        
        # Should have error (either date or non_field_errors for unique constraint)
        self.assertTrue('date' in serializer.errors or 'non_field_errors' in serializer.errors)
    
    @settings(max_examples=10)
    def test_property_2_validation_enforcement_cancelled_without_reason(self):
        """
        Feature: backend-api-implementation, Property 2: Validation Enforcement
        
        **Validates: Requirements 1.9**
        
        For any invalid input data that violates model constraints or business rules,
        the serializer should reject it and return detailed validation errors.
        
        Test case: Cancelled session must have cancellation reason.
        """
        # Try to create cancelled session without reason
        session_date = date(2023, 9, 15)
        
        data = {
            'schedule': self.schedule.id,
            'date': session_date.isoformat(),
            'session_type': 'LECTURE',
            'is_cancelled': True,
            'cancellation_reason': ''  # Empty reason
        }
        
        serializer = CourseSessionCreateSerializer(data=data)
        
        # Should be invalid due to missing cancellation reason
        is_valid = serializer.is_valid()
        self.assertFalse(is_valid)
        
        # Should have cancellation_reason error
        self.assertIn('cancellation_reason', serializer.errors)


class AnnouncementSerializerPropertyTests(TestCase):
    """Property tests for Announcement serializers."""
    
    def setUp(self):
        """Set up test data."""
        # Create user with unique username
        unique_id = str(uuid.uuid4())[:8]
        self.admin_user = User.objects.create_user(
            username=f'admin_announce_{unique_id}',
            email=f'admin_announce_{unique_id}@test.com',
            password='testpass123',
            role=User.Role.ADMIN,
            first_name='Admin',
            last_name='Test'
        )
        
        # Create faculty
        self.faculty = Faculty.objects.create(
            name='Test Faculty',
            code=f'TF{unique_id}',
            dean=self.admin_user
        )
        
        # Create department
        self.department = Department.objects.create(
            name='Test Department',
            code=f'TD{unique_id}',
            faculty=self.faculty,
            head=self.admin_user
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
    
    @settings(max_examples=10)
    @given(
        announcement_type=st.sampled_from([choice[0] for choice in Announcement.AnnouncementType.choices]),
        target_audience=st.sampled_from([choice[0] for choice in Announcement.TargetAudience.choices]),
        is_published=st.booleans(),
        is_pinned=st.booleans()
    )
    def test_property_1_foreign_key_representation(self, announcement_type, target_audience, is_published, is_pinned):
        """
        Feature: backend-api-implementation, Property 1: Foreign Key Representation
        
        **Validates: Requirements 1.8**
        
        For any model instance with foreign key relationships, when serialized,
        the output should include readable representations of the related objects.
        """
        # Create announcement
        announcement = Announcement.objects.create(
            title='Test Announcement',
            content='Test content',
            announcement_type=announcement_type,
            target_audience=target_audience,
            faculty=self.faculty,
            program=self.program,
            is_published=is_published,
            is_pinned=is_pinned,
            created_by=self.admin_user
        )
        
        # Test list serializer
        list_serializer = AnnouncementListSerializer(announcement)
        list_data = list_serializer.data
        
        # Verify readable representations are included
        self.assertIn('announcement_type_display', list_data)
        self.assertIn('target_audience_display', list_data)
        self.assertIn('faculty_name', list_data)
        self.assertIn('program_name', list_data)
        self.assertIn('created_by_name', list_data)
        
        # Verify values are correct
        self.assertEqual(list_data['announcement_type_display'], announcement.get_announcement_type_display())
        self.assertEqual(list_data['target_audience_display'], announcement.get_target_audience_display())
        self.assertEqual(list_data['faculty_name'], self.faculty.name)
        self.assertEqual(list_data['created_by_name'], self.admin_user.get_full_name())
        
        # Test detail serializer
        detail_serializer = AnnouncementDetailSerializer(announcement)
        detail_data = detail_serializer.data
        
        # Verify additional readable representations in detail view
        self.assertIn('faculty_code', detail_data)
        self.assertIn('program_code', detail_data)
        self.assertIn('department_name', detail_data)
        self.assertIn('created_by_email', detail_data)
    
    @settings(max_examples=10)
    def test_property_2_validation_enforcement_invalid_target_audience(self):
        """
        Feature: backend-api-implementation, Property 2: Validation Enforcement
        
        **Validates: Requirements 1.9**
        
        For any invalid input data that violates model constraints or business rules,
        the serializer should reject it and return detailed validation errors.
        
        Test case: Invalid target audience should be rejected.
        """
        # Try to create announcement with invalid target audience
        data = {
            'title': 'Test Announcement',
            'content': 'Test content',
            'announcement_type': 'GENERAL',
            'target_audience': 'INVALID_AUDIENCE',  # Invalid choice
            'created_by': self.admin_user.id
        }
        
        serializer = AnnouncementCreateSerializer(data=data)
        
        # Should be invalid due to invalid target audience
        is_valid = serializer.is_valid()
        self.assertFalse(is_valid)
        
        # Should have target_audience error
        self.assertIn('target_audience', serializer.errors)
    
    @settings(max_examples=10)
    def test_property_2_validation_enforcement_expiry_before_publish(self):
        """
        Feature: backend-api-implementation, Property 2: Validation Enforcement
        
        **Validates: Requirements 1.9**
        
        For any invalid input data that violates model constraints or business rules,
        the serializer should reject it and return detailed validation errors.
        
        Test case: Expiry date must be after publish date.
        """
        # Try to create announcement with expiry before publish date
        publish_date = timezone.now()
        expiry_date = publish_date - timedelta(days=1)  # Before publish date
        
        data = {
            'title': 'Test Announcement',
            'content': 'Test content',
            'announcement_type': 'GENERAL',
            'target_audience': 'ALL',
            'publish_date': publish_date.isoformat(),
            'expiry_date': expiry_date.isoformat(),
            'created_by': self.admin_user.id
        }
        
        serializer = AnnouncementCreateSerializer(data=data)
        
        # Should be invalid due to expiry before publish
        is_valid = serializer.is_valid()
        self.assertFalse(is_valid)
        
        # Should have expiry_date error
        self.assertIn('expiry_date', serializer.errors)
