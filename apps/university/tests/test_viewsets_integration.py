"""
Integration tests for university app viewsets.

Tests the complete viewset implementation including:
- Queryset optimization (select_related, prefetch_related)
- Permission classes
- Serializer selection
- Filtering, searching, and ordering
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from apps.university.models import (
    AcademicYear, Semester, Faculty, Department, Level, Program, Classroom
)

User = get_user_model()


class UniversityViewSetIntegrationTests(TestCase):
    """Integration tests for university viewsets."""
    
    def setUp(self):
        """Set up test data."""
        # Create users with different roles
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            role='ADMIN',
            first_name='Admin',
            last_name='User'
        )
        
        self.secretary_user = User.objects.create_user(
            username='secretary',
            email='secretary@test.com',
            password='testpass123',
            role='SECRETARY',
            first_name='Secretary',
            last_name='User'
        )
        
        self.student_user = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='testpass123',
            role='STUDENT',
            first_name='Student',
            last_name='User'
        )
        
        # Create test data
        self.academic_year = AcademicYear.objects.create(
            name='2023-2024',
            start_date='2023-09-01',
            end_date='2024-06-30',
            is_current=True
        )
        
        self.semester = Semester.objects.create(
            academic_year=self.academic_year,
            semester_type='S1',
            start_date='2023-09-01',
            end_date='2024-01-31',
            is_current=True
        )
        
        self.faculty = Faculty.objects.create(
            name='Faculty of Science',
            code='SCI',
            description='Science faculty',
            dean=self.admin_user
        )
        
        self.department = Department.objects.create(
            name='Computer Science',
            code='CS',
            faculty=self.faculty,
            head=self.admin_user,
            description='CS department'
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
            tuition_fee=1000.00,
            is_active=True
        )
        
        self.classroom = Classroom.objects.create(
            name='Room 101',
            code='R101',
            building='Building A',
            capacity=30,
            has_projector=True,
            has_computers=False,
            is_available=True
        )
        
        self.client = APIClient()
    
    def test_academic_year_viewset_list(self):
        """Test AcademicYearViewSet list action."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/university/academic-years/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertIn('semesters_count', response.data['results'][0])
    
    def test_academic_year_viewset_retrieve(self):
        """Test AcademicYearViewSet retrieve action."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(f'/api/university/academic-years/{self.academic_year.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], '2023-2024')
        self.assertIn('semesters_count', response.data)
    
    def test_academic_year_viewset_permissions(self):
        """Test AcademicYearViewSet permissions."""
        # Admin can create
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post('/api/university/academic-years/', {
            'name': '2024-2025',
            'start_date': '2024-09-01',
            'end_date': '2025-06-30',
            'is_current': False
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Student cannot create
        self.client.force_authenticate(user=self.student_user)
        response = self.client.post('/api/university/academic-years/', {
            'name': '2025-2026',
            'start_date': '2025-09-01',
            'end_date': '2026-06-30',
            'is_current': False
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Student can read
        response = self.client.get('/api/university/academic-years/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_semester_viewset_filtering(self):
        """Test SemesterViewSet filtering."""
        self.client.force_authenticate(user=self.admin_user)
        
        # Filter by academic year
        response = self.client.get(
            f'/api/university/semesters/?academic_year={self.academic_year.id}'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
        # Filter by semester type
        response = self.client.get('/api/university/semesters/?semester_type=S1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
        # Filter by is_current
        response = self.client.get('/api/university/semesters/?is_current=true')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_faculty_viewset_searching(self):
        """Test FacultyViewSet searching."""
        self.client.force_authenticate(user=self.admin_user)
        
        # Search by name
        response = self.client.get('/api/university/faculties/?search=Science')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
        # Search by code
        response = self.client.get('/api/university/faculties/?search=SCI')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_department_viewset_ordering(self):
        """Test DepartmentViewSet ordering."""
        self.client.force_authenticate(user=self.admin_user)
        
        # Create another department
        Department.objects.create(
            name='Mathematics',
            code='MATH',
            faculty=self.faculty,
            description='Math department'
        )
        
        # Order by name ascending
        response = self.client.get('/api/university/departments/?ordering=name')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'][0]['name'], 'Computer Science')
        
        # Order by name descending
        response = self.client.get('/api/university/departments/?ordering=-name')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'][0]['name'], 'Mathematics')
    
    def test_program_viewset_permissions(self):
        """Test ProgramViewSet permissions."""
        # Admin can create
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post('/api/university/programs/', {
            'name': 'Computer Science L2',
            'code': 'CS-L2',
            'department': self.department.id,
            'level': self.level.id,
            'duration_years': 1,
            'tuition_fee': 1000.00,
            'is_active': True
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Secretary can create
        self.client.force_authenticate(user=self.secretary_user)
        response = self.client.post('/api/university/programs/', {
            'name': 'Computer Science L3',
            'code': 'CS-L3',
            'department': self.department.id,
            'level': self.level.id,
            'duration_years': 1,
            'tuition_fee': 1000.00,
            'is_active': True
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Student cannot create
        self.client.force_authenticate(user=self.student_user)
        response = self.client.post('/api/university/programs/', {
            'name': 'Computer Science M1',
            'code': 'CS-M1',
            'department': self.department.id,
            'level': self.level.id,
            'duration_years': 1,
            'tuition_fee': 1000.00,
            'is_active': True
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Student can read
        response = self.client.get('/api/university/programs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_classroom_viewset_filtering(self):
        """Test ClassroomViewSet filtering."""
        self.client.force_authenticate(user=self.admin_user)
        
        # Create another classroom
        Classroom.objects.create(
            name='Room 102',
            code='R102',
            building='Building B',
            capacity=40,
            has_projector=False,
            has_computers=True,
            is_available=False
        )
        
        # Filter by building
        response = self.client.get('/api/university/classrooms/?building=Building A')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
        # Filter by has_projector
        response = self.client.get('/api/university/classrooms/?has_projector=true')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
        # Filter by has_computers
        response = self.client.get('/api/university/classrooms/?has_computers=true')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
        # Filter by is_available
        response = self.client.get('/api/university/classrooms/?is_available=true')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_serializer_selection(self):
        """Test that viewsets use appropriate serializers for different actions."""
        self.client.force_authenticate(user=self.admin_user)
        
        # List action should use list serializer (fewer fields)
        list_response = self.client.get('/api/university/faculties/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        list_fields = set(list_response.data['results'][0].keys())
        
        # Retrieve action should use detail serializer (more fields)
        detail_response = self.client.get(f'/api/university/faculties/{self.faculty.id}/')
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        detail_fields = set(detail_response.data.keys())
        
        # Detail should have more fields than list
        self.assertGreater(len(detail_fields), len(list_fields))
        self.assertIn('programs_count', detail_fields)
    
    def test_queryset_optimization(self):
        """Test that viewsets use select_related and prefetch_related."""
        self.client.force_authenticate(user=self.admin_user)
        
        # This test verifies that the queries are optimized
        # by checking that related objects are accessible without additional queries
        with self.assertNumQueries(4):  # Should be minimal queries due to optimization
            response = self.client.get('/api/university/departments/')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            # Access related data that should be prefetched
            self.assertIn('faculty_name', response.data['results'][0])
            self.assertIn('programs_count', response.data['results'][0])
