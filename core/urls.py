"""
URL configuration for Université Attawoune Management System.

This module provides:
- Admin interface
- JWT Authentication endpoints
- Versioned API endpoints (/api/v1/)
- Backward-compatible API endpoints (/api/)
- API documentation (Swagger/ReDoc)
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

# API v1 endpoints
api_v1_patterns = [
    path('accounts/', include('apps.accounts.urls')),
    path('university/', include('apps.university.urls')),
    path('students/', include('apps.students.urls')),
    path('teachers/', include('apps.teachers.urls')),
    path('academics/', include('apps.academics.urls')),
    path('finance/', include('apps.finance.urls')),
    path('scheduling/', include('apps.scheduling.urls')),
]

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),

    # JWT Authentication
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    # API v1 (versioned endpoints)
    path('api/v1/', include((api_v1_patterns, 'api_v1'), namespace='v1')),

    # Backward-compatible API endpoints (without versioning)
    path('api/accounts/', include('apps.accounts.urls')),
    path('api/university/', include('apps.university.urls')),
    path('api/students/', include('apps.students.urls')),
    path('api/teachers/', include('apps.teachers.urls')),
    path('api/academics/', include('apps.academics.urls')),
    path('api/finance/', include('apps.finance.urls')),
    path('api/scheduling/', include('apps.scheduling.urls')),

    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

