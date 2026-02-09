from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'courses', views.CourseViewSet)
router.register(r'exams', views.ExamViewSet)
router.register(r'grades', views.GradeViewSet)
router.register(r'course-grades', views.CourseGradeViewSet)
router.register(r'report-cards', views.ReportCardViewSet)
router.register(r'deliberation', views.DeliberationViewSet, basename='deliberation')

urlpatterns = [
    path('', include(router.urls)),
]
