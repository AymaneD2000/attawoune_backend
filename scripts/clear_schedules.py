
from apps.scheduling.models import Schedule, TimeSlot, CourseSession

print("Clearing scheduling data...")

# Delete sessions first (referencing schedules)
sessions_count = CourseSession.objects.all().delete()[0]
print(f"Deleted {sessions_count} course sessions.")

# Delete schedules
schedules_count = Schedule.objects.all().delete()[0]
print(f"Deleted {schedules_count} schedules.")

# Delete time slots (optional, but requested 'all')
slots_count = TimeSlot.objects.all().delete()[0]
print(f"Deleted {slots_count} time slots.")

print("Done.")
