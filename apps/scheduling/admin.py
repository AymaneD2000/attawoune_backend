from django.contrib import admin
from .models import TimeSlot, Schedule, CourseSession, Announcement


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ['day', 'start_time', 'end_time']
    list_filter = ['day']
    ordering = ['day', 'start_time']


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ['course', 'teacher', 'semester', 'time_slot', 'classroom', 'is_active']
    list_filter = ['semester', 'is_active']
    raw_id_fields = ['course', 'teacher']


@admin.register(CourseSession)
class CourseSessionAdmin(admin.ModelAdmin):
    list_display = ['schedule', 'date', 'session_type', 'is_cancelled']
    list_filter = ['session_type', 'is_cancelled', 'date']
    raw_id_fields = ['schedule']


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'announcement_type', 'target_audience', 'is_published', 'is_pinned', 'created_at']
    list_filter = ['announcement_type', 'target_audience', 'is_published', 'is_pinned']
    search_fields = ['title', 'content']
