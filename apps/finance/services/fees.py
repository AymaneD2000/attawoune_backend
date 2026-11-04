"""Single source of truth for the tuition amount a student owes for one year.

Resolution order (first match wins):

1. ``ProgramFee`` for (program, level, academic_year) — the per-level fee
   configured on the Filières page.
2. ``TuitionFee`` for (program, academic_year, level) — finance admin config.
3. ``TuitionFee`` for (program, academic_year) without a level.
4. ``Program.tuition_fee`` — the program's yearly price.
"""

from decimal import Decimal

from apps.university.models import ProgramFee

from ..models import TuitionFee

ZERO = Decimal('0.00')


def resolve_tuition_due(program, level, academic_year):
    """Return the amount due for one academic year of ``program`` at ``level``."""
    if program is None:
        return ZERO

    if academic_year is not None:
        if level is not None:
            program_fee = ProgramFee.objects.filter(
                program=program, level=level, academic_year=academic_year,
            ).values_list('amount', flat=True).first()
            if program_fee is not None:
                return program_fee

            tuition_fee = TuitionFee.objects.filter(
                program=program, academic_year=academic_year, level=level,
            ).values_list('amount', flat=True).first()
            if tuition_fee is not None:
                return tuition_fee

        tuition_fee = TuitionFee.objects.filter(
            program=program, academic_year=academic_year, level__isnull=True,
        ).values_list('amount', flat=True).first()
        if tuition_fee is not None:
            return tuition_fee

    return program.tuition_fee or ZERO


def resolve_student_tuition_due(student, academic_year):
    """Amount due by ``student`` for ``academic_year``, based on that year's
    enrollment (falling back to the student's profile program/level)."""
    from apps.students.models import Enrollment

    enrollment = Enrollment.objects.filter(
        student=student, academic_year=academic_year,
    ).select_related('program', 'level').order_by('-is_active').first()
    if enrollment is not None:
        return resolve_tuition_due(enrollment.program, enrollment.level, academic_year)
    return resolve_tuition_due(student.program, student.current_level, academic_year)
