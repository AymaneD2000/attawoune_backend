"""
Tests for student viewset custom actions.

This module tests:
- enrollments action
- grades action  
- promote/repeat actions
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from apps.university.models import AcademicYear, Semester, Faculty, Department, Program, Level
from apps.students.models import Student, Enrollment
from apps.academics.models import Course, Exam, Grade, CourseGrade
from apps.teachers.models import Teacher
from datetime import date, time
from decimal import Decimal

User = get_user_model()


class StudentCustomActionsTestCase(TestCase):
    """Test cases for StudentViewSet custom actions."""
    
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
        
        self.student_user = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='testpass123',
            first_name='Student',
            last_name='User',
            role='STUDENT'
        )
        
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
        
        self.level_l1 = Level.objects.create(name='L1', order=1)
        self.level_l2 = Level.objects.create(name='L2', order=2)
        
        self.program = Program.objects.create(
            name='Licence Informatique',
            code='LINF',
            department=self.department,
            level=self.level_l1,
            duration_years=3
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
        
        # Create student
        self.student = Student.objects.create(
            user=self.student_user,
            student_id='ETU2025001',
            program=self.program,
            current_level=self.level_l1,
            enrollment_date=date(2025, 9, 1),
            status='ACTIVE'
        )
        
        # Create enrollment
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            academic_year=self.academic_year,
            program=self.program,
            level=self.level_l1,
            status='ENROLLED'
        )
        
        # Create course
        self.course = Course.objects.create(
            name='Programmation Python',
            code='INF101',
            program=self.program,
            semester=self.semester,
            credits=6,
            hours_lecture=24
        )
        
        # Create exam and grade
        self.exam = Exam.objects.create(
            course=self.course,
            semester=self.semester,
            exam_type='MIDTERM',
            date=date(2025, 11, 15),
            start_time=time(8, 0),
            end_time=time(10, 0),
            max_score=Decimal('20.00')
        )
        
        self.grade = Grade.objects.create(
            student=self.student,
            exam=self.exam,
            score=Decimal('15.5'),
            remarks='Bon travail'
        )
        
        # Create course grade
        self.course_grade = CourseGrade.objects.create(
            student=self.student,
            course=self.course,
            semester=self.semester,
            final_score=Decimal('14.5'),
            is_validated=True
        )
        
        self.client = APIClient()
    
    def test_enrollments_action(self):
        """Test the enrollments custom action."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(f'/api/v1/students/students/{self.student.id}/enrollments/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('enrollments', response.data)
        self.assertEqual(len(response.data['enrollments']), 1)
    
    def test_grades_action(self):
        """Test the grades custom action."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(f'/api/v1/students/students/{self.student.id}/grades/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('exam_grades', response.data)
        self.assertIn('course_grades', response.data)
        # Should have 1 exam grade
        self.assertEqual(len(response.data['exam_grades']), 1)
        # Should have 1 course grade
        self.assertEqual(len(response.data['course_grades']), 1)
    
    def test_attendance_stats_action(self):
        """Test the attendance_stats custom action."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(f'/api/v1/students/students/{self.student.id}/attendance_stats/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_sessions', response.data)
        self.assertIn('present', response.data)
        self.assertIn('absent', response.data)
    
    def test_promote_action(self):
        """Test the promote custom action."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(f'/api/v1/students/students/{self.student.id}/promote/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Refresh student from database
        self.student.refresh_from_db()
        # Student should now be at L2
        self.assertEqual(self.student.current_level.name, 'L2')
    
    def test_repeat_action(self):
        """Test the repeat custom action."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(f'/api/v1/students/students/{self.student.id}/repeat/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Refresh student from database
        self.student.refresh_from_db()
        # Status should still be ACTIVE and level should be L1
        self.assertEqual(self.student.status, 'ACTIVE')
        self.assertEqual(self.student.current_level.name, 'L1')


class StudentEnrollmentValidationTestCase(TestCase):
    """Test cases for enrollment validation."""
    
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
        
        self.student_user = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='testpass123',
            first_name='Student',
            last_name='User',
            role='STUDENT'
        )
        
        self.academic_year = AcademicYear.objects.create(
            name='2025-2026',
            start_date=date(2025, 9, 1),
            end_date=date(2026, 7, 31),
            is_current=True
        )
        
        self.faculty = Faculty.objects.create(name='Sciences', code='SCI')
        self.department = Department.objects.create(
            name='Informatique', code='INFO', faculty=self.faculty
        )
        self.level = Level.objects.create(name='L1', order=1)
        self.program = Program.objects.create(
            name='Licence Informatique',
            code='LINF',
            department=self.department,
            level=self.level,
            duration_years=3
        )
        
        self.student = Student.objects.create(
            user=self.student_user,
            student_id='ETU2025001',
            program=self.program,
            current_level=self.level,
            enrollment_date=date(2025, 9, 1),
            status='ACTIVE'
        )
        
        self.client = APIClient()
    
    def test_create_enrollment(self):
        """Test creating an enrollment."""
        self.client.force_authenticate(user=self.admin_user)
        data = {
            'student': self.student.id,
            'academic_year': self.academic_year.id,
            'program': self.program.id,
            'level': self.level.id,
            'status': 'ENROLLED'
        }
        response = self.client.post('/api/v1/students/enrollments/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_list_enrollments(self):
        """Test listing enrollments."""
        Enrollment.objects.create(
            student=self.student,
            academic_year=self.academic_year,
            program=self.program,
            level=self.level,
            status='ENROLLED'
        )
        
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/v1/students/enrollments/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
