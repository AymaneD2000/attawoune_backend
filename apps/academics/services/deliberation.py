from decimal import Decimal
from django.db import transaction
from django.db.models import Sum, F, Avg
from apps.students.models import Student, StudentPromotion, Enrollment
from apps.academics.models import CourseGrade, ReportCard
from apps.university.models import AcademicYear, Level, ProgramFee
from apps.finance.models import StudentBalance

class DeliberationService:
    @staticmethod
    def calculate_gpa(student, semester):
        """Calcule et met à jour le bulletin (ReportCard) d'un semestre."""
        # Get/Create ReportCard
        report_card, _ = ReportCard.objects.get_or_create(
            student=student,
            semester=semester,
            defaults={
                'generated_by': None # System/Auto
            }
        )
        report_card.calculate_gpa()
        return report_card

    @staticmethod
    def deliberate_student(student, academic_year):
        """
        Effectue la délibération annuelle pour un étudiant.
        Retourne l'objet StudentPromotion créé.
        """
        # 1. Ensure both semester GPAs are calculated
        semesters = academic_year.semesters.all().order_by('semester_type')
        if not semesters.exists():
            raise ValueError("Aucun semestre défini pour cette année académique.")

        s1 = semesters.filter(semester_type='S1').first()
        s2 = semesters.filter(semester_type='S2').first()

        report_s1 = DeliberationService.calculate_gpa(student, s1) if s1 else None
        report_s2 = DeliberationService.calculate_gpa(student, s2) if s2 else None

        # 2. Calculate Annual GPA
        total_points = Decimal('0.00')
        total_credits = 0

        if report_s1:
            total_points += report_s1.gpa * report_s1.total_credits
            total_credits += report_s1.total_credits
        
        if report_s2:
            total_points += report_s2.gpa * report_s2.total_credits
            total_credits += report_s2.total_credits

        annual_gpa = (total_points / total_credits) if total_credits > 0 else Decimal('0.00')

        # 3. Determine Decision
        # Rule: GPA >= 10 => PROMOTED, else REPEATED
        if annual_gpa >= 10:
            decision = StudentPromotion.PromotionDecision.PROMOTED
            
            # Determine next level
            current_level_order = student.current_level.order
            next_level = Level.objects.filter(order=current_level_order + 1).first()
            level_to = next_level if next_level else student.current_level 
            
            if not next_level:
                remarks = "Fin de cycle - Diplômable"
            else:
                remarks = f"Admis en {level_to.name}"

        else:
            decision = StudentPromotion.PromotionDecision.REPEATED
            level_to = student.current_level
            remarks = "Redoublement"

        # 4. Save Promotion Record
        with transaction.atomic():
            promotion, created = StudentPromotion.objects.update_or_create(
                student=student,
                academic_year=academic_year,
                defaults={
                    'program': student.program,
                    'level_from': student.current_level,
                    'level_to': level_to,
                    'annual_gpa': annual_gpa,
                    'decision': decision,
                }
            )
            
            # 5. Automatic Enrollment for Next Year
            if decision in [StudentPromotion.PromotionDecision.PROMOTED, StudentPromotion.PromotionDecision.REPEATED]:
                # If Promoted, level_to is next level. If Repeated, level_to is current level.
                # Note: logic above sets level_to correctly for both cases.
                DeliberationService.enroll_for_next_year(student, academic_year, level_to)
            
        return promotion

    @staticmethod
    def enroll_for_next_year(student, current_year, level_to):
        """
        Inscrit automatiquement l'étudiant pour l'année suivante et génère le solde.
        """
        # 1. Find next academic year
        next_year = AcademicYear.objects.filter(
            start_date__gt=current_year.start_date
        ).order_by('start_date').first()
        
        if not next_year:
            return  # No next year defined, cannot enroll
            
        # 2. Create Enrollment
        if not Enrollment.objects.filter(student=student, academic_year=next_year).exists():
            Enrollment.objects.create(
                student=student,
                academic_year=next_year,
                program=student.program,
                level=level_to,
                status='ENROLLED'
            )
            
        # 3. Create Student Balance
        if not StudentBalance.objects.filter(student=student, academic_year=next_year).exists():
            # Determine fee
            try:
                program_fee = ProgramFee.objects.get(
                    program=student.program,
                    level=level_to,
                    academic_year=next_year
                )
                amount = program_fee.amount
            except ProgramFee.DoesNotExist:
                amount = student.program.tuition_fee
                
            StudentBalance.objects.create(
                student=student,
                academic_year=next_year,
                total_due=amount,
                total_paid=0
            )
