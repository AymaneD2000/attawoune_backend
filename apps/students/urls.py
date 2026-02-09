from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'', views.StudentViewSet)
router.register(r'enrollments', views.EnrollmentViewSet)
router.register(r'attendances', views.AttendanceViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
