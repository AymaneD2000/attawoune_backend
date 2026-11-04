"""One-time fix: align current-year balances with the per-level program fees.

Before this release, balances were created and reconciled from the program's
yearly fee only, ignoring the per-level fees set on the Filières page. This
recomputes ``total_due`` for the current academic year using the same rule as
``apps.finance.services.fees.resolve_tuition_due``. ``total_paid`` is untouched and
finished academic years are not modified.
"""

from django.db import migrations


def resync(apps, schema_editor):
    AcademicYear = apps.get_model('university', 'AcademicYear')
    ProgramFee = apps.get_model('university', 'ProgramFee')
    TuitionFee = apps.get_model('finance', 'TuitionFee')
    StudentBalance = apps.get_model('finance', 'StudentBalance')
    Enrollment = apps.get_model('students', 'Enrollment')

    year = AcademicYear.objects.filter(is_current=True).first()
    if year is None:
        return

    def resolve(program, level):
        if program is None:
            return None
        if level is not None:
            fees = ProgramFee.objects.filter(program=program, level=level)
            amount = fees.filter(academic_year=year).values_list('amount', flat=True).first()
            if amount is None:
                amount = fees.filter(
                    academic_year__start_date__lte=year.start_date,
                ).order_by('-academic_year__start_date').values_list('amount', flat=True).first()
            if amount is None:
                amount = fees.order_by('-academic_year__start_date').values_list('amount', flat=True).first()
            if amount is not None:
                return amount
            amount = TuitionFee.objects.filter(
                program=program, academic_year=year, level=level,
            ).values_list('amount', flat=True).first()
            if amount is not None:
                return amount
        amount = TuitionFee.objects.filter(
            program=program, academic_year=year, level__isnull=True,
        ).values_list('amount', flat=True).first()
        if amount is not None:
            return amount
        return program.tuition_fee

    balances = StudentBalance.objects.filter(academic_year=year).select_related(
        'student__program', 'student__current_level',
    )
    for balance in balances:
        enrollment = Enrollment.objects.filter(
            student_id=balance.student_id, academic_year=year,
        ).select_related('program', 'level').order_by('-is_active').first()
        if enrollment is not None:
            amount = resolve(enrollment.program, enrollment.level)
        else:
            amount = resolve(balance.student.program, balance.student.current_level)
        if amount is not None and amount != balance.total_due:
            balance.total_due = amount
            balance.save(update_fields=['total_due', 'updated_at'])


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0004_studentdebt_debtpayment'),
        ('university', '0003_programfee'),
        ('students', '0003_student_photo'),
    ]

    operations = [
        migrations.RunPython(resync, migrations.RunPython.noop),
    ]
