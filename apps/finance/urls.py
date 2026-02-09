from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'tuition-payments', views.TuitionPaymentViewSet)
router.register(r'tuition-fees', views.TuitionFeeViewSet)
router.register(r'student-balances', views.StudentBalanceViewSet)
router.register(r'salaries', views.SalaryViewSet)
router.register(r'expenses', views.ExpenseViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', views.FinanceDashboardView.as_view(), name='finance-dashboard'),
]
