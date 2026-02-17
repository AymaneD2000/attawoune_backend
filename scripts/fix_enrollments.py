import os
import django
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.students.models import Student, Enrollment
from apps.university.models import AcademicYear, Program, Level

def run():
    print("Fixing student enrollments...")
    
    # Get current academic year
    try:
        current_year = AcademicYear.objects.get(is_current=True)
        print(f"Current Year: {current_year}")
    except AcademicYear.DoesNotExist:
        print("No current academic year found!")
        return

    # Get all students
    students = Student.objects.all()
    print(f"Total students: {students.count()}")
    
    # Enroll first 50 students in current year
    count = 0
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
            
    print(f"Enrolled {count} students in {current_year}")

if __name__ == '__main__':
    run()
