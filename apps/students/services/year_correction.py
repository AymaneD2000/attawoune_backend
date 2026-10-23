"""
Academic-year correction service.

Moves a newly created student from a mistaken academic year to the correct
year. This is a correction, NOT a re-inscription: students with any
academic or financial history in the source year are blocked and left
untouched for manual review.

Per-student behavior (each student in its own atomic transaction):

1. preserve the account, profile, photo, program, level and contact data;
2. remove the empty generated source-year balance (total_paid == 0);
3. delete the mistaken source-year enrollment;
4. create the target-year enrollment (same program/level, ENROLLED, active);
5. create the target-year balance (exact ProgramFee, program fee fallback);
6. set the corrected enrollment date;
7. regenerate the matricule with the target year's segment.

If any step fails, that student's transaction rolls back and the student
is reported as blocked; other students in a batch are unaffected.
"""

from dataclasses import dataclass

from django.db import transaction

from apps.academics.models import CourseGrade, Grade, ReportCard
from apps.finance.models import StudentBalance, StudentDebt, TuitionPayment
from apps.students.models import Attendance, Enrollment, Student, StudentPromotion

from .registration import register_student_in_year


class CorrectionBlocked(Exception):
    """Raised when a student is not eligible for year correction (data untouched)."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True)
class CorrectionResult:
    student: int
    name: str
    old_student_id: str
    new_student_id: str


def correct_student_academic_year(*, student_id, source_year, target_year, enrollment_date) -> CorrectionResult:
    """
    Correct one student's academic year atomically.

    Raises ``CorrectionBlocked`` (with a human-readable French reason) when
    the student is not eligible. On success returns the old/new matricules.
    """
    with transaction.atomic():
        student = (
            Student.objects.select_for_update()
            .select_related('user', 'program')
            .filter(pk=student_id)
            .first()
        )
        if student is None:
            raise CorrectionBlocked("Étudiant introuvable.")

        # Lock this student's enrollment rows before evaluating eligibility.
        list(Enrollment.objects.select_for_update().filter(student=student))

        block_reason = _block_reason(student, source_year, target_year)
        if block_reason:
            raise CorrectionBlocked(block_reason)

        source_enrollment = Enrollment.objects.get(student=student)

        # 1. Remove the empty generated balance for the source year, if any.
        StudentBalance.objects.filter(student=student, academic_year=source_year).delete()

        # 2. Delete the mistaken source-year enrollment.
        source_enrollment.delete()

        # 3. Create the target-year enrollment + balance and sync the profile.
        register_student_in_year(
            student,
            target_year,
            level=source_enrollment.level,
            program=source_enrollment.program,
            status='ENROLLED',
        )

        # 4. Apply the corrected enrollment date.
        student.enrollment_date = enrollment_date
        student.save(update_fields=['enrollment_date', 'updated_at'])

        # 5. Regenerate the matricule for the target year.
        old_student_id, new_student_id = student.regenerate_student_id_for_year(target_year)

    return CorrectionResult(
        student=student.pk,
        name=student.user.get_full_name(),
        old_student_id=old_student_id,
        new_student_id=new_student_id,
    )


def _block_reason(student, source_year, target_year):
    """Return a French blocking reason, or None when the student is eligible."""
    source_name = source_year.name
    target_name = target_year.name

    total_enrollments = Enrollment.objects.filter(student=student).count()
    if total_enrollments == 0:
        return f"Aucune inscription trouvée pour {source_name}."

    if not Enrollment.objects.filter(student=student, academic_year=source_year).exists():
        return f"Aucune inscription trouvée pour {source_name}."

    if Enrollment.objects.filter(student=student, academic_year=target_year).exists():
        return f"L'étudiant est déjà inscrit pour {target_name}."

    if total_enrollments > 1:
        return "Historique d'inscriptions multiple; correction manuelle requise."

    if TuitionPayment.objects.filter(student=student, academic_year=source_year).exists():
        return f"Paiements trouvés pour {source_name}."

    if StudentBalance.objects.filter(student=student, academic_year=source_year, total_paid__gt=0).exists():
        return f"Solde partiellement payé pour {source_name}."

    if StudentDebt.objects.filter(student=student, academic_year=source_year).exists():
        return f"Dettes trouvées pour {source_name}."

    if Grade.objects.filter(student=student, exam__semester__academic_year=source_year).exists():
        return f"Notes d'examen trouvées pour {source_name}."

    if CourseGrade.objects.filter(student=student, semester__academic_year=source_year).exists():
        return f"Notes de cours trouvées pour {source_name}."

    if Attendance.objects.filter(
        student=student,
        course_session__schedule__semester__academic_year=source_year,
    ).exists():
        return f"Présences trouvées pour {source_name}."

    if ReportCard.objects.filter(student=student, semester__academic_year=source_year).exists():
        return f"Bulletins trouvés pour {source_name}."

    if StudentPromotion.objects.filter(student=student, academic_year=source_year).exists():
        return f"Délibérations trouvées pour {source_name}."

    return None
