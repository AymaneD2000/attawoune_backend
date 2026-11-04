"""Single source of truth for the tuition amount a student owes for one year.

Per-level fees set on the Filières page (``ProgramFee``) belong to the program
and carry over from one academic year to the next: each save is stored for the
year it was made in, and a year without its own row uses the latest earlier one.

Resolution order (first match wins):

1. ``ProgramFee`` for (program, level): the row for ``academic_year``, else the
   most recent row from an earlier year, else the most recent row at all.
2. ``TuitionFee`` for (program, academic_year, level) — finance admin config.
3. ``TuitionFee`` for (program, academic_year) without a level.
4. ``Program.tuition_fee`` — the program's yearly price.
"""

from decimal import Decimal

from apps.university.models import ProgramFee

from ..models import TuitionFee

ZERO = Decimal('0.00')


def effective_program_fee(program, level, academic_year):
    """The ``ProgramFee`` row that applies to (program, level) in
    ``academic_year``, or ``None`` when the level has never had a fee."""
    fees = ProgramFee.objects.filter(program=program, level=level).select_related(
        'level', 'academic_year',
    )
    if academic_year is not None:
        exact = fees.filter(academic_year=academic_year).first()
        if exact is not None:
            return exact
        earlier = fees.filter(
            academic_year__start_date__lte=academic_year.start_date,
        ).order_by('-academic_year__start_date').first()
        if earlier is not None:
            return earlier
    return fees.order_by('-academic_year__start_date').first()


def effective_program_fees(program, academic_year):
    """Effective ``ProgramFee`` row for each level of ``program``."""
    rows = []
    for level in program.levels.all():
        fee = effective_program_fee(program, level, academic_year)
        if fee is not None:
            rows.append(fee)
    return rows


def resolve_tuition_due(program, level, academic_year):
    """Return the amount due for one academic year of ``program`` at ``level``."""
    if program is None:
        return ZERO

    if level is not None:
        program_fee = effective_program_fee(program, level, academic_year)
        if program_fee is not None:
            return program_fee.amount

    if academic_year is not None:
        if level is not None:
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


def sync_program_balances(program, academic_year):
    """Align ``total_due`` of every balance of ``program`` for ``academic_year``
    with the configured fees. Amounts paid are never changed.

    A balance belongs to the program when the student's enrollment for that
    year is in the program, or (no enrollment that year) the student's profile
    program is. Returns the number of balances updated.
    """
    from django.db.models import Q

    from apps.students.models import Enrollment, Student

    from ..models import StudentBalance

    enrolled_in_program = Enrollment.objects.filter(
        academic_year=academic_year, program=program,
    ).values('student_id')
    profile_only = Student.objects.filter(program=program).exclude(
        enrollments__academic_year=academic_year,
    ).values('id')

    balances = StudentBalance.objects.filter(academic_year=academic_year).filter(
        Q(student_id__in=enrolled_in_program) | Q(student_id__in=profile_only)
    ).select_related('student__program', 'student__current_level')

    updated = 0
    for balance in balances:
        new_due = resolve_student_tuition_due(balance.student, academic_year)
        if new_due != balance.total_due:
            balance.total_due = new_due
            balance.save(update_fields=['total_due', 'updated_at'])
            updated += 1
    return updated
