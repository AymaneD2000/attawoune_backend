"""
Property-based tests for scheduling viewsets.

This module tests the viewset functionality including:
- Schedule CRUD operations
- Conflict detection
- Custom actions
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from apps.university.models import AcademicYear, Semester, Faculty, Department, Program, Level, Classroom
from apps.scheduling.models import Schedule, TimeSlot, Announcement
from apps.teachers.models import Teacher
from apps.academics.models import Course
from datetime import date, time

User = get_user_model()


class ScheduleViewSetTestCase(TestCase):
    """Test cases for ScheduleViewSet."""
    
    def setUp(self):
        """Set up test data."""
        # Create admin user
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            role='ADMIN'
        )
        
        # Create teacher user
        self.teacher_user = User.objects.create_user(
            username='teacher',
            email='teacher@test.com',
            password='testpass123',
            first_name='Teacher',
            last_name='User',
            role='TEACHER'
        )
        
        # Create academic structure
        self.academic_year = AcademicYear.objects.create(
            name='2025-2026',
            start_date=date(2025, 9, 1),
            end_date=date(2026, 7, 31),
            is_current=True
        )
        
        self.semester = Semester.objects.create(
            academic_year=self.academic_year,
            semester_type='S1',
            start_date=date(2025, 9, 1),
            end_date=date(2026, 1, 31),
            is_current=True
        )
        
        self.faculty = Faculty.objects.create(
            name='Sciences',
            code='SCI'
        )
        
        self.department = Department.objects.create(
            name='Informatique',
            code='INFO',
            faculty=self.faculty
        )
        
        self.level = Level.objects.create(
            name='L1',
            order=1
        )
        
        self.program = Program.objects.create(
            name='Licence Informatique',
            code='LINF',
            department=self.department,
            level=self.level,
            duration_years=3
        )
        
        # Create classroom
        self.classroom = Classroom.objects.create(
            name='Salle A101',
            code='A101',
            building='Bâtiment A',
            capacity=50,
            is_available=True
        )
        
        self.classroom2 = Classroom.objects.create(
            name='Salle B201',
            code='B201',
            building='Bâtiment B',
            capacity=30,
            is_available=True
        )
        
        # Create teacher
        self.teacher = Teacher.objects.create(
            user=self.teacher_user,
            employee_id='EMP001',
            department=self.department,
            rank='LECTURER',
            contract_type='PERMANENT',
            hire_date=date(2020, 1, 1)
        )
        
        # Create course
        self.course = Course.objects.create(
            name='Programmation Python',
            code='INF101',
            program=self.program,
            semester=self.semester,
            credits=6,
            hours_lecture=24,
            hours_practical=24
        )
        
        # Create time slots
        self.time_slot_monday_8 = TimeSlot.objects.create(
            day=0,  # Monday
            start_time=time(8, 0),
            end_time=time(10, 0)
        )
        
        self.time_slot_monday_10 = TimeSlot.objects.create(
            day=0,  # Monday
            start_time=time(10, 0),
            end_time=time(12, 0)
        )
        
        self.time_slot_tuesday_8 = TimeSlot.objects.create(
            day=1,  # Tuesday
            start_time=time(8, 0),
            end_time=time(10, 0)
        )
        
        # Create a schedule
        self.schedule = Schedule.objects.create(
            course=self.course,
            teacher=self.teacher,
            classroom=self.classroom,
            time_slot=self.time_slot_monday_8,
            semester=self.semester
        )
        
        # Set up API client
        self.client = APIClient()
    
    def test_list_schedules_authenticated(self):
        """Test that authenticated users can list schedules."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/v1/scheduling/schedules/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_list_schedules_unauthenticated(self):
        """Test that unauthenticated users cannot list schedules."""
        response = self.client.get('/api/v1/scheduling/schedules/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_create_schedule_admin(self):
        """Test that admin can create schedules."""
        self.client.force_authenticate(user=self.admin_user)
        data = {
            'course': self.course.id,
            'teacher': self.teacher.id,
            'classroom': self.classroom2.id,
            'time_slot': self.time_slot_tuesday_8.id,
            'semester': self.semester.id
        }
        response = self.client.post('/api/v1/scheduling/schedules/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_check_conflicts_action(self):
        """Test the check_conflicts custom action."""
        self.client.force_authenticate(user=self.admin_user)
        data = {
            'semester_id': self.semester.id
        }
        response = self.client.post('/api/v1/scheduling/schedules/check_conflicts/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('conflicts', response.data)
        self.assertIn('conflicts_found', response.data)
    
    def test_teacher_conflict_detection(self):
        """Test that teacher conflicts are detected."""
        # Create another schedule with the same teacher at the same time
        Schedule.objects.create(
            course=self.course,
            teacher=self.teacher,
            classroom=self.classroom2,
            time_slot=self.time_slot_monday_8,  # Same time slot
            semester=self.semester
        )
        
        self.client.force_authenticate(user=self.admin_user)
        data = {
            'semester_id': self.semester.id
        }
        response = self.client.post('/api/v1/scheduling/schedules/check_conflicts/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should detect at least one conflict
        teacher_conflicts = [c for c in response.data['conflicts'] if c['type'] == 'teacher']
        self.assertGreaterEqual(len(teacher_conflicts), 1)
    
    def test_classroom_conflict_detection(self):
        """Test that classroom conflicts are detected."""
        # Create a second teacher 
        teacher2_user = User.objects.create_user(
            username='teacher2',
            email='teacher2@test.com',
            password='testpass123',
            first_name='Teacher2',
            last_name='User',
            role='TEACHER'
        )
        teacher2 = Teacher.objects.create(
            user=teacher2_user,
            employee_id='EMP002',
            department=self.department,
            rank='LECTURER',
            contract_type='PERMANENT',
            hire_date=date(2020, 1, 1)
        )
        
        # Create another schedule with the same classroom at the same time
        Schedule.objects.create(
            course=self.course,
            teacher=teacher2,
            classroom=self.classroom,  # Same classroom
            time_slot=self.time_slot_monday_8,  # Same time slot
            semester=self.semester
        )
        
        self.client.force_authenticate(user=self.admin_user)
        data = {
            'semester_id': self.semester.id
        }
        response = self.client.post('/api/v1/scheduling/schedules/check_conflicts/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should detect at least one classroom conflict
        classroom_conflicts = [c for c in response.data['conflicts'] if c['type'] == 'classroom']
        self.assertGreaterEqual(len(classroom_conflicts), 1)


class AnnouncementViewSetTestCase(TestCase):
    """Test cases for AnnouncementViewSet."""
    
    def setUp(self):
        """Set up test data."""
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            role='ADMIN'
        )
        
        self.secretary_user = User.objects.create_user(
            username='secretary',
            email='secretary@test.com',
            password='testpass123',
            first_name='Secretary',
            last_name='User',
            role='SECRETARY'
        )
        
        self.announcement = Announcement.objects.create(
            title='Test Announcement',
            content='This is a test announcement.',
            announcement_type='GENERAL',
            target_audience='ALL',
            is_published=True,
            created_by=self.admin_user,
            publish_date=date.today()
        )
        
        self.client = APIClient()
    
    def test_list_announcements(self):
        """Test that authenticated users can list announcements."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/v1/scheduling/announcements/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_active_announcements_action(self):
        """Test the active custom action."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/v1/scheduling/announcements/active/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return our published announcement
        self.assertGreaterEqual(len(response.data.get('results', [])), 1)
    
    def test_create_announcement_admin(self):
        """Test that admin can create announcements."""
        self.client.force_authenticate(user=self.admin_user)
        data = {
            'title': 'New Announcement',
            'content': 'New announcement content',
            'announcement_type': 'ACADEMIC',
            'target_audience': 'STUDENTS',
            'is_published': True,
            'publish_date': date.today().isoformat()
        }
        response = self.client.post('/api/v1/scheduling/announcements/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_create_announcement_secretary(self):
        """Test that secretary can create announcements."""
        self.client.force_authenticate(user=self.secretary_user)
        data = {
            'title': 'New Announcement',
            'content': 'New announcement content',
            'announcement_type': 'FINANCIAL',
            'target_audience': 'ALL',
            'is_published': False,
            'publish_date': date.today().isoformat()
        }
        response = self.client.post('/api/v1/scheduling/announcements/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
