from django.contrib import admin
from .models import Teacher, TeacherCourse, TeacherContract


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ['employee_id', 'user', 'department', 'rank', 'contract_type', 'is_active']
    search_fields = ['employee_id', 'user__first_name', 'user__last_name', 'specialization']
    list_filter = ['department', 'rank', 'contract_type', 'is_active']
    raw_id_fields = ['user']


@admin.register(TeacherCourse)
class TeacherCourseAdmin(admin.ModelAdmin):
    list_display = ['teacher', 'course', 'semester', 'is_primary', 'assigned_date']
    list_filter = ['semester', 'is_primary']
    raw_id_fields = ['teacher', 'course']


@admin.register(TeacherContract)
class TeacherContractAdmin(admin.ModelAdmin):
    list_display = ['contract_number', 'teacher', 'start_date', 'end_date', 'base_salary', 'status']
    list_filter = ['status']
    search_fields = ['contract_number']
    raw_id_fields = ['teacher']
