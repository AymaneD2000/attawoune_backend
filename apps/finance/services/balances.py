from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Sum

from ..models import StudentBalance, TuitionPayment
from .fees import resolve_student_tuition_due


def _total_due(student, academic_year):
    return resolve_student_tuition_due(student, academic_year)


@transaction.atomic
def reconcile_student_balance(student, academic_year):
    """Rebuild one cached balance from its authoritative payment ledger."""
    student_id = getattr(student, 'pk', student)
    academic_year_id = getattr(academic_year, 'pk', academic_year)

    balance = StudentBalance.objects.select_for_update().filter(
        student_id=student_id,
        academic_year_id=academic_year_id,
    ).first()

    created = False
    if balance is None:
        try:
            balance = StudentBalance.objects.create(
                student_id=student_id,
                academic_year_id=academic_year_id,
                total_due=Decimal('0.00'),
                total_paid=Decimal('0.00'),
            )
            created = True
        except IntegrityError:
            balance = StudentBalance.objects.select_for_update().get(
                student_id=student_id,
                academic_year_id=academic_year_id,
            )

    total_paid = TuitionPayment.objects.filter(
        student_id=student_id,
        academic_year_id=academic_year_id,
        status=TuitionPayment.PaymentStatus.COMPLETED,
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    # Resolve objects through the locked row to avoid extra caller assumptions.
    # The amount due of a finished academic year is frozen: only the current
    # year (or a balance created just now) follows the configured fees.
    if created or balance.academic_year.is_current:
        balance.total_due = _total_due(balance.student, balance.academic_year)
    balance.total_paid = total_paid
    balance.save(update_fields=['total_due', 'total_paid', 'updated_at'])
    return balance


def reconcile_balance_pairs(*pairs):
    seen = set()
    balances = []
    for student, academic_year in pairs:
        if student is None or academic_year is None:
            continue
        key = (
            getattr(student, 'pk', student),
            getattr(academic_year, 'pk', academic_year),
        )
        if key in seen:
            continue
        seen.add(key)
        balances.append(reconcile_student_balance(student, academic_year))
    return balances
