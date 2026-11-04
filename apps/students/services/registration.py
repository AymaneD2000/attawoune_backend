"""
Registration service (year-scoped data).

All academic data is independent per academic year. Registration is the
only operation that creates data for a given year: it creates

- an ``Enrollment`` record for that year (program + level),
- a financial ``StudentBalance`` for that year when one does not exist yet,
- a sync of the student profile snapshot (``current_level`` / ``program``)
  so legacy features (ID card, reports) keep working.
"""

from decimal import Decimal

from django.db import transaction

from apps.finance.models import StudentBalance
from apps.finance.services.fees import resolve_tuition_due
from apps.university.models import AcademicYear

from apps.students.models import Enrollment


def register_student_in_year(student, academic_year, level=None, program=None, status='ENROLLED'):
    """
    Register ``student`` for ``academic_year`` (new registration or
    re-inscription from a previous year).

    Idempotent: if the enrollment already exists for (student, academic_year)
    the existing record is returned and no other data is touched.
    """
    level = level or student.current_level
    program = program or student.program

    with transaction.atomic():
        enrollment, created = Enrollment.objects.get_or_create(
            student=student,
            academic_year=academic_year,
            defaults={
                'program': program,
                'level': level,
                'status': status,
            },
        )

        if created:
            # Keep the profile snapshot in sync with the active enrollment.
            if student.current_level_id != level.id or student.program_id != program.id:
                student.current_level = level
                student.program = program
                student.save(update_fields=['current_level', 'program', 'updated_at'])

            _ensure_balance_for_year(student, academic_year, program, level)

    return enrollment


def _ensure_balance_for_year(student, academic_year, program, level):
    """Create (or align) the year's financial balance with the exact fee for
    the enrolled program/level. Payments already recorded are kept."""
    amount = resolve_tuition_due(program, level, academic_year)
    balance, created = StudentBalance.objects.get_or_create(
        student=student,
        academic_year=academic_year,
        defaults={'total_due': amount, 'total_paid': Decimal('0.00')},
    )
    # Never rewrite the amount due of a finished academic year.
    if not created and academic_year.is_current and balance.total_due != amount:
        balance.total_due = amount
        balance.save(update_fields=['total_due', 'updated_at'])


def register_in_current_year(student, level=None, program=None, status='ENROLLED'):
    """
    Register a student in the active academic year.

    Returns the created/existing Enrollment, or None when no academic year
    is active.
    """
    current_year = AcademicYear.objects.filter(is_current=True).first()
    if not current_year:
        return None
    return register_student_in_year(student, current_year, level=level, program=program, status=status)
