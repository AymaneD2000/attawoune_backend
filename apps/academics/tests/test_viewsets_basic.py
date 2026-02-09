"""
Basic tests for academics viewsets.

This module provides basic tests to verify that the viewsets are properly configured.
"""

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import User
from apps.university.models import AcademicYear, Semester, Faculty, Department, Level, Program
from apps.students.models import Student
from apps.teachers.models import Teacher
from apps.academics.models import Course, Exam, Grade, CourseGrade, ReportCard
from decimal import Decimal
from datetime import date, time


class AcademicsViewSetBasicTests(TestCase):
    """Basic tests for academics viewsets."""
    
    def setUp(self):
        """Set up test data."""
        # Create users
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            role='ADMIN'
        )
        
        self.teacher_user = User.objects.create_user(
            username='teacher',
            email='teacher@test.com',
            password='testpass123',
            first_name='Teacher',
            last_name='User',
            role='TEACHER'
        )
        
        self.student_user = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='testpass123',
            first_name='Student',
            last_name='User',
            role='STUDENT'
        )
        
        # Create academic structure
        self.academic_year = AcademicYear.objects.create(
            name='2023-2024',
            start_date=date(2023, 9, 1),
            end_date=date(2024, 6, 30),
            is_current=True
        )
        
        self.semester = Semester.objects.create(
            academic_year=self.academic_year,
            semester_type='S1',
            start_date=date(2023, 9, 1),
            end_date=date(2024, 1, 31),
            is_current=True
        )
        
        self.faculty = Faculty.objects.create(
            name='Faculty of Science',
            code='SCI',
            dean=self.admin_user
        )
        
        self.department = Department.objects.create(
            name='Computer Science',
            code='CS',
            faculty=self.faculty,
            head=self.teacher_user
        )
        
        self.level = Level.objects.create(
            name='L1',
            order=1
        )
        
        self.program = Program.objects.create(
            name='Computer Science L1',
            code='CS-L1',
            department=self.department,
            level=self.level,
            duration_years=1,
            is_active=True
        )
        
        # Create student
        self.student = Student.objects.create(
            user=self.student_user,
            student_id='STU001',
            program=self.program,
            current_level=self.level,
            enrollment_date=date(2023, 9, 1),
            status='ACTIVE'
        )
        
        # Create teacher
        self.teacher = Teacher.objects.create(
            user=self.teacher_user,
            employee_id='TEACH001',
            department=self.department,
            rank='LECTURER',
            contract_type='PERMANENT',
            hire_date=date(2020, 9, 1),
            is_active=True
        )
        
        # Create course
        self.course = Course.objects.create(
            name='Introduction to Programming',
            code='CS101',
            program=self.program,
            course_type='REQUIRED',
            credits=3,
            semester=self.semester,
            is_active=True
        )
        
        # Create exam
        self.exam = Exam.objects.create(
            course=self.course,
            exam_type='MIDTERM',
            semester=self.semester,
            date=date(2023, 11, 15),
            start_time=time(9, 0),
            end_time=time(11, 0),
            max_score=Decimal('20.00'),
            weight=Decimal('0.40')
        )
        
        # Set up API client
        self.client = APIClient()
    
    def test_course_viewset_list_as_admin(self):
        """Test that admin can list courses."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/academics/courses/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
    
    def test_course_viewset_retrieve_as_admin(self):
        """Test that admin can retrieve a course."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(f'/api/academics/courses/{self.course.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 'CS101')
    
    def test_exam_viewset_list_as_admin(self):
        """Test that admin can list exams."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/academics/exams/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
    
    def test_exam_viewset_retrieve_as_admin(self):
        """Test that admin can retrieve an exam."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(f'/api/academics/exams/{self.exam.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['exam_type'], 'MIDTERM')
    
    def test_grade_viewset_create_as_teacher(self):
        """Test that teacher can create a grade."""
        # First assign teacher to course
        from apps.teachers.models import TeacherCourse
        TeacherCourse.objects.create(
            teacher=self.teacher,
            course=self.course,
            semester=self.semester,
            is_primary=True
        )
        
        self.client.force_authenticate(user=self.teacher_user)
        response = self.client.post('/api/academics/grades/', {
            'student': self.student.id,
            'exam': self.exam.id,
            'score': '15.50',
            'is_absent': False
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_grade_viewset_list_as_student(self):
        """Test that student can list their own grades."""
        # Create a grade
        Grade.objects.create(
            student=self.student,
            exam=self.exam,
            score=Decimal('15.50'),
            graded_by=self.teacher_user
        )
        
        self.client.force_authenticate(user=self.student_user)
        response = self.client.get('/api/academics/grades/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_course_grade_viewset_list_as_admin(self):
        """Test that admin can list course grades."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/academics/course-grades/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
    
    def test_report_card_viewset_list_as_admin(self):
        """Test that admin can list report cards."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/academics/report-cards/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
    
    def test_course_viewset_filtering(self):
        """Test that course filtering works."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(f'/api/academics/courses/?program={self.program.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_course_viewset_search(self):
        """Test that course search works."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/academics/courses/?search=CS101')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_course_viewset_ordering(self):
        """Test that course ordering works."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/academics/courses/?ordering=code')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
