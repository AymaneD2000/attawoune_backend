from django.contrib import admin
from .models import TuitionPayment, TuitionFee, StudentBalance, Salary, Expense


@admin.register(TuitionPayment)
class TuitionPaymentAdmin(admin.ModelAdmin):
    list_display = ['reference', 'student', 'academic_year', 'amount', 'payment_method', 'status', 'payment_date']
    search_fields = ['reference', 'receipt_number']
    list_filter = ['academic_year', 'payment_method', 'status']
    raw_id_fields = ['student']


@admin.register(TuitionFee)
class TuitionFeeAdmin(admin.ModelAdmin):
    list_display = ['program', 'academic_year', 'amount', 'installments_allowed', 'due_date']
    list_filter = ['academic_year']
    raw_id_fields = ['program']


@admin.register(StudentBalance)
class StudentBalanceAdmin(admin.ModelAdmin):
    list_display = ['student', 'academic_year', 'total_due', 'total_paid', 'balance', 'is_paid']
    list_filter = ['academic_year']
    raw_id_fields = ['student']


@admin.register(Salary)
class SalaryAdmin(admin.ModelAdmin):
    list_display = ['employee', 'month', 'year', 'base_salary', 'net_salary', 'status', 'payment_date']
    list_filter = ['year', 'month', 'status']
    raw_id_fields = ['employee']


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['category', 'description', 'amount', 'date', 'approved_by']
    list_filter = ['category', 'date']
