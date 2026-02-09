import os
import django
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from apps.academics.models import Grade, Exam, CourseGrade, ReportCard

print("Starting data clearing...")

count_grades = Grade.objects.count()
Grade.objects.all().delete()
print(f"Deleted {count_grades} Grades.")

count_exams = Exam.objects.count()
Exam.objects.all().delete()
print(f"Deleted {count_exams} Exams.")

count_cg = CourseGrade.objects.count()
CourseGrade.objects.all().delete()
print(f"Deleted {count_cg} CourseGrades.")

count_rc = ReportCard.objects.count()
ReportCard.objects.all().delete()
print(f"Deleted {count_rc} ReportCards.")

print("All grade data cleared successfully.")
