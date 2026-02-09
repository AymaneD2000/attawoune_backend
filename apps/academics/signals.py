from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum, F
from decimal import Decimal
from .models import Grade, Exam, CourseGrade
from apps.students.models import Student

def calculate_student_course_grade(student, course, semester):
    """
    Calculate the weighted average for a student in a specific course and semester.
    Updates or creates the CourseGrade record.
    """
    # Get all grades for this student in this course/semester
    grades = Grade.objects.filter(
        student=student,
        exam__course=course,
        exam__semester=semester
    ).select_related('exam')

    total_weighted_score = Decimal('0.00')
    total_weight = Decimal('0.00')

    for grade in grades:
        exam = grade.exam
        weight = exam.weight
        
        # If exam has no weight or max_score is 0, skip contribution to average but careful
        if weight == 0:
            continue
            
        # Determine score
        if grade.is_absent:
            score = Decimal('0.00')
        else:
            score = grade.score
            
        # Normalize score to 20 if max_score is not 20
        # Formula: (score / max_score) * 20
        # If max_score is 0, avoid division by zero (should strictly be validated elsewhere)
        if exam.max_score and exam.max_score > 0:
            normalized_score = (score / exam.max_score) * Decimal('20.00')
        else:
            normalized_score = score # Fallback, assume out of 20
            
        total_weighted_score += normalized_score * weight
        total_weight += weight

    # Calculate final average
    if total_weight > 0:
        final_average = total_weighted_score / total_weight
    else:
        final_average = Decimal('0.00')
        
    # Round to 2 decimal places
    final_average = final_average.quantize(Decimal('0.01'))

    # Update or Create CourseGrade
    CourseGrade.objects.update_or_create(
        student=student,
        course=course,
        semester=semester,
        defaults={
            'final_score': final_average
        }
    )

@receiver(post_save, sender=Grade)
@receiver(post_delete, sender=Grade)
def update_course_grade_on_grade_change(sender, instance, **kwargs):
    """
    When a grade is added, modified, or deleted, recalculate the CourseGrade.
    """
    exam = instance.exam
    calculate_student_course_grade(instance.student, exam.course, exam.semester)

@receiver(post_save, sender=Exam)
def update_course_grades_on_exam_change(sender, instance, created, **kwargs):
    """
    When an exam is modified (e.g. weight change), recalculate CourseGrade for ALL students
    who have a grade for this exam.
    """
    if created:
        return # New exam has no grades yet

    # Find all students who have a grade for this exam
    # We can query Grade model
    student_ids = Grade.objects.filter(exam=instance).values_list('student', flat=True).distinct()
    
    for student_id in student_ids:
        # We need the student object, or just pass ID? helper expects object but can just get it?
        # Optimization: calculate_student_course_grade takes student object.
        # We can fetch students or modify helper to take ID.
        # Let's fetch student to be safe with helper signature
        try:
            student = Student.objects.get(id=student_id)
            calculate_student_course_grade(student, instance.course, instance.semester)
        except Student.DoesNotExist:
            continue
