from django.contrib import admin
from .models import (
    AcademicYear, Semester, Faculty, Department, Level, Program, Classroom
)


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'is_current']
    list_filter = ['is_current']
    search_fields = ['name']


@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ['academic_year', 'semester_type', 'start_date', 'end_date', 'is_current']
    list_filter = ['academic_year', 'semester_type', 'is_current']


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'dean', 'created_at']
    search_fields = ['name', 'code']
    list_filter = ['created_at']


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'faculty', 'head', 'created_at']
    search_fields = ['name', 'code']
    list_filter = ['faculty']


@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ['name', 'order']
    ordering = ['order']


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'department', 'get_levels', 'tuition_fee', 'is_active']
    search_fields = ['name', 'code']
    list_filter = ['department', 'levels', 'is_active']

    def get_levels(self, obj):
        return ", ".join([l.name for l in obj.levels.all()])
    get_levels.short_description = 'Niveaux'


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'building', 'capacity', 'is_available']
    search_fields = ['name', 'code', 'building']
    list_filter = ['building', 'is_available', 'has_projector', 'has_computers']
