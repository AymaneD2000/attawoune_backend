from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'academic-years', views.AcademicYearViewSet)
router.register(r'semesters', views.SemesterViewSet)
router.register(r'faculties', views.FacultyViewSet)
router.register(r'departments', views.DepartmentViewSet)
router.register(r'levels', views.LevelViewSet)
router.register(r'programs', views.ProgramViewSet)
router.register(r'classrooms', views.ClassroomViewSet)

from .dashboard import DashboardView

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
]
