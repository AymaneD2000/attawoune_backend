
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.accounts.models import User
from apps.students.models import Student

def full_cleanup():
    print("Starting full database cleanup...")
    
    # 1. Delete all Student profiles (cascade will handle some things, but let's be explicit)
    student_count = Student.objects.count()
    Student.objects.all().delete()
    print(f"Deleted {student_count} Student profiles.")
    
    # 2. Delete all Users except 'admin'
    users_to_delete = User.objects.exclude(username='admin')
    user_count = users_to_delete.count()
    
    # List them for logging
    for u in users_to_delete:
        print(f"Deleting user: {u.username} ({u.role})")
        
    users_to_delete.delete()
    print(f"Deleted {user_count} User accounts.")
    
    # 3. Double check admin exists
    admin_exists = User.objects.filter(username='admin').exists()
    if admin_exists:
        print("Admin user 'admin' preserved.")
    else:
        print("WARNING: User 'admin' not found!")

if __name__ == '__main__':
    try:
        full_cleanup()
        print("Cleanup completed successfully.")
    except Exception as e:
        print(f"Error during cleanup: {e}")
