from django.contrib import admin
from .models import TuitionPayment, TuitionFee, StudentBalance, Salary, Expense, StudentDebt, DebtPayment


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


@admin.register(StudentDebt)
class StudentDebtAdmin(admin.ModelAdmin):
    list_display = ['id', 'student', 'academic_year', 'amount_due', 'amount_paid', 'outstanding', 'status', 'created_at']
    list_filter = ['status', 'academic_year']
    search_fields = ['student__student_id', 'student__user__first_name', 'student__user__last_name', 'description']
    raw_id_fields = ['student']

    @admin.display(description='Restant')
    def outstanding(self, obj):
        return obj.outstanding


@admin.register(DebtPayment)
class DebtPaymentAdmin(admin.ModelAdmin):
    list_display = ['reference', 'debt', 'amount', 'payment_date', 'payment_method', 'received_by']
    list_filter = ['payment_method', 'payment_date']
    search_fields = ['reference']
    raw_id_fields = ['debt']
