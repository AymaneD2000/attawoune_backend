from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.students.models import StudentPromotion
from apps.teachers.models import TeacherCourse

from ..models import CourseGrade, Grade, ReportCard


def ensure_course_access(actor, course, semester):
    """Ensure an actor may manage grades for this exact course assignment."""
    if actor.role == 'ADMIN':
        return
    if actor.role == 'TEACHER' and TeacherCourse.objects.filter(
        teacher__user=actor,
        course=course,
        semester=semester,
    ).exists():
        return
    raise PermissionDenied("Vous n'êtes pas assigné à ce cours pour ce semestre.")


def ensure_academic_year_open(semester):
    if not semester.academic_year.is_current:
        raise ValidationError(
            "Impossible de modifier les notes d'une année académique inactive."
        )


def validate_grade_mutation(*, actor, student, exam):
    ensure_course_access(actor, exam.course, exam.semester)
    ensure_academic_year_open(exam.semester)

    if student.program_id != exam.course.program_id:
        raise ValidationError({
            'student': "L'étudiant n'appartient pas au programme de ce cours."
        })

    if StudentPromotion.objects.filter(
        student=student,
        academic_year=exam.semester.academic_year,
    ).exists():
        raise ValidationError(
            "Impossible de modifier les notes : l'étudiant a déjà été délibéré "
            "pour cette année."
        )


@transaction.atomic
def save_grade(*, actor, validated_data, instance=None):
    """Create/update one exam grade through the shared authorization rules."""
    if instance is not None:
        instance = Grade.objects.select_for_update().select_related(
            'student', 'exam__course', 'exam__semester__academic_year'
        ).get(pk=instance.pk)
        previous_student = instance.student
        previous_exam = instance.exam
        # A grade cannot be moved out of a locked context as a workaround.
        validate_grade_mutation(actor=actor, student=instance.student, exam=instance.exam)

    student = validated_data.get('student', getattr(instance, 'student', None))
    exam = validated_data.get('exam', getattr(instance, 'exam', None))
    validate_grade_mutation(actor=actor, student=student, exam=exam)

    if instance is None:
        return Grade.objects.create(
            **validated_data,
            graded_by=actor,
        )

    for field, value in validated_data.items():
        setattr(instance, field, value)
    instance.graded_by = actor
    instance.save()
    if (
        previous_student.pk != instance.student_id
        or previous_exam.pk != instance.exam_id
    ):
        recalculate_course_grade(
            previous_student,
            previous_exam.course,
            previous_exam.semester,
        )
    return instance


@transaction.atomic
def delete_grade(*, actor, grade):
    grade = Grade.objects.select_for_update().select_related(
        'student', 'exam__course', 'exam__semester__academic_year'
    ).get(pk=grade.pk)
    validate_grade_mutation(actor=actor, student=grade.student, exam=grade.exam)
    grade.delete()


def _weighted_score(grades):
    total_weighted_score = Decimal('0.00')
    total_weight = Decimal('0.00')

    for grade in grades:
        exam = grade.exam
        if exam.weight <= 0 or exam.max_score <= 0:
            continue
        score = Decimal('0.00') if grade.is_absent else grade.score
        normalized_score = (score / exam.max_score) * Decimal('20.00')
        total_weighted_score += normalized_score * exam.weight
        total_weight += exam.weight

    if total_weight == 0:
        return Decimal('0.00')
    return (total_weighted_score / total_weight).quantize(Decimal('0.01'))


def _invalidate_report_card(student, semester):
    report_card = ReportCard.objects.filter(
        student=student,
        semester=semester,
    ).first()
    if report_card:
        report_card.calculate_gpa()


@transaction.atomic
def recalculate_course_grade(student, course, semester):
    """Rebuild a derived grade and explicitly invalidate its lifecycle state."""
    student_id = getattr(student, 'pk', student)
    course_id = getattr(course, 'pk', course)
    semester_id = getattr(semester, 'pk', semester)
    grades = list(Grade.objects.filter(
        student_id=student_id,
        exam__course_id=course_id,
        exam__semester_id=semester_id,
    ).select_related('exam'))

    existing = CourseGrade.objects.select_for_update().filter(
        student_id=student_id,
        course_id=course_id,
        semester_id=semester_id,
    ).first()

    if not grades:
        if existing:
            existing.delete()
        _invalidate_report_card(student_id, semester_id)
        return None, False

    final_score = _weighted_score(grades)
    created = existing is None
    course_grade = existing or CourseGrade(
        student_id=student_id,
        course_id=course_id,
        semester_id=semester_id,
    )
    course_grade.final_score = final_score
    course_grade.is_validated = False
    course_grade.validated_by = None
    course_grade.validated_at = None
    course_grade.is_published = False
    course_grade.published_at = None
    course_grade.save()
    _invalidate_report_card(student_id, semester_id)
    return course_grade, created


def recalculate_exam_course_grades(exam):
    student_ids = Grade.objects.filter(
        exam__course=exam.course,
        exam__semester=exam.semester,
    ).values_list('student_id', flat=True).distinct()
    for student_id in student_ids:
        recalculate_course_grade(student_id, exam.course, exam.semester)


@transaction.atomic
def save_course_grade(*, actor, validated_data, instance=None):
    """Guard the legacy manual CourseGrade write endpoints."""
    if instance is not None:
        instance = CourseGrade.objects.select_for_update().select_related(
            'student', 'course', 'semester__academic_year'
        ).get(pk=instance.pk)
        ensure_course_access(actor, instance.course, instance.semester)
        ensure_academic_year_open(instance.semester)
        previous_student = instance.student
        previous_semester = instance.semester

    student = validated_data.get('student', getattr(instance, 'student', None))
    course = validated_data.get('course', getattr(instance, 'course', None))
    semester = validated_data.get('semester', getattr(instance, 'semester', None))
    ensure_course_access(actor, course, semester)
    ensure_academic_year_open(semester)

    if student.program_id != course.program_id:
        raise ValidationError({
            'student': "L'étudiant n'appartient pas au programme de ce cours."
        })
    if StudentPromotion.objects.filter(
        student=student,
        academic_year=semester.academic_year,
    ).exists():
        raise ValidationError("L'étudiant a déjà été délibéré pour cette année.")

    course_grade = instance or CourseGrade()
    for field, value in validated_data.items():
        setattr(course_grade, field, value)
    course_grade.is_validated = False
    course_grade.validated_by = None
    course_grade.validated_at = None
    course_grade.is_published = False
    course_grade.published_at = None
    course_grade.save()
    _invalidate_report_card(student, semester)
    if instance is not None and (
        previous_student.pk != course_grade.student_id
        or previous_semester.pk != course_grade.semester_id
    ):
        _invalidate_report_card(previous_student, previous_semester)
    return course_grade


@transaction.atomic
def delete_course_grade(*, actor, course_grade):
    course_grade = CourseGrade.objects.select_for_update().select_related(
        'student', 'course', 'semester__academic_year'
    ).get(pk=course_grade.pk)
    ensure_course_access(actor, course_grade.course, course_grade.semester)
    ensure_academic_year_open(course_grade.semester)
    student = course_grade.student
    semester = course_grade.semester
    course_grade.delete()
    _invalidate_report_card(student, semester)


@transaction.atomic
def validate_course_grade(*, actor, course_grade):
    course_grade = CourseGrade.objects.select_for_update().select_related(
        'course', 'semester__academic_year'
    ).get(pk=course_grade.pk)
    ensure_course_access(actor, course_grade.course, course_grade.semester)
    ensure_academic_year_open(course_grade.semester)
    if course_grade.is_validated:
        raise ValidationError("Cette note est déjà validée.")
    course_grade.is_validated = True
    course_grade.validated_by = actor
    course_grade.validated_at = timezone.now()
    course_grade.save(update_fields=[
        'is_validated', 'validated_by', 'validated_at', 'updated_at'
    ])
    return course_grade


@transaction.atomic
def unvalidate_course_grade(*, actor, course_grade):
    course_grade = CourseGrade.objects.select_for_update().select_related(
        'student', 'course', 'semester__academic_year'
    ).get(pk=course_grade.pk)
    ensure_course_access(actor, course_grade.course, course_grade.semester)
    ensure_academic_year_open(course_grade.semester)
    course_grade.is_validated = False
    course_grade.validated_by = None
    course_grade.validated_at = None
    course_grade.is_published = False
    course_grade.published_at = None
    course_grade.save(update_fields=[
        'is_validated', 'validated_by', 'validated_at',
        'is_published', 'published_at', 'updated_at',
    ])
    _invalidate_report_card(course_grade.student, course_grade.semester)
    return course_grade


@transaction.atomic
def set_course_grades_published(*, actor, course, semester, published):
    ensure_course_access(actor, course, semester)
    ensure_academic_year_open(semester)
    queryset = CourseGrade.objects.select_for_update().filter(
        course=course,
        semester=semester,
    )
    if published:
        queryset = queryset.filter(is_validated=True, is_published=False)
    else:
        queryset = queryset.filter(is_published=True)
    now = timezone.now() if published else None
    return queryset.update(is_published=published, published_at=now), now
