from decimal import Decimal
from django.db import transaction
from django.db.models import Sum, F, Avg
from apps.students.models import Student, StudentPromotion, Enrollment
from apps.academics.models import CourseGrade, ReportCard
from apps.university.models import AcademicYear, Level

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
                    'remarks': remarks
                }
            )
            
        return promotion
