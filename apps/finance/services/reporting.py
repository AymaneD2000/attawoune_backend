from django.db.models import Sum
from apps.finance.models import TuitionPayment
from apps.finance.services.fees import resolve_tuition_due
from apps.students.models import Enrollment

class FinancialReportService:
    @staticmethod
    def generate_statement(student, academic_year=None):
        """
        Génère un état financier pour un étudiant.
        Retourne le total dû, le total payé et le solde.
        """
        # Default to current enrollment's academic year if not provided
        if not academic_year:
            current_enrollment = Enrollment.objects.filter(student=student, is_active=True).first()
            if current_enrollment:
                academic_year = current_enrollment.academic_year

        # Get payments
        payments = TuitionPayment.objects.filter(student=student)
        if academic_year:
            payments = payments.filter(academic_year=academic_year)

        total_paid = payments.filter(status='COMPLETED').aggregate(sum=Sum('amount'))['sum'] or 0

        # Determine total due based on Program Tuition Fee
        total_due = 0
        program_name = "N/A"

        # Try to find relevant enrollment to determine program
        enrollment = Enrollment.objects.filter(student=student)
        if academic_year:
            enrollment = enrollment.filter(academic_year=academic_year)
        enrollment = enrollment.first()

        if enrollment:
            program = enrollment.program
        else:
            # Fallback to student's main program if no enrollment found
            program = student.program

        if program:
            program_name = program.name

            # Determine level for fee lookup
            level = enrollment.level if enrollment else student.current_level

            total_due = resolve_tuition_due(program, level, academic_year)

        balance = total_due - total_paid

        history = list(payments.values('id', 'payment_date', 'amount', 'payment_method', 'reference', 'status', 'description'))

        return {
            "student_name": student.user.get_full_name(),
            "program": program_name,
            "academic_year": academic_year.name if academic_year else "Non défini",
            "total_due": total_due,
            "total_paid": total_paid,
            "balance": balance,
            "status": "PAID" if balance <= 0 and total_due > 0 else ("PARTIAL" if total_paid > 0 else "UNPAID"),
            "transactions": history
        }
