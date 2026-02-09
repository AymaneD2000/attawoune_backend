from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'users', views.UserViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('me/', views.CurrentUserView.as_view(), name='current-user'),
    path('register/', views.RegisterView.as_view(), name='register'),
]
