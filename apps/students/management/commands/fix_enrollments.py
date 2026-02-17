from django.core.management.base import BaseCommand
from apps.students.models import Student, Enrollment
from apps.university.models import AcademicYear, Program, Level

class Command(BaseCommand):
    help = 'Fixes student enrollments for testing purposes'

    def handle(self, *args, **kwargs):
        self.stdout.write("Fixing student enrollments...")
        
        # Get current academic year
        try:
            current_year = AcademicYear.objects.get(is_current=True)
            self.stdout.write(f"Current Year: {current_year}")
        except AcademicYear.DoesNotExist:
            self.stdout.write(self.style.ERROR("No current academic year found!"))
            return

        # Get all students
        students = Student.objects.all()
        self.stdout.write(f"Total students: {students.count()}")
        
        # Enroll first 50 students in current year
        count = 0
        skipped = 0
        for student in students[:50]:
            # Check if already enrolled
            if not Enrollment.objects.filter(student=student, academic_year=current_year).exists():
                Enrollment.objects.create(
                    student=student,
                    academic_year=current_year,
                    program=student.program,
                    level=student.current_level,
                    status='ENROLLED',
                    is_active=True
                )
                count += 1
            else:
                skipped += 1
                
        self.stdout.write(self.style.SUCCESS(f"Enrolled {count} students in {current_year} (Skipped {skipped})"))
