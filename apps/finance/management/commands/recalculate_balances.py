from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.finance.models import StudentBalance
from apps.finance.services.fees import resolve_student_tuition_due
from apps.university.models import AcademicYear


class Command(BaseCommand):
    help = (
        "Recalculate total_due of student balances from the configured fees "
        "(per-level fee, else program yearly fee). Amounts paid are never changed."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help="Show what would change without saving anything.",
        )
        parser.add_argument(
            '--year', type=int, default=None,
            help="Academic year id (defaults to the current academic year).",
        )

    def handle(self, *args, dry_run=False, year=None, **options):
        if year is not None:
            academic_year = AcademicYear.objects.filter(pk=year).first()
        else:
            academic_year = AcademicYear.objects.filter(is_current=True).first()
        if academic_year is None:
            raise CommandError("Academic year not found.")

        self.stdout.write(f"Academic year: {academic_year.name}{' (dry run)' if dry_run else ''}")

        balances = StudentBalance.objects.filter(
            academic_year=academic_year,
        ).select_related('student__user', 'student__program', 'student__current_level')

        changed = 0
        total = 0
        with transaction.atomic():
            for balance in balances:
                total += 1
                new_due = resolve_student_tuition_due(balance.student, academic_year)
                if new_due == balance.total_due:
                    continue
                changed += 1
                self.stdout.write(
                    f"  {balance.student.student_id} {balance.student.user.get_full_name()}: "
                    f"{balance.total_due} -> {new_due}"
                )
                if not dry_run:
                    balance.total_due = new_due
                    balance.save(update_fields=['total_due', 'updated_at'])

        verb = "Would update" if dry_run else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{verb} {changed} of {total} balances."))
