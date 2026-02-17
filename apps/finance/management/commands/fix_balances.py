from django.core.management.base import BaseCommand
from apps.students.models import Student
from apps.finance.models import StudentBalance
from apps.university.models import AcademicYear

class Command(BaseCommand):
    help = 'Fixes student balances for enrolled students in current academic year'

    def handle(self, *args, **kwargs):
        self.stdout.write("Fixing student balances...")
        
        # Get current academic year
        try:
            current_year = AcademicYear.objects.get(is_current=True)
            self.stdout.write(f"Current Year: {current_year}")
        except AcademicYear.DoesNotExist:
            self.stdout.write(self.style.ERROR("No current academic year found!"))
            return

        # Get all students enrolled in current year
        students = Student.objects.filter(enrollments__academic_year=current_year, enrollments__is_active=True).distinct()
        self.stdout.write(f"Total enrolled students in current year: {students.count()}")
        
        count = 0
        skipped = 0
        
        for student in students:
            # Check if balance exists
            if not StudentBalance.objects.filter(student=student, academic_year=current_year).exists():
                # Create balance
                if student.program:
                    StudentBalance.objects.create(
                        student=student,
                        academic_year=current_year,
                        total_due=student.program.tuition_fee,
                        total_paid=0
                    )
                    count += 1
                else:
                    self.stdout.write(self.style.WARNING(f"Student {student} has no program!"))
            else:
                skipped += 1
                
        self.stdout.write(self.style.SUCCESS(f"Created {count} StudentBalance records (Skipped {skipped})"))
