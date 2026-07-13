from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from rest_framework.test import APIClient

from apps.audit.middleware import AuditMiddleware, get_current_request
from apps.audit.models import AuditLog


User = get_user_model()


class AccountSecurityRegressionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.users = {
            role: User.objects.create_user(
                username=f'{role.lower()}_security',
                email=f'{role.lower()}@example.test',
                password='ComplexPass123!',
                role=role,
            )
            for role in User.Role.values
        }

    def test_me_cannot_change_role_or_activation(self):
        student = self.users[User.Role.STUDENT]
        self.client.force_authenticate(student)

        response = self.client.patch('/api/v1/accounts/me/', {
            'first_name': 'Safe',
            'role': User.Role.ADMIN,
            'is_active': False,
        })

        self.assertEqual(response.status_code, 200)
        student.refresh_from_db()
        self.assertEqual(student.first_name, 'Safe')
        self.assertEqual(student.role, User.Role.STUDENT)
        self.assertTrue(student.is_active)

    def test_delegated_creators_can_only_create_students_and_teachers(self):
        for creator_role in (User.Role.DEAN, User.Role.SECRETARY):
            self.client.force_authenticate(self.users[creator_role])
            for requested_role in User.Role.values:
                response = self.client.post('/api/v1/accounts/users/', {
                    'username': f'{creator_role.lower()}_{requested_role.lower()}',
                    'email': f'{creator_role.lower()}_{requested_role.lower()}@example.test',
                    'password': 'ComplexPass123!',
                    'password_confirm': 'ComplexPass123!',
                    'role': requested_role,
                })
                expected = 201 if requested_role in {
                    User.Role.STUDENT, User.Role.TEACHER
                } else 400
                self.assertEqual(
                    response.status_code,
                    expected,
                    (creator_role, requested_role, response.data),
                )

    def test_non_managers_cannot_create_users(self):
        for role in (User.Role.TEACHER, User.Role.STUDENT, User.Role.ACCOUNTANT):
            self.client.force_authenticate(self.users[role])
            response = self.client.post('/api/v1/accounts/users/', {
                'username': f'forbidden_{role.lower()}',
                'email': f'forbidden_{role.lower()}@example.test',
                'password': 'ComplexPass123!',
                'password_confirm': 'ComplexPass123!',
                'role': User.Role.STUDENT,
            })
            self.assertEqual(response.status_code, 403, role)

    def test_by_role_respects_the_callers_scoped_queryset(self):
        self.client.force_authenticate(self.users[User.Role.STUDENT])
        response = self.client.get('/api/v1/accounts/users/by_role/?role=ADMIN')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

        self.client.force_authenticate(self.users[User.Role.DEAN])
        response = self.client.get('/api/v1/accounts/users/by_role/?role=ADMIN')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])


class AuditRegressionTests(TestCase):
    def test_model_saves_without_http_context_do_not_write_audit_rows(self):
        user = User.objects.create_user(
            username='no_request_audit',
            password='ComplexPass123!',
            role=User.Role.ADMIN,
        )
        user.first_name = 'System change'
        user.save()
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_middleware_always_clears_request_context(self):
        request = RequestFactory().get('/test/')

        def fail(_request):
            raise RuntimeError('expected')

        middleware = AuditMiddleware(fail)
        with self.assertRaises(RuntimeError):
            middleware(request)
        self.assertIsNone(get_current_request())


class CustomActionAuthorizationMatrixTests(TestCase):
    ALL_ROLES = set(User.Role.values)
    STAFF_ROLES = {User.Role.ADMIN, User.Role.DEAN, User.Role.SECRETARY}
    GRADE_ROLES = {User.Role.ADMIN, User.Role.TEACHER}
    FINANCE_ROLES = {User.Role.ADMIN, User.Role.ACCOUNTANT}

    ACTIONS = [
        ('/api/v1/accounts/users/999999/change_password/', ALL_ROLES, {}),
        ('/api/v1/students/999999/promote/', STAFF_ROLES, {}),
        ('/api/v1/students/999999/repeat/', STAFF_ROLES, {}),
        ('/api/v1/students/generate_bulk_id_cards/', STAFF_ROLES, {}),
        ('/api/v1/students/import_excel/', STAFF_ROLES, {}),
        ('/api/v1/students/attendances/record_bulk/', GRADE_ROLES, {}),
        ('/api/v1/university/academic-years/999999/set_current/', STAFF_ROLES, {}),
        ('/api/v1/university/semesters/999999/set_current/', STAFF_ROLES, {}),
        ('/api/v1/university/classrooms/999999/check_availability/', ALL_ROLES, {}),
        ('/api/v1/finance/tuition-payments/999999/approve/', FINANCE_ROLES, {}),
        ('/api/v1/finance/tuition-payments/import_excel/', FINANCE_ROLES, {}),
        ('/api/v1/finance/student-balances/999999/recalculate/', FINANCE_ROLES, {}),
        ('/api/v1/finance/salaries/999999/pay/', FINANCE_ROLES, {}),
        ('/api/v1/finance/salaries/import_excel/', FINANCE_ROLES, {}),
        ('/api/v1/finance/expenses/import_excel/', FINANCE_ROLES, {}),
        ('/api/v1/academics/courses/999999/check_prerequisites/', ALL_ROLES, {}),
        ('/api/v1/academics/grades/bulk_create/', GRADE_ROLES, {}),
        ('/api/v1/academics/grades/import_grades/', GRADE_ROLES, {}),
        ('/api/v1/academics/course-grades/calculate_final_grades/', GRADE_ROLES, {}),
        ('/api/v1/academics/course-grades/999999/validate/', GRADE_ROLES, {}),
        ('/api/v1/academics/course-grades/999999/unvalidate/', GRADE_ROLES, {}),
        ('/api/v1/academics/course-grades/publish/', GRADE_ROLES, {}),
        ('/api/v1/academics/course-grades/unpublish/', GRADE_ROLES, {}),
        ('/api/v1/academics/report-cards/999999/calculate_gpa/', STAFF_ROLES, {}),
        ('/api/v1/academics/report-cards/999999/publish/', STAFF_ROLES, {}),
        ('/api/v1/academics/report-cards/999999/unpublish/', STAFF_ROLES, {}),
        ('/api/v1/academics/report-cards/generate_bulk/', STAFF_ROLES, {}),
        ('/api/v1/academics/deliberation/process/', {User.Role.ADMIN}, {}),
        ('/api/v1/scheduling/schedules/check_conflicts/', STAFF_ROLES, {}),
        ('/api/v1/scheduling/sessions/999999/cancel/', GRADE_ROLES, {}),
        ('/api/v1/scheduling/announcements/999999/publish/', STAFF_ROLES, {}),
    ]

    def setUp(self):
        self.client = APIClient()
        self.users = {
            role: User.objects.create_user(
                username=f'{role.lower()}_matrix',
                password='ComplexPass123!',
                role=role,
            )
            for role in User.Role.values
        }

    def test_every_role_against_every_custom_write_action(self):
        for url, allowed_roles, payload in self.ACTIONS:
            for role, user in self.users.items():
                with self.subTest(url=url, role=role):
                    self.client.force_authenticate(user)
                    response = self.client.post(url, payload, format='json')
                    if role in allowed_roles:
                        self.assertNotEqual(response.status_code, 403, response.data)
                    else:
                        self.assertEqual(response.status_code, 403, response.data)
