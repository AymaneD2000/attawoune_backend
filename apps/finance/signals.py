from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.students.models import Student
from apps.finance.models import StudentBalance
from apps.university.models import AcademicYear

@receiver(post_save, sender=Student)
def create_student_balance(sender, instance, created, **kwargs):
    """
    Automatically create a StudentBalance record when a new Student is created.
    Uses the current academic year and the student's program tuition fee.
    """
    if created and instance.program:
        current_year = AcademicYear.objects.filter(is_current=True).first()
        if current_year:
            StudentBalance.objects.get_or_create(
                student=instance,
                academic_year=current_year,
                defaults={
                    'total_due': instance.program.tuition_fee,
                    'total_paid': 0
                }
            )
