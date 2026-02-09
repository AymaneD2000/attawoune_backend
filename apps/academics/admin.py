from django.contrib import admin
from .models import Course, Exam, Grade, CourseGrade, ReportCard


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'program', 'course_type', 'credits', 'is_active']
    search_fields = ['code', 'name']
    list_filter = ['program', 'course_type', 'is_active']


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ['course', 'exam_type', 'semester', 'date', 'start_time', 'classroom']
    list_filter = ['exam_type', 'semester', 'date']
    raw_id_fields = ['course']


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ['student', 'exam', 'score', 'is_absent', 'graded_by', 'graded_at']
    list_filter = ['is_absent', 'graded_at']
    raw_id_fields = ['student', 'exam']


@admin.register(CourseGrade)
class CourseGradeAdmin(admin.ModelAdmin):
    list_display = ['student', 'course', 'semester', 'final_score', 'grade_letter', 'is_validated']
    list_filter = ['semester', 'grade_letter', 'is_validated']
    raw_id_fields = ['student', 'course']


@admin.register(ReportCard)
class ReportCardAdmin(admin.ModelAdmin):
    list_display = ['student', 'semester', 'gpa', 'total_credits', 'credits_earned', 'is_published']
    list_filter = ['semester', 'is_published']
    raw_id_fields = ['student']
