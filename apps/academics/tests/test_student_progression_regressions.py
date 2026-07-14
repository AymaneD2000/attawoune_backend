from datetime import date, time
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.academics.models import Course, Exam, Grade
from apps.students.models import Student
from apps.university.models import AcademicYear, Department, Faculty, Level, Program, Semester


class StudentProgressionRegressionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username='progression-admin',
            password='testpass123',
            role=User.Role.ADMIN,
        )
        student_user = User.objects.create_user(
            username='progression-student',
            password='testpass123',
            role=User.Role.STUDENT,
            first_name='Mariam',
            last_name='Diallo',
        )
        faculty = Faculty.objects.create(name='Progress Faculty', code='PROG-FAC')
        department = Department.objects.create(name='Progress Department', code='PROG-DEP', faculty=faculty)
        level, _ = Level.objects.get_or_create(name='L1', defaults={'order': 1})
        program = Program.objects.create(name='Progress Program', code='PROG-PROG', department=department)
        program.levels.add(level)
        self.student = Student.objects.create(
            user=student_user,
            student_id='PROGRESS-1',
            program=program,
            current_level=level,
            enrollment_date=date(2025, 9, 1),
        )
        academic_year = AcademicYear.objects.create(
            name='2025-2026',
            start_date=date(2025, 9, 1),
            end_date=date(2026, 8, 31),
            is_current=True,
        )
        semester = Semester.objects.create(
            academic_year=academic_year,
            semester_type='S1',
            start_date=date(2025, 9, 1),
            end_date=date(2026, 1, 31),
            is_current=True,
        )
        course = Course.objects.create(
            name='Analyse',
            code='PROG-MATH-101',
            program=program,
            course_type=Course.CourseType.REQUIRED,
            credits=4,
            semester_type='S1',
            level=level,
        )

        quiz = Exam.objects.create(
            course=course,
            exam_type=Exam.ExamType.QUIZ,
            semester=semester,
            date=date(2025, 10, 1),
            start_time=time(8, 0),
            end_time=time(9, 0),
            max_score=Decimal('10.00'),
            weight=Decimal('0.30'),
        )
        final = Exam.objects.create(
            course=course,
            exam_type=Exam.ExamType.FINAL,
            semester=semester,
            date=date(2025, 12, 15),
            start_time=time(8, 0),
            end_time=time(10, 0),
            max_score=Decimal('20.00'),
            weight=Decimal('0.70'),
        )
        Grade.objects.create(
            student=self.student,
            exam=quiz,
            score=Decimal('8.00'),
            remarks='Bon devoir',
            graded_by=self.admin,
        )
        Grade.objects.create(
            student=self.student,
            exam=final,
            score=Decimal('10.00'),
            remarks='Résultat satisfaisant',
            graded_by=self.admin,
        )
        self.client.force_authenticate(self.admin)

    def test_history_normalizes_different_exam_scales_and_exposes_progression_fields(self):
        response = self.client.get(
            '/api/v1/academics/grades/student_history/',
            {'student_id': self.student.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['stats']['avg_score'], 13.0)
        self.assertEqual(response.data['stats']['pass_rate'], 100.0)
        self.assertEqual(response.data['stats']['total_exams'], 2)
        self.assertEqual([grade['exam_type'] for grade in response.data['grades']], ['QUIZ', 'FINAL'])

        first_grade = response.data['grades'][0]
        self.assertEqual(first_grade['exam_date'], '2025-10-01')
        self.assertEqual(Decimal(first_grade['max_score']), Decimal('10.00'))
        self.assertEqual(first_grade['remarks'], 'Bon devoir')
        self.assertEqual(Decimal(first_grade['percentage']), Decimal('80.00'))

        breakdown = {item['type']: item for item in response.data['type_breakdown']}
        self.assertEqual(breakdown['QUIZ']['average_score'], 16.0)
        self.assertEqual(breakdown['FINAL']['average_score'], 10.0)
