from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from .models import Exam, Grade
from .services.grades import recalculate_course_grade, recalculate_exam_course_grades

@receiver(post_save, sender=Grade)
@receiver(post_delete, sender=Grade)
def update_course_grade_on_grade_change(sender, instance, **kwargs):
    """
    When a grade is added, modified, or deleted, recalculate the CourseGrade.
    """
    exam = instance.exam
    recalculate_course_grade(instance.student, exam.course, exam.semester)

@receiver(post_save, sender=Exam)
def update_course_grades_on_exam_change(sender, instance, created, **kwargs):
    """
    When an exam is modified (e.g. weight change), recalculate CourseGrade for ALL students
    who have a grade for this exam.
    """
    previous = getattr(instance, '_previous_grade_context', None)
    current = (instance.course_id, instance.semester_id, instance.weight, instance.max_score)
    if created or previous == current:
        return # New exam has no grades yet

    if previous and previous[:2] != current[:2]:
        student_ids = Grade.objects.filter(exam=instance).values_list(
            'student_id', flat=True
        ).distinct()
        for student_id in student_ids:
            recalculate_course_grade(student_id, previous[0], previous[1])
    recalculate_exam_course_grades(instance)


@receiver(pre_save, sender=Exam)
def capture_previous_exam_calculation_context(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_grade_context = None
        return
    previous = Exam.objects.filter(pk=instance.pk).values_list(
        'course_id', 'semester_id', 'weight', 'max_score'
    ).first()
    instance._previous_grade_context = previous
