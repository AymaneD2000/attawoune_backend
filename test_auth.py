import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.accounts.serializers import UserCreateSerializer
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()
User.objects.filter(username="test_api_user2").delete()

data = {
    "username": "test_api_user2",
    "email": "testapi2@attawoune.edu",
    "password": "TestPassword123!",
    "password_confirm": "TestPassword123!",
    "first_name": "Test",
    "last_name": "Api",
    "role": "TEACHER",
    "phone": "12345678"
}

serializer = UserCreateSerializer(data=data)
if serializer.is_valid():
    user = serializer.save()
    print("User created successfully:", user.username, "Role:", user.role, "Is Active:", user.is_active)
    
    # Try token auth
    client = APIClient()
    response = client.post('/api/auth/token/', {"username": "test_api_user2", "password": "TestPassword123!"})
    print("Token response:", response.status_code, response.data)
else:
    print("Errors:", serializer.errors)
