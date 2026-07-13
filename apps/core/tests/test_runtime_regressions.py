from datetime import date

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.academics.models import Course
from apps.scheduling.models import CourseSession, Schedule, TimeSlot
from apps.students.models import Enrollment, Student
from apps.teachers.models import Teacher, TeacherCourse
from apps.university.models import AcademicYear, Department, Faculty, Level, Program, Semester


class AttendanceAndDashboardRuntimeRegressionTests(TestCase):
    def setUp(self):
        self.teacher_user = User.objects.create_user(
            username='runtime_teacher', password='ComplexPass123!', role='TEACHER'
        )
        self.other_teacher_user = User.objects.create_user(
            username='runtime_other_teacher', password='ComplexPass123!', role='TEACHER'
        )
        self.student_user = User.objects.create_user(
            username='runtime_student', password='ComplexPass123!', role='STUDENT'
        )
        self.year = AcademicYear.objects.create(
            name='2096-2097', start_date=date(2096, 9, 1),
            end_date=date(2097, 7, 1), is_current=True,
        )
        self.semester = Semester.objects.create(
            academic_year=self.year, semester_type='S1',
            start_date=date(2096, 9, 1), end_date=date(2097, 1, 31),
            is_current=True,
        )
        faculty = Faculty.objects.create(name='Runtime Faculty', code='RTF')
        department = Department.objects.create(
            name='Runtime Department', code='RTD', faculty=faculty,
        )
        level = Level.objects.get_or_create(name='L1', defaults={'order': 1})[0]
        program = Program.objects.create(
            name='Runtime Program', code='RTP', department=department,
            duration_years=1,
        )
        program.levels.add(level)
        self.student = Student.objects.create(
            user=self.student_user, student_id='RTS0001', program=program,
            current_level=level, enrollment_date=date(2096, 9, 1),
        )
        Enrollment.objects.create(
            student=self.student, academic_year=self.year, program=program,
            level=level, is_active=True,
        )
        self.teacher = Teacher.objects.create(
            user=self.teacher_user, employee_id='RTT0001',
            department=department, hire_date=date(2090, 1, 1),
        )
        Teacher.objects.create(
            user=self.other_teacher_user, employee_id='RTT0002',
            department=department, hire_date=date(2090, 1, 1),
        )
        course = Course.objects.create(
            name='Runtime Course', code='RTC101', program=program,
            level=level, semester_type='S1', credits=3,
        )
        TeacherCourse.objects.create(
            teacher=self.teacher, course=course, semester=self.semester,
        )
        time_slot = TimeSlot.objects.create(
            day=timezone.localdate().weekday(), start_time='08:00', end_time='10:00'
        )
        schedule = Schedule.objects.create(
            course=course, teacher=self.teacher, semester=self.semester,
            time_slot=time_slot, is_active=True,
        )
        self.session = CourseSession.objects.create(
            schedule=schedule, date=timezone.localdate(),
        )
        self.client = APIClient()

    def test_teacher_and_student_dashboards_use_real_model_relations(self):
        self.client.force_authenticate(self.teacher_user)
        teacher_response = self.client.get('/api/v1/university/dashboard/')
        self.assertEqual(teacher_response.status_code, 200, teacher_response.data)
        self.assertEqual(teacher_response.data['courses_count'], 1)
        self.assertEqual(len(teacher_response.data['schedule']), 1)

        self.client.force_authenticate(self.student_user)
        student_response = self.client.get('/api/v1/university/dashboard/')
        self.assertEqual(student_response.status_code, 200, student_response.data)
        self.assertEqual(student_response.data['courses_count'], 1)
        self.assertEqual(len(student_response.data['schedule']), 1)

    def test_single_attendance_requires_the_scheduled_teacher(self):
        payload = {
            'student': self.student.id,
            'course_session': self.session.id,
            'status': 'PRESENT',
        }
        self.client.force_authenticate(self.other_teacher_user)
        denied = self.client.post('/api/v1/students/attendances/', payload)
        self.assertEqual(denied.status_code, 403, denied.data)

        self.client.force_authenticate(self.teacher_user)
        allowed = self.client.post('/api/v1/students/attendances/', payload)
        self.assertEqual(allowed.status_code, 201, allowed.data)
