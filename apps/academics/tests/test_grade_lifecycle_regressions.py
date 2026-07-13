from datetime import date, time
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.academics.models import Course, CourseGrade, Exam, ReportCard
from apps.students.models import Enrollment, Student
from apps.teachers.models import Teacher, TeacherCourse
from apps.university.models import AcademicYear, Department, Faculty, Level, Program, Semester


class GradeLifecycleRegressionTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='grade_admin', password='ComplexPass123!', role='ADMIN'
        )
        self.teacher_user = User.objects.create_user(
            username='grade_teacher', password='ComplexPass123!', role='TEACHER'
        )
        self.student_user = User.objects.create_user(
            username='grade_student', password='ComplexPass123!', role='STUDENT'
        )
        self.year = AcademicYear.objects.create(
            name='2098-2099', start_date=date(2098, 9, 1),
            end_date=date(2099, 7, 1), is_current=True,
        )
        self.semester = Semester.objects.create(
            academic_year=self.year, semester_type='S1',
            start_date=date(2098, 9, 1), end_date=date(2099, 1, 31),
            is_current=True,
        )
        self.faculty = Faculty.objects.create(name='Lifecycle Faculty', code='GLF')
        self.department = Department.objects.create(
            name='Lifecycle Department', code='GLD', faculty=self.faculty,
        )
        self.level = Level.objects.get_or_create(name='L1', defaults={'order': 1})[0]
        self.program = Program.objects.create(
            name='Lifecycle Program', code='GLP', department=self.department,
            duration_years=1, tuition_fee=Decimal('1000.00'),
        )
        self.program.levels.add(self.level)
        self.student = Student.objects.create(
            user=self.student_user, student_id='GLS0001', program=self.program,
            current_level=self.level, enrollment_date=date(2098, 9, 1),
        )
        Enrollment.objects.create(
            student=self.student, academic_year=self.year, program=self.program,
            level=self.level, is_active=True,
        )
        self.teacher = Teacher.objects.create(
            user=self.teacher_user, employee_id='GLT0001',
            department=self.department, hire_date=date(2090, 1, 1),
        )
        self.course = Course.objects.create(
            name='Lifecycle Course', code='GLC101', program=self.program,
            level=self.level, semester_type='S1', credits=4,
        )
        TeacherCourse.objects.create(
            teacher=self.teacher, course=self.course, semester=self.semester,
        )
        self.exam = Exam.objects.create(
            course=self.course, exam_type='FINAL', semester=self.semester,
            date=date(2099, 1, 10), start_time=time(9), end_time=time(11),
            max_score=Decimal('20.00'), weight=Decimal('1.00'),
        )
        self.client = APIClient()
        self.client.force_authenticate(self.teacher_user)

    def test_grade_mutation_invalidates_validation_and_publication(self):
        response = self.client.post('/api/v1/academics/grades/', {
            'student': self.student.id,
            'exam': self.exam.id,
            'score': '16.00',
            'is_absent': False,
        })
        self.assertEqual(response.status_code, 201, response.data)

        course_grade = CourseGrade.objects.get(
            student=self.student, course=self.course, semester=self.semester
        )
        response = self.client.post(
            f'/api/v1/academics/course-grades/{course_grade.id}/validate/'
        )
        self.assertEqual(response.status_code, 200, response.data)
        response = self.client.post('/api/v1/academics/course-grades/publish/', {
            'course_id': self.course.id,
            'semester_id': self.semester.id,
        })
        self.assertEqual(response.status_code, 200, response.data)

        report_card = ReportCard.objects.create(
            student=self.student, semester=self.semester, generated_by=self.admin
        )
        report_card.calculate_gpa()
        report_card.is_published = True
        report_card.save(update_fields=['is_published'])

        response = self.client.patch(
            f"/api/v1/academics/grades/{self.exam.grades.get(student=self.student).id}/",
            {'score': '12.00'},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)

        course_grade.refresh_from_db()
        report_card.refresh_from_db()
        self.assertEqual(course_grade.final_score, Decimal('12.00'))
        self.assertFalse(course_grade.is_validated)
        self.assertIsNone(course_grade.validated_by)
        self.assertFalse(course_grade.is_published)
        self.assertFalse(report_card.is_published)
        self.assertEqual(report_card.gpa, Decimal('0.00'))

    def test_unvalidate_is_an_explicit_reversal(self):
        self.client.post('/api/v1/academics/grades/', {
            'student': self.student.id, 'exam': self.exam.id, 'score': '14.00'
        })
        course_grade = CourseGrade.objects.get(student=self.student, course=self.course)
        self.client.post(f'/api/v1/academics/course-grades/{course_grade.id}/validate/')
        self.client.post('/api/v1/academics/course-grades/publish/', {
            'course_id': self.course.id, 'semester_id': self.semester.id,
        })

        response = self.client.post(
            f'/api/v1/academics/course-grades/{course_grade.id}/unvalidate/'
        )
        self.assertEqual(response.status_code, 200, response.data)
        course_grade.refresh_from_db()
        self.assertFalse(course_grade.is_validated)
        self.assertFalse(course_grade.is_published)
        self.assertIsNone(course_grade.validated_at)
        self.assertIsNone(course_grade.published_at)
