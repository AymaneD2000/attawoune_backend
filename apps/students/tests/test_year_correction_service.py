"""
Academic-year correction service tests (Task 1 of the correction plan).

The service moves a newly created student from a mistaken academic year to
the correct year: it regenerates the matricule, recreates the target-year
financial balance, and removes the source-year enrollment and empty balance.
Students with academic or financial history in the source year are blocked
for manual review.
"""

from datetime import date, time
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.university.models import (
    AcademicYear, Faculty, Program, Department, Level, ProgramFee, Semester,
)

from apps.students.models import Student, Enrollment, StudentPromotion, Attendance
from apps.finance.models import StudentBalance, StudentDebt, TuitionPayment
from apps.academics.models import Course, CourseGrade, Exam, Grade, ReportCard
from apps.scheduling.models import CourseSession, Schedule, TimeSlot
from apps.teachers.models import Teacher

from apps.students.services.year_correction import (
    CorrectionBlocked,
    correct_student_academic_year,
)

User = get_user_model()


class MatriculeRegenerationTests(TestCase):
    """`Student.regenerate_student_id_for_year()` model helper."""

    def setUp(self):
        self.user_a = User.objects.create_user(
            username='cy_amina',
            email='cy_amina@test.com',
            password='testpass123',
            first_name='Amina',
            last_name='Corr',
            role='STUDENT',
            gender='M',
        )

        self.level_l1, _ = Level.objects.get_or_create(name='L1', defaults={'order': 1})

        self.faculty = Faculty.objects.create(name='CY Faculty', code='CYF')
        self.department = Department.objects.create(name='CY Dept', code='CYD', faculty=self.faculty)
        self.program = Program.objects.create(
            name='CY Program',
            code='CY-PG',
            department=self.department,
            tuition_fee=Decimal('300000.00'),
        )
        self.program.levels.add(self.level_l1)

        self.target_year = AcademicYear.objects.create(
            name='2026-27CY',
            start_date=date(2026, 9, 1),
            end_date=date(2027, 6, 30),
        )

        # The student being corrected holds a 2526 matricule.
        self.student = Student.objects.create(
            user=self.user_a,
            student_id='CYF2526MA000001',
            program=self.program,
            current_level=self.level_l1,
            enrollment_date=date(2025, 9, 1),
        )

        # An existing student occupies the 2627 sequence slot 4.
        user_x = User.objects.create_user(
            username='cy_existing',
            email='cy_existing@test.com',
            password='testpass123',
            first_name='Amina',
            last_name='Corr',
            role='STUDENT',
            gender='M',
        )
        self.existing = Student.objects.create(
            user=user_x,
            student_id='CYF2627MA000004',
            program=self.program,
            current_level=self.level_l1,
            enrollment_date=date(2026, 9, 1),
        )

    def test_regenerate_student_id_uses_target_year_and_next_sequence(self):
        old_id = self.student.student_id

        returned_old, returned_new = self.student.regenerate_student_id_for_year(self.target_year)

        self.student.refresh_from_db()
        self.assertEqual(returned_old, old_id)
        self.assertEqual(returned_new, 'CYF2627MA000005')
        self.assertEqual(self.student.student_id, returned_new)
        self.assertNotEqual(self.existing.student_id, returned_new)

    def test_regenerate_preserves_faculty_gender_initial_prefix(self):
        _, new_id = self.student.regenerate_student_id_for_year(self.target_year)
        self.assertTrue(new_id.startswith('CYF2627M'), new_id)

    def test_generate_student_id_behavior_unchanged(self):
        """Existing creation path keeps its 2526-style generation."""
        user_b = User.objects.create_user(
            username='cy_bina',
            email='cy_bina@test.com',
            password='testpass123',
            first_name='Bina',
            last_name='Corr',
            role='STUDENT',
            gender='F',
        )
        student = Student.objects.create(
            user=user_b,
            program=self.program,
            current_level=self.level_l1,
            enrollment_date=date(2025, 9, 1),
        )
        self.assertTrue(student.student_id.startswith('CYF2526F'), student.student_id)
        self.assertEqual(len(student.student_id[-6:]), 6)


class YearCorrectionServiceTests(TestCase):
    """correct_student_academic_year() domain service (single-student atomics)."""

    def setUp(self):
        self.user_a = User.objects.create_user(
            username='cy_svc_amina',
            email='cy_svc_amina@test.com',
            password='testpass123',
            first_name='Amina',
            last_name='Corr',
            role='STUDENT',
            gender='M',
        )

        self.level_l1, _ = Level.objects.get_or_create(name='L1', defaults={'order': 1})

        self.faculty = Faculty.objects.create(name='CYS Faculty', code='CYF')
        self.department = Department.objects.create(name='CYS Dept', code='CYD', faculty=self.faculty)
        self.program = Program.objects.create(
            name='CYS Program',
            code='CY-PG',
            department=self.department,
            tuition_fee=Decimal('300000.00'),
        )
        self.program.levels.add(self.level_l1)

        self.source_year = AcademicYear.objects.create(
            name='2025-26CY',
            start_date=date(2025, 9, 1),
            end_date=date(2026, 6, 30),
        )
        self.target_year = AcademicYear.objects.create(
            name='2026-27CY',
            start_date=date(2026, 9, 1),
            end_date=date(2027, 6, 30),
        )
        # Keep a single is_current context so student-creation signals stay out of the way.
        AcademicYear.objects.exclude(pk__in=[self.source_year.pk, self.target_year.pk]).update(is_current=False)

        # Exact target-year fee for the target level.
        ProgramFee.objects.create(
            program=self.program,
            level=self.level_l1,
            academic_year=self.target_year,
            amount=Decimal('123456.00'),
        )

        self.student = Student.objects.create(
            user=self.user_a,
            student_id='CYF2526MA000010',
            program=self.program,
            current_level=self.level_l1,
            enrollment_date=date(2025, 9, 1),
        )
        self.source_enrollment = Enrollment.objects.create(
            student=self.student,
            academic_year=self.source_year,
            program=self.program,
            level=self.level_l1,
            status='ENROLLED',
        )
        self.source_balance = StudentBalance.objects.create(
            student=self.student,
            academic_year=self.source_year,
            total_due=Decimal('300000.00'),
            total_paid=Decimal('0.00'),
        )

        # Source-year academic fixtures (used by the blocker tests).
        self.semester_s1 = Semester.objects.create(
            academic_year=self.source_year,
            semester_type='S1',
            start_date=date(2025, 9, 1),
            end_date=date(2025, 12, 20),
        )
        self.course = Course.objects.create(
            name='CYS Course',
            code='CY-C1',
            program=self.program,
            level=self.level_l1,
            semester_type='S1',
        )

        teacher_user = User.objects.create_user(
            username='cy_svc_teacher',
            email='cy_svc_teacher@test.com',
            password='testpass123',
            role='TEACHER',
        )
        self.teacher = Teacher.objects.create(
            user=teacher_user,
            employee_id='CY-T1',
            department=self.department,
            hire_date=date(2020, 1, 1),
        )

    def _run_correction(self):
        return correct_student_academic_year(
            student_id=self.student.pk,
            source_year=self.source_year,
            target_year=self.target_year,
            enrollment_date=date(2026, 10, 22),
        )

    def _assert_blocked_and_unchanged(self, expect_source_records=True, target_enrollment_expected=False):
        with self.assertRaises(CorrectionBlocked):
            self._run_correction()
        self.student.refresh_from_db()
        self.assertEqual(self.student.student_id, 'CYF2526MA000010')
        self.assertEqual(self.student.enrollment_date, date(2025, 9, 1))
        if expect_source_records:
            self.assertTrue(Enrollment.objects.filter(pk=self.source_enrollment.pk).exists())
            self.assertTrue(StudentBalance.objects.filter(pk=self.source_balance.pk).exists())
        if target_enrollment_expected:
            self.assertTrue(
                Enrollment.objects.filter(student=self.student, academic_year=self.target_year).exists()
            )
        else:
            self.assertFalse(
                Enrollment.objects.filter(student=self.student, academic_year=self.target_year).exists()
            )

    # ------------------------------------------------------------------
    # Successful correction
    # ------------------------------------------------------------------

    def test_successful_correction_moves_student_to_target_year(self):
        result = self._run_correction()

        # Source-year records are gone.
        self.assertFalse(
            Enrollment.objects.filter(student=self.student, academic_year=self.source_year).exists()
        )
        self.assertFalse(
            StudentBalance.objects.filter(student=self.student, academic_year=self.source_year).exists()
        )

        # Target-year records are created.
        target_enrollment = Enrollment.objects.get(student=self.student, academic_year=self.target_year)
        self.assertEqual(target_enrollment.level, self.level_l1)
        self.assertEqual(target_enrollment.status, 'ENROLLED')
        self.assertTrue(target_enrollment.is_active)
        self.assertEqual(
            StudentBalance.objects.get(student=self.student, academic_year=self.target_year).total_due,
            Decimal('123456.00'),
        )

        # Profile corrections.
        self.student.refresh_from_db()
        self.assertEqual(self.student.enrollment_date, date(2026, 10, 22))
        self.assertEqual(self.student.current_level, self.level_l1)
        self.assertEqual(self.student.program, self.program)

        # Matricule regeneration + result payload.
        self.assertEqual(result.student, self.student.pk)
        self.assertEqual(result.name, self.student.user.get_full_name())
        self.assertEqual(result.old_student_id, 'CYF2526MA000010')
        self.assertIn('2627', result.new_student_id)
        self.assertEqual(self.student.student_id, result.new_student_id)

    def test_nonexistent_student_is_blocked_without_side_effects(self):
        with self.assertRaises(CorrectionBlocked):
            correct_student_academic_year(
                student_id=999999,
                source_year=self.source_year,
                target_year=self.target_year,
                enrollment_date=date(2026, 10, 22),
            )
        self.assertEqual(Enrollment.objects.filter(student=self.student).count(), 1)

    # ------------------------------------------------------------------
    # Blockers (one test case each) — data must remain untouched
    # ------------------------------------------------------------------

    def test_blocked_without_source_enrollment(self):
        self.source_enrollment.delete()
        self._assert_blocked_and_unchanged(expect_source_records=False)

    def test_blocked_when_enrolled_in_target_year(self):
        Enrollment.objects.create(
            student=self.student,
            academic_year=self.target_year,
            program=self.program,
            level=self.level_l1,
            status='ENROLLED',
        )
        self._assert_blocked_and_unchanged(target_enrollment_expected=True)

    def test_blocked_with_multiple_year_history(self):
        other_year = AcademicYear.objects.create(
            name='2024-25CY',
            start_date=date(2024, 9, 1),
            end_date=date(2025, 6, 30),
        )
        Enrollment.objects.create(
            student=self.student,
            academic_year=other_year,
            program=self.program,
            level=self.level_l1,
            status='ENROLLED',
        )
        self._assert_blocked_and_unchanged()

    def test_blocked_with_source_year_tuition_payment(self):
        TuitionPayment.objects.create(
            student=self.student,
            academic_year=self.source_year,
            amount=Decimal('10000.00'),
            reference='CY-BLK-PAY',
            payment_date=date(2025, 10, 1),
            status='COMPLETED',
        )
        self._assert_blocked_and_unchanged()

    def test_blocked_with_paid_source_balance(self):
        self.source_balance.total_paid = Decimal('50000.00')
        self.source_balance.save()
        self._assert_blocked_and_unchanged()

    def test_blocked_with_source_year_debt(self):
        StudentDebt.objects.create(
            student=self.student,
            academic_year=self.source_year,
            amount_due=Decimal('1000.00'),
        )
        self._assert_blocked_and_unchanged()

    def test_blocked_with_source_year_exam_grade(self):
        exam = Exam.objects.create(
            course=self.course,
            exam_type='FINAL',
            semester=self.semester_s1,
            date=date(2025, 12, 15),
            start_time=time(8, 0),
            end_time=time(10, 0),
        )
        Grade.objects.create(student=self.student, exam=exam, score=Decimal('12.00'))
        self._assert_blocked_and_unchanged()

    def test_blocked_with_source_year_course_grade(self):
        CourseGrade.objects.create(
            student=self.student,
            course=self.course,
            semester=self.semester_s1,
            final_score=Decimal('12.00'),
        )
        self._assert_blocked_and_unchanged()

    def test_blocked_with_source_year_attendance(self):
        time_slot = TimeSlot.objects.create(
            day=0,
            start_time=time(8, 0),
            end_time=time(10, 0),
        )
        schedule = Schedule.objects.create(
            course=self.course,
            teacher=self.teacher,
            semester=self.semester_s1,
            time_slot=time_slot,
        )
        course_session = CourseSession.objects.create(schedule=schedule, date=date(2025, 9, 10))
        Attendance.objects.create(student=self.student, course_session=course_session, status='PRESENT')
        self._assert_blocked_and_unchanged()

    def test_blocked_with_source_year_report_card(self):
        ReportCard.objects.create(student=self.student, semester=self.semester_s1)
        self._assert_blocked_and_unchanged()

    def test_blocked_with_source_year_deliberation(self):
        StudentPromotion.objects.create(
            student=self.student,
            academic_year=self.source_year,
            program=self.program,
            level_from=self.level_l1,
            level_to=self.level_l1,
            annual_gpa=Decimal('8.00'),
            decision='REPEATED',
        )
        self._assert_blocked_and_unchanged()
