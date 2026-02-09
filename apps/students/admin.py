from django.contrib import admin
from .models import Student, Enrollment, Attendance


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['student_id', 'user', 'program', 'current_level', 'status', 'enrollment_date']
    search_fields = ['student_id', 'user__first_name', 'user__last_name', 'user__email']
    list_filter = ['program', 'current_level', 'status']
    raw_id_fields = ['user']


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'academic_year', 'program', 'level', 'status', 'is_active']
    list_filter = ['academic_year', 'program', 'status', 'is_active']
    raw_id_fields = ['student']


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['student', 'course_session', 'status', 'recorded_at', 'recorded_by']
    list_filter = ['status', 'recorded_at']
    raw_id_fields = ['student', 'course_session']
