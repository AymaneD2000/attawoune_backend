"""
Integration tests for teachers app viewsets.

Tests basic CRUD operations and filtering for:
- TeacherViewSet
- TeacherCourseViewSet
- TeacherContractViewSet
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from apps.university.models import Department, Faculty, Semester, AcademicYear, Level, Program
from apps.academics.models import Course
from apps.teachers.models import Teacher, TeacherCourse, TeacherContract
from decimal import Decimal
from datetime import date, timedelta

User = get_user_model()


class TeacherViewSetIntegrationTests(TestCase):
    """Integration tests for TeacherViewSet."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
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
        
        # Create faculty and department
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
        
        # Create teacher
        self.teacher = Teacher.objects.create(
            user=self.teacher_user,
            employee_id='T001',
            department=self.department,
            rank='LECTURER',
            contract_type='PERMANENT',
            hire_date=date.today() - timedelta(days=365)
        )
    
    def test_list_teachers_as_admin(self):
        """Test listing teachers as admin user."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/teachers/teachers/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_retrieve_teacher_as_admin(self):
        """Test retrieving a teacher as admin user."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(f'/api/teachers/teachers/{self.teacher.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['employee_id'], 'T001')
        self.assertEqual(response.data['user_name'], 'Teacher User')
    
    def test_create_teacher_as_admin(self):
        """Test creating a teacher as admin user."""
        # Create a new user for the teacher
        new_user = User.objects.create_user(
            username='newteacher',
            email='newteacher@test.com',
            password='testpass123',
            first_name='New',
            last_name='Teacher',
            role='TEACHER'
        )
        
        self.client.force_authenticate(user=self.admin_user)
        data = {
            'user': new_user.id,
            'employee_id': 'T002',
            'department': self.department.id,
            'rank': 'ASSISTANT',
            'contract_type': 'CONTRACT',
            'hire_date': date.today().isoformat(),
            'is_active': True
        }
        response = self.client.post('/api/teachers/teachers/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['employee_id'], 'T002')
    
    def test_filter_teachers_by_department(self):
        """Test filtering teachers by department."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(
            f'/api/teachers/teachers/?department={self.department.id}'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_search_teachers_by_employee_id(self):
        """Test searching teachers by employee ID."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/teachers/teachers/?search=T001')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)


class TeacherCourseViewSetIntegrationTests(TestCase):
    """Integration tests for TeacherCourseViewSet."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
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
        
        # Create faculty and department
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
        
        # Create teacher
        self.teacher = Teacher.objects.create(
            user=self.teacher_user,
            employee_id='T001',
            department=self.department,
            rank='LECTURER',
            contract_type='PERMANENT',
            hire_date=date.today() - timedelta(days=365)
        )
        
        # Create academic year and semester
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
        
        # Create level and program
        self.level = Level.objects.create(
            name='L1',
            order=1
        )
        self.program = Program.objects.create(
            name='Computer Science L1',
            code='CS-L1',
            department=self.department,
            level=self.level
        )
        
        # Create course
        self.course = Course.objects.create(
            name='Introduction to Programming',
            code='CS101',
            program=self.program,
            credits=6,
            coefficient=2
        )
    
    def test_list_teacher_courses_as_admin(self):
        """Test listing teacher courses as admin user."""
        # Create a teacher course assignment
        TeacherCourse.objects.create(
            teacher=self.teacher,
            course=self.course,
            semester=self.semester,
            is_primary=True
        )
        
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/teachers/assignments/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_create_teacher_course_as_admin(self):
        """Test creating a teacher course assignment as admin user."""
        self.client.force_authenticate(user=self.admin_user)
        data = {
            'teacher': self.teacher.id,
            'course': self.course.id,
            'semester': self.semester.id,
            'is_primary': True
        }
        response = self.client.post('/api/teachers/assignments/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['is_primary'])
    
    def test_filter_teacher_courses_by_teacher(self):
        """Test filtering teacher courses by teacher."""
        TeacherCourse.objects.create(
            teacher=self.teacher,
            course=self.course,
            semester=self.semester,
            is_primary=True
        )
        
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(
            f'/api/teachers/assignments/?teacher={self.teacher.id}'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)


class TeacherContractViewSetIntegrationTests(TestCase):
    """Integration tests for TeacherContractViewSet."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
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
        
        # Create faculty and department
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
        
        # Create teacher
        self.teacher = Teacher.objects.create(
            user=self.teacher_user,
            employee_id='T001',
            department=self.department,
            rank='LECTURER',
            contract_type='PERMANENT',
            hire_date=date.today() - timedelta(days=365)
        )
    
    def test_list_teacher_contracts_as_admin(self):
        """Test listing teacher contracts as admin user."""
        # Create a contract
        TeacherContract.objects.create(
            teacher=self.teacher,
            contract_number='C001',
            start_date=date.today() - timedelta(days=365),
            end_date=date.today() + timedelta(days=365),
            base_salary=Decimal('50000.00'),
            status='ACTIVE'
        )
        
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/teachers/contracts/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_create_teacher_contract_as_admin(self):
        """Test creating a teacher contract as admin user."""
        self.client.force_authenticate(user=self.admin_user)
        data = {
            'teacher': self.teacher.id,
            'contract_number': 'C002',
            'start_date': date.today().isoformat(),
            'end_date': (date.today() + timedelta(days=365)).isoformat(),
            'base_salary': '60000.00',
            'status': 'ACTIVE'
        }
        response = self.client.post('/api/teachers/contracts/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['contract_number'], 'C002')
    
    def test_teacher_can_view_own_contracts(self):
        """Test that teachers can view their own contracts."""
        # Create a contract
        contract = TeacherContract.objects.create(
            teacher=self.teacher,
            contract_number='C003',
            start_date=date.today() - timedelta(days=365),
            end_date=date.today() + timedelta(days=365),
            base_salary=Decimal('50000.00'),
            status='ACTIVE'
        )
        
        self.client.force_authenticate(user=self.teacher_user)
        response = self.client.get('/api/teachers/contracts/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['contract_number'], 'C003')
    
    def test_filter_contracts_by_status(self):
        """Test filtering contracts by status."""
        TeacherContract.objects.create(
            teacher=self.teacher,
            contract_number='C004',
            start_date=date.today() - timedelta(days=365),
            end_date=date.today() + timedelta(days=365),
            base_salary=Decimal('50000.00'),
            status='ACTIVE'
        )
        
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/teachers/contracts/?status=ACTIVE')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

