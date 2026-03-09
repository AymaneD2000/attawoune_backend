import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.accounts.models import User

user = User.objects.filter(username='comptable1').first()
if user:
    print("User found:", user.username)
    print("Is active:", user.is_active)
    print("Raw password prefix:", user.password[:10] if user.password else "None")
    print("Match 'comptable1@attawoune':", user.check_password('comptable1@attawoune'))
    print("Match 'comptable1@attawoune ':", user.check_password('comptable1@attawoune '))
else:
    print("User comptable1 not found!")
