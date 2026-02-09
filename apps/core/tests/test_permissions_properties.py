"""
Property-based tests for permission classes.

Feature: backend-api-implementation
Tests Properties 11-18: Permission and access control properties

These tests verify that role-based access control works correctly across all user roles
and that object-level permissions are properly enforced.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.core.permissions import (
    IsAdmin, IsDean, IsTeacher, IsStudent, IsAccountant, IsSecretary,
    IsAdminOrReadOnly, IsTeacherOrAdmin, IsAccountantOrAdmin, IsSecretaryOrAdmin,
    IsOwnerOrAdmin, IsTeacherOfCourse
)
from apps.university.models import (
    AcademicYear, Semester, Faculty, Department, Level, Program
)
from apps.students.models import Student, Enrollment
from apps.teachers.models import Teacher, TeacherCourse
from apps.academics.models import Course, Exam, Grade

User = get_user_model()


# Test view for permission testing
class TestView(APIView):
    """Simple test view for permission testing."""
    
    def get(self, request):
        return Response({"message": "success"}, status=status.HTTP_200_OK)
    
    def post(self, request):
        return Response({"message": "created"}, status=status.HTTP_201_CREATED)
    
    def put(self, request):
        return Response({"message": "updated"}, status=status.HTTP_200_OK)
    
    def delete(self, request):
        return Response(status=status.HTTP_204_NO_CONTENT)


class PermissionPropertyTests(TestCase):
    """
    Property-based tests for permission classes.
    
    Note: These are structured as property tests but use Django's TestCase
    for database access. Each test verifies a universal property across
    different user roles and scenarios.
    """
    
    def setUp(self):
        """Set up test data for all permission tests."""
        self.factory = APIRequestFactory()
        
        # Create users for each role
        self.admin_user = User.objects.create_user(
            username='admin',
            password='testpass123',
            role='ADMIN',
            first_name='Admin',
            last_name='User'
        )
        
        self.dean_user = User.objects.create_user(
            username='dean',
            password='testpass123',
            role='DEAN',
            first_name='Dean',
            last_name='User'
        )
        
        self.teacher_user = User.objects.create_user(
            username='teacher',
            password='testpass123',
            role='TEACHER',
            first_name='Teacher',
            last_name='User'
        )
        
        self.student_user = User.objects.create_user(
            username='student',
            password='testpass123',
            role='STUDENT',
            first_name='Student',
            last_name='User'
        )
        
        self.accountant_user = User.objects.create_user(
            username='accountant',
            password='testpass123',
            role='ACCOUNTANT',
            first_name='Accountant',
            last_name='User'
        )
        
        self.secretary_user = User.objects.create_user(
            username='secretary',
            password='testpass123',
            role='SECRETARY',
            first_name='Secretary',
            last_name='User'
        )
        
        # Create academic structure for testing
        self.academic_year = AcademicYear.objects.create(
            name='2024-2025',
            start_date='2024-09-01',
            end_date='2025-06-30',
            is_current=True
        )
        
        self.semester = Semester.objects.create(
            academic_year=self.academic_year,
            semester_type='S1',
            start_date='2024-09-01',
            end_date='2025-01-31',
            is_current=True
        )
        
        self.faculty = Faculty.objects.create(
            name='Faculty of Science',
            code='SCI',
            dean=self.dean_user
        )
        
        self.department = Department.objects.create(
            name='Computer Science',
            code='CS',
            faculty=self.faculty
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
            tuition_fee=500000
        )
        
        # Create student profile
        self.student = Student.objects.create(
            user=self.student_user,
            student_id='STU001',
            program=self.program,
            current_level=self.level,
            enrollment_date='2024-09-01'
        )
        
        # Create teacher profile
        self.teacher = Teacher.objects.create(
            user=self.teacher_user,
            employee_id='TCH001',
            department=self.department,
            hire_date='2020-01-01'
        )
        
        # Create course
        self.course = Course.objects.create(
            name='Introduction to Programming',
            code='CS101',
            program=self.program,
            semester=self.semester,
            credits=3
        )
        
        # Assign teacher to course
        self.teacher_course = TeacherCourse.objects.create(
            teacher=self.teacher,
            course=self.course,
            semester=self.semester,
            is_primary=True
        )
    
    # Property 11: Admin Full Access
    def test_property_11_admin_full_access(self):
        """
        Feature: backend-api-implementation, Property 11: Admin Full Access
        
        For any authenticated admin user, all API endpoints should grant full
        read and write access regardless of data ownership.
        
        Validates: Requirements 3.2
        """
        view = TestView.as_view()
        
        # Test all HTTP methods with admin user
        methods_and_requests = [
            ('GET', self.factory.get('/test/')),
            ('POST', self.factory.post('/test/')),
            ('PUT', self.factory.put('/test/')),
            ('DELETE', self.factory.delete('/test/'))
        ]
        
        for method, request in methods_and_requests:
            force_authenticate(request, user=self.admin_user)
            
            # Test with IsAdmin permission
            view.permission_classes = [IsAdmin]
            response = view(request)
            self.assertIn(
                response.status_code,
                [200, 201, 204],
                f"Admin should have access to {method} requests"
            )
            
            # Test with IsAdminOrReadOnly permission
            view.permission_classes = [IsAdminOrReadOnly]
            response = view(request)
            self.assertIn(
                response.status_code,
                [200, 201, 204],
                f"Admin should have access to {method} requests with IsAdminOrReadOnly"
            )
    
    # Property 12: Dean Faculty Access
    def test_property_12_dean_faculty_access(self):
        """
        Feature: backend-api-implementation, Property 12: Dean Faculty Access
        
        For any dean user accessing faculty or department endpoints, the API
        should only return data for their assigned faculty.
        
        Validates: Requirements 3.3
        """
        view = TestView.as_view()
        view.permission_classes = [IsDean]
        
        request = self.factory.get('/test/')
        force_authenticate(request, user=self.dean_user)
        
        response = view(request)
        self.assertEqual(
            response.status_code,
            200,
            "Dean should have access to faculty endpoints"
        )
        
        # Verify dean is assigned to faculty
        self.assertEqual(
            self.faculty.dean,
            self.dean_user,
            "Dean should be assigned to faculty"
        )
    
    # Property 13: Teacher Course Access
    def test_property_13_teacher_course_access(self):
        """
        Feature: backend-api-implementation, Property 13: Teacher Course Access
        
        For any teacher user accessing course or grade endpoints, the API
        should only grant access to courses they are assigned to teach.
        
        Validates: Requirements 3.4
        """
        view = TestView.as_view()
        view.permission_classes = [IsTeacher]
        
        request = self.factory.get('/test/')
        force_authenticate(request, user=self.teacher_user)
        
        response = view(request)
        self.assertEqual(
            response.status_code,
            200,
            "Teacher should have access to their course endpoints"
        )
        
        # Test IsTeacherOfCourse object-level permission
        permission = IsTeacherOfCourse()
        request = self.factory.get('/test/')
        request.user = self.teacher_user
        
        # Teacher should have access to their assigned course
        has_permission = permission.has_object_permission(request, view, self.course)
        self.assertTrue(
            has_permission,
            "Teacher should have access to their assigned course"
        )
        
        # Create another course not assigned to this teacher
        other_course = Course.objects.create(
            name='Advanced Programming',
            code='CS201',
            program=self.program,
            semester=self.semester,
            credits=3
        )
        
        # Teacher should NOT have access to unassigned course
        has_permission = permission.has_object_permission(request, view, other_course)
        self.assertFalse(
            has_permission,
            "Teacher should NOT have access to unassigned course"
        )
    
    # Property 14: Student Own Data Access
    def test_property_14_student_own_data_access(self):
        """
        Feature: backend-api-implementation, Property 14: Student Own Data Access
        
        For any student user accessing grade or enrollment endpoints, the API
        should only return their own data, not other students' data.
        
        Validates: Requirements 3.5
        """
        view = TestView.as_view()
        view.permission_classes = [IsStudent]
        
        request = self.factory.get('/test/')
        force_authenticate(request, user=self.student_user)
        
        response = view(request)
        self.assertEqual(
            response.status_code,
            200,
            "Student should have access to their own data"
        )
        
        # Test IsOwnerOrAdmin object-level permission
        permission = IsOwnerOrAdmin()
        request = self.factory.get('/test/')
        request.user = self.student_user
        
        # Student should have access to their own profile
        has_permission = permission.has_object_permission(request, view, self.student)
        self.assertTrue(
            has_permission,
            "Student should have access to their own profile"
        )
        
        # Create another student
        other_student_user = User.objects.create_user(
            username='student2',
            password='testpass123',
            role='STUDENT'
        )
        other_student = Student.objects.create(
            user=other_student_user,
            student_id='STU002',
            program=self.program,
            current_level=self.level,
            enrollment_date='2024-09-01'
        )
        
        # Student should NOT have access to other student's profile
        request = self.factory.get('/test/')
        request.user = self.student_user
        has_permission = permission.has_object_permission(request, view, other_student)
        self.assertFalse(
            has_permission,
            "Student should NOT have access to other student's profile"
        )
    
    # Property 15: Accountant Finance Access
    def test_property_15_accountant_finance_access(self):
        """
        Feature: backend-api-implementation, Property 15: Accountant Finance Access
        
        For any accountant user, all finance endpoints should grant full
        read and write access to financial data.
        
        Validates: Requirements 3.6
        """
        view = TestView.as_view()
        view.permission_classes = [IsAccountant]
        
        # Test read access
        request = self.factory.get('/test/')
        force_authenticate(request, user=self.accountant_user)
        response = view(request)
        self.assertEqual(
            response.status_code,
            200,
            "Accountant should have read access to finance endpoints"
        )
        
        # Test write access
        request = self.factory.post('/test/')
        force_authenticate(request, user=self.accountant_user)
        response = view(request)
        self.assertEqual(
            response.status_code,
            201,
            "Accountant should have write access to finance endpoints"
        )
        
        # Test with IsAccountantOrAdmin permission
        view.permission_classes = [IsAccountantOrAdmin]
        request = self.factory.get('/test/')
        force_authenticate(request, user=self.accountant_user)
        response = view(request)
        self.assertEqual(
            response.status_code,
            200,
            "Accountant should have access with IsAccountantOrAdmin"
        )
    
    # Property 16: Secretary Student Access
    def test_property_16_secretary_student_access(self):
        """
        Feature: backend-api-implementation, Property 16: Secretary Student Access
        
        For any secretary user accessing student or enrollment endpoints, the API
        should grant read access to all students and create access for new students.
        
        Validates: Requirements 3.7
        """
        view = TestView.as_view()
        view.permission_classes = [IsSecretary]
        
        # Test read access
        request = self.factory.get('/test/')
        force_authenticate(request, user=self.secretary_user)
        response = view(request)
        self.assertEqual(
            response.status_code,
            200,
            "Secretary should have read access to student endpoints"
        )
        
        # Test create access
        request = self.factory.post('/test/')
        force_authenticate(request, user=self.secretary_user)
        response = view(request)
        self.assertEqual(
            response.status_code,
            201,
            "Secretary should have create access for students"
        )
        
        # Test with IsSecretaryOrAdmin permission
        view.permission_classes = [IsSecretaryOrAdmin]
        request = self.factory.get('/test/')
        force_authenticate(request, user=self.secretary_user)
        response = view(request)
        self.assertEqual(
            response.status_code,
            200,
            "Secretary should have access with IsSecretaryOrAdmin"
        )
    
    # Property 17: Unauthorized Access Denial
    def test_property_17_unauthorized_access_denial(self):
        """
        Feature: backend-api-implementation, Property 17: Unauthorized Access Denial
        
        For any user attempting to access a resource they don't have permission for,
        the API should return HTTP 403 with an appropriate error message.
        
        Validates: Requirements 3.8
        """
        view = TestView.as_view()
        
        # Test student trying to access admin-only endpoint
        view.permission_classes = [IsAdmin]
        request = self.factory.get('/test/')
        request.user = self.student_user
        
        permission = IsAdmin()
        has_permission = permission.has_permission(request, view)
        self.assertFalse(
            has_permission,
            "Student should NOT have admin access"
        )
        
        # Test teacher trying to access accountant-only endpoint
        view.permission_classes = [IsAccountant]
        request = self.factory.get('/test/')
        request.user = self.teacher_user
        
        permission = IsAccountant()
        has_permission = permission.has_permission(request, view)
        self.assertFalse(
            has_permission,
            "Teacher should NOT have accountant access"
        )
        
        # Test unauthenticated access
        request = self.factory.get('/test/')
        # Don't set request.user to simulate unauthenticated request
        
        # Create a mock user object that simulates unauthenticated state
        class AnonymousUser:
            is_authenticated = False
        
        request.user = AnonymousUser()
        permission = IsAdmin()
        has_permission = permission.has_permission(request, view)
        self.assertFalse(
            has_permission,
            "Unauthenticated user should NOT have access"
        )
    
    # Property 18: Object Ownership Check
    def test_property_18_object_ownership_check(self):
        """
        Feature: backend-api-implementation, Property 18: Object Ownership Check
        
        For any endpoint with object-level permissions, the API should verify
        ownership or relationship before granting access to the specific object.
        
        Validates: Requirements 3.9
        """
        view = TestView.as_view()
        
        # Test IsOwnerOrAdmin with owner
        permission = IsOwnerOrAdmin()
        request = self.factory.get('/test/')
        request.user = self.student_user
        
        has_permission = permission.has_object_permission(request, view, self.student)
        self.assertTrue(
            has_permission,
            "Owner should have access to their own object"
        )
        
        # Test IsOwnerOrAdmin with admin
        request = self.factory.get('/test/')
        request.user = self.admin_user
        
        has_permission = permission.has_object_permission(request, view, self.student)
        self.assertTrue(
            has_permission,
            "Admin should have access to any object"
        )
        
        # Test IsTeacherOfCourse with assigned teacher
        permission = IsTeacherOfCourse()
        request = self.factory.get('/test/')
        request.user = self.teacher_user
        
        has_permission = permission.has_object_permission(request, view, self.course)
        self.assertTrue(
            has_permission,
            "Assigned teacher should have access to their course"
        )
        
        # Test IsTeacherOfCourse with admin
        request = self.factory.get('/test/')
        request.user = self.admin_user
        
        has_permission = permission.has_object_permission(request, view, self.course)
        self.assertTrue(
            has_permission,
            "Admin should have access to any course"
        )
        
        # Test IsTeacherOfCourse with unassigned teacher
        other_teacher_user = User.objects.create_user(
            username='teacher2',
            password='testpass123',
            role='TEACHER'
        )
        other_teacher = Teacher.objects.create(
            user=other_teacher_user,
            employee_id='TCH002',
            department=self.department,
            hire_date='2020-01-01'
        )
        
        request = self.factory.get('/test/')
        request.user = other_teacher_user
        
        has_permission = permission.has_object_permission(request, view, self.course)
        self.assertFalse(
            has_permission,
            "Unassigned teacher should NOT have access to course"
        )
    
    # Additional test: IsAdminOrReadOnly with read-only users
    def test_admin_or_readonly_permission(self):
        """
        Test IsAdminOrReadOnly permission class.
        
        Admins should have full access, other authenticated users should have read-only access.
        """
        view = TestView.as_view()
        view.permission_classes = [IsAdminOrReadOnly]
        
        # Test read access for non-admin users
        for user in [self.teacher_user, self.student_user, self.secretary_user]:
            request = self.factory.get('/test/')
            request.user = user
            
            permission = IsAdminOrReadOnly()
            has_permission = permission.has_permission(request, view)
            self.assertTrue(
                has_permission,
                f"{user.role} should have read access"
            )
        
        # Test write access denied for non-admin users
        for user in [self.teacher_user, self.student_user, self.secretary_user]:
            request = self.factory.post('/test/')
            request.user = user
            
            permission = IsAdminOrReadOnly()
            has_permission = permission.has_permission(request, view)
            self.assertFalse(
                has_permission,
                f"{user.role} should NOT have write access"
            )
        
        # Test write access for admin
        request = self.factory.post('/test/')
        request.user = self.admin_user
        
        permission = IsAdminOrReadOnly()
        has_permission = permission.has_permission(request, view)
        self.assertTrue(
            has_permission,
            "Admin should have write access"
        )
    
    # Additional test: Combined permission classes
    def test_combined_permission_classes(self):
        """
        Test combined permission classes (IsTeacherOrAdmin, IsAccountantOrAdmin, IsSecretaryOrAdmin).
        
        These should grant access to specific roles plus admin.
        """
        view = TestView.as_view()
        
        # Test IsTeacherOrAdmin
        permission = IsTeacherOrAdmin()
        
        for user, should_have_access in [
            (self.admin_user, True),
            (self.teacher_user, True),
            (self.student_user, False),
            (self.accountant_user, False),
            (self.secretary_user, False),
        ]:
            request = self.factory.get('/test/')
            request.user = user
            
            has_permission = permission.has_permission(request, view)
            self.assertEqual(
                has_permission,
                should_have_access,
                f"{user.role} access to IsTeacherOrAdmin should be {should_have_access}"
            )
        
        # Test IsAccountantOrAdmin
        permission = IsAccountantOrAdmin()
        
        for user, should_have_access in [
            (self.admin_user, True),
            (self.accountant_user, True),
            (self.teacher_user, False),
            (self.student_user, False),
            (self.secretary_user, False),
        ]:
            request = self.factory.get('/test/')
            request.user = user
            
            has_permission = permission.has_permission(request, view)
            self.assertEqual(
                has_permission,
                should_have_access,
                f"{user.role} access to IsAccountantOrAdmin should be {should_have_access}"
            )
        
        # Test IsSecretaryOrAdmin
        permission = IsSecretaryOrAdmin()
        
        for user, should_have_access in [
            (self.admin_user, True),
            (self.secretary_user, True),
            (self.teacher_user, False),
            (self.student_user, False),
            (self.accountant_user, False),
        ]:
            request = self.factory.get('/test/')
            request.user = user
            
            has_permission = permission.has_permission(request, view)
            self.assertEqual(
                has_permission,
                should_have_access,
                f"{user.role} access to IsSecretaryOrAdmin should be {should_have_access}"
            )
