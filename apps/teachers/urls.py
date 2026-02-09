from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'teachers', views.TeacherViewSet)
router.register(r'assignments', views.TeacherCourseViewSet)
router.register(r'contracts', views.TeacherContractViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
