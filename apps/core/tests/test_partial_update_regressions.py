from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.academics.models import Course
from apps.students.models import Student
from apps.teachers.models import Teacher
from apps.university.models import Department, Faculty, Level, Program


class PartialUpdateRegressionTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='partial_admin', password='ComplexPass123!', role='ADMIN'
        )
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

        faculty = Faculty.objects.create(name='Partial Faculty', code='PAF')
        self.department = Department.objects.create(
            name='Partial Department', code='PAD', faculty=faculty,
        )
        self.level = Level.objects.get_or_create(
            name='L1', defaults={'order': 1}
        )[0]
        self.program = Program.objects.create(
            name='Partial Program', code='PAP', department=self.department,
            duration_years=3, tuition_fee=Decimal('500000.00'),
        )
        self.program.levels.add(self.level)

        self.student_user = User.objects.create_user(
            username='partial_student', password='ComplexPass123!',
            role='STUDENT', first_name='Mariam', last_name='Diallo',
            email='mariam@example.test', gender='F', phone='70000000',
            address='Bamako',
        )
        self.student = Student.objects.create(
            user=self.student_user, student_id='PARTIALS001',
            program=self.program, current_level=self.level,
            enrollment_date=date(2026, 9, 1), status='ACTIVE',
            guardian_name='Parent Diallo', guardian_phone='71000000',
            emergency_contact='72000000',
        )

        self.teacher_user = User.objects.create_user(
            username='partial_teacher', password='ComplexPass123!',
            role='TEACHER', first_name='Awa', last_name='Keita',
            email='awa@example.test', gender='F', phone='73000000',
            address='Sotuba',
        )
        self.teacher = Teacher.objects.create(
            user=self.teacher_user, employee_id='PARTIALT001',
            department=self.department, rank='LECTURER',
            contract_type='PERMANENT', hire_date=date(2020, 9, 1),
            specialization='Mathématiques', office_location='B12',
            is_active=True,
        )
        self.course = Course.objects.create(
            name='Analyse', code='PARTIALC001', program=self.program,
            level=self.level, course_type='REQUIRED', credits=4,
            coefficient=Decimal('2.0'), hours_lecture=40,
            hours_tutorial=12, hours_practical=4, semester_type='S1',
            description='Cours initial', is_active=True,
        )

    def test_user_patch_changes_only_requested_attribute(self):
        response = self.client.patch(
            f'/api/v1/accounts/users/{self.student_user.id}/',
            {'first_name': 'Aminata'}, format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)

        self.student_user.refresh_from_db()
        self.assertEqual(self.student_user.first_name, 'Aminata')
        self.assertEqual(self.student_user.last_name, 'Diallo')
        self.assertEqual(self.student_user.email, 'mariam@example.test')
        self.assertEqual(self.student_user.gender, 'F')
        self.assertEqual(self.student_user.role, 'STUDENT')
        self.assertEqual(self.student_user.address, 'Bamako')

    def test_student_and_teacher_patch_preserve_unmentioned_profile_fields(self):
        student_response = self.client.patch(
            f'/api/v1/students/{self.student.id}/',
            {'guardian_phone': '79999999'}, format='json',
        )
        self.assertEqual(student_response.status_code, 200, student_response.data)
        self.student.refresh_from_db()
        self.assertEqual(self.student.guardian_phone, '79999999')
        self.assertEqual(self.student.guardian_name, 'Parent Diallo')
        self.assertEqual(self.student.emergency_contact, '72000000')
        self.assertEqual(self.student.program, self.program)
        self.assertEqual(self.student.current_level, self.level)
        self.assertEqual(self.student.status, 'ACTIVE')

        teacher_response = self.client.patch(
            f'/api/v1/teachers/teachers/{self.teacher.id}/',
            {'first_name': 'Aissata'}, format='json',
        )
        self.assertEqual(teacher_response.status_code, 200, teacher_response.data)
        self.teacher.refresh_from_db()
        self.teacher_user.refresh_from_db()
        self.assertEqual(self.teacher_user.first_name, 'Aissata')
        self.assertEqual(self.teacher_user.last_name, 'Keita')
        self.assertEqual(self.teacher_user.gender, 'F')
        self.assertEqual(self.teacher.specialization, 'Mathématiques')
        self.assertEqual(self.teacher.rank, 'LECTURER')
        self.assertEqual(self.teacher.office_location, 'B12')

    def test_course_patch_preserves_unmentioned_academic_fields(self):
        response = self.client.patch(
            f'/api/v1/academics/courses/{self.course.id}/',
            {'name': 'Analyse avancée'}, format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)

        self.course.refresh_from_db()
        self.assertEqual(self.course.name, 'Analyse avancée')
        self.assertEqual(self.course.code, 'PARTIALC001')
        self.assertEqual(self.course.credits, 4)
        self.assertEqual(self.course.coefficient, Decimal('2.0'))
        self.assertEqual(self.course.hours_lecture, 40)
        self.assertEqual(self.course.hours_tutorial, 12)
        self.assertEqual(self.course.hours_practical, 4)
        self.assertEqual(self.course.semester_type, 'S1')
